from agent1.observer import StateBuilder
from agent1.planner import getDecisions, parseAction
from agent1.data import actionRecord, agentMemory, returnResult
from agent1.executor import executor
from agent1.progress import progressCheck
import datetime


class browserAgent:
    def __init__(self, page, client, goal, model, maxTokens=1024, maxSteps=10, maxErrors=3, maxSameActions=3):
        self.page = page
        self.client = client
        self.goal = goal
        self.model = model
        self.maxTokens = maxTokens
        self.maxSteps = maxSteps
        self.maxErrors = maxErrors
        self.maxSameActions = maxSameActions
        self.res = None

        self.observer = StateBuilder()
        self.planner = getDecisions(self.client, self.goal, self.model, self.maxTokens)
        self.memory = agentMemory(goal=goal)
        self.executor = executor(self.page, self.memory, downloadDir="./downloads", defaultTimeout=10000)

    async def run(self):
        step = 0
        consecutiveErrors = []

        while step < self.maxSteps:
            step += 1

            print(f"\n{'='*70}")
            print(f"STEP {step}")
            print("=" * 70)

            # observe
            state = await self.observer.build(self.page, self.memory)
        
            # get decision/action
            try:
                rawText = self.planner.decide(state, self.memory, includeScreenShot=False)
                curActionRecord = parseAction(rawText, step, self.page.url)
                curActionRecord.state = state

            except Exception as e:
                print(f"Planner error on step {step}: {e}")
                consecutiveErrors.append(True)
                curActionRecord = actionRecord(
                    step=step,
                    timestamp=datetime.datetime.now().isoformat(),
                    error=str(e),
                    state=state,
                )
            # exit method
                if len(consecutiveErrors) >= self.maxErrors and all(consecutiveErrors[-self.maxErrors:]):
                    self.memory.history.append(curActionRecord)
                    self.res = returnResult(success=False, steps=step, memory=self.memory, downloadedPath=None, info="consecutive error")
                    break

                self.memory.history.append(curActionRecord)
                continue

            
            print("step:", curActionRecord.step, 
                  "action:",curActionRecord.action, 
                    "selector:", curActionRecord.selector,
                    "timestamp:",  curActionRecord.timestamp,
                      "thought:", curActionRecord.thought,
                        "reason:", curActionRecord.reason, 
                        "error:", curActionRecord.error)


            # execute action/exit
            try:
                status, savePath = await self.executor.execute(curActionRecord)
                curActionRecord.success = True
                if status == "downloaded":
                    self.memory.history.append(curActionRecord)
                    self.res = returnResult(success=True, steps=step, memory=self.memory, downloadedPath=savePath, info="downloaded")
                    break
                if status == "done/abort":
                    self.memory.history.append(curActionRecord)
                    self.res = returnResult(success=True, steps=step, memory=self.memory, downloadedPath=savePath, info="done/abort")
                    break

            except Exception as e:
                consecutiveErrors.append(True)
                curActionRecord.state = state
                curActionRecord.error = str(e)

                if len(consecutiveErrors) >= self.maxErrors and all(consecutiveErrors[-self.maxErrors:]):
                    self.memory.history.append(curActionRecord)
                    self.res = returnResult(success=False, steps=step, memory=self.memory, downloadedPath=None, info="consecutive error")
                    break

                self.memory.history.append(curActionRecord)
                continue



            # validate post execution to see progress
            afterPageState = await self.observer.build(self.page, self.memory)
            result = progressCheck(curActionRecord, state, afterPageState, self.executor.savePath)
            curActionRecord.validation = result

            if result[0] is False:
                self.memory.history.append(curActionRecord)
                self.res = returnResult(success=False, steps=step, memory=self.memory, downloadedPath=savePath, info="same step repeated")
                break

            self.memory.history.append(curActionRecord)
            consecutiveErrors = []

        if self.res is None:
            self.res = returnResult(success=False, steps=step, memory=self.memory, downloadedPath=None, info="max steps reached")

        return self.res
