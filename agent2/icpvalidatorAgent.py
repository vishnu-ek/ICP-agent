import json
import re
import time
from google.genai import types
from agent2.data2 import icpFit, actionRecord
from agent2.companyLookUp import CompanyLookupTool


ASCENDO_ICP_CONTEXT = """
                        ascendo.ai builds an agentic AI platform for field service and customer
                        support organizations. It focuses on:
                        - Field service management (FSM) teams and technicians
                        - Customer support / customer experience (CX) organizations
                        - Companies with complex physical products needing service, parts,
                            warranty, or knowledge-base support (e.g. industrial equipment,
                            medical devices, telecom, HVAC, manufacturing)
                        - Mid-market to enterprise companies looking to automate service triage,
                            diagnostics, knowledge retrieval, and technician assistance with AI/agents

                        Good ICP fits are: Heads/VPs/Directors of Field Service, Customer Support,
                        Customer Experience, Service Operations, or CX Technology, at companies in
                        industrial, medical device, telecom, HVAC, manufacturing, or similar
                        service-heavy sectors.

                        Poor fits are: pure software/SaaS companies with no field service or physical
                        product component, marketing/sales-only roles, or organizations without a
                        support/service operation.
                        """


def buildDecisionPrompt(curIcpFit, accumulatedContext):
    speakerLines = ""
    for speakerTitle in curIcpFit.speakers:
        speakerLines = speakerLines + str(speakerTitle) + "\n"

    speakerLines = "no speaker listed" if speakerLines == "" else speakerLines
    context = "no external lookups performed yet" if accumulatedContext is None else accumulatedContext

    prompt = f"""
                You are assessing whether the company "{curIcpFit.company}" fits the
                Ideal Customer Profile (ICP) of ascendo.ai.

                ASCENDO.AI ICP CONTEXT:
                {ASCENDO_ICP_CONTEXT}

                Known speakers from this company at the conference:
                {speakerLines}

                External information gathered so far:
                {context}

                Decide what to do next. You have two options:

                1. If you already have enough information (from the speaker
                   titles, company name recognition, or prior lookups) to
                   confidently judge ICP fit, respond with a FINAL decision.

                2. If the company name is unfamiliar or you're unsure what
                   industry/business it's in, and you have NOT already looked
                   it up (avoid repeating the same lookup), request a lookup.

                Return ONLY valid JSON, no markdown fences, in ONE of these
                two shapes:

                Requesting more info:
                {{
                  "decision": "lookup",
                  "thought": "<why you need more info>",
                  "lookupQuery": "<company name to search>"
                }}

                Final answer:
                {{
                  "decision": "final",
                  "thought": "<your reasoning>",
                  "fitScore": "high" | "medium" | "low",
                  "reasoning": "<1-2 sentence justification>"
                }}
                """
    return prompt


def parseDecision(rawText):
    match = re.search(r"\{.*\}", rawText, re.DOTALL)
    if not match:
        return {"decision": "final", "fitScore": "low",
                 "reasoning": "Could not parse model output; defaulting to low confidence.",
                 "thought": ""}
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return {"decision": "final", "fitScore": "low",
                 "reasoning": "Invalid JSON from model; defaulting to low confidence.",
                 "thought": ""}


class IcpValidatorAgent:
    def __init__(self, client, model, maxTokens=1024, maxIterations=3):
        self.client = client
        self.model = model
        self.lookupTool = CompanyLookupTool()
        self.maxTokens = maxTokens
        self.maxIterations = maxIterations

    def callModel(self, prompt):
        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            max_output_tokens=self.maxTokens,
        )
        response = self.client.models.generate_content(
            model=self.model,
            contents=[prompt],
            config=config,
        )
        return response.text
    
    def evaluateCompany(self, company, curIcpFit):

        alreadyLookedUp = set()
        accumulatedContext = None
        iteration = 0

        while iteration < self.maxIterations:
            curActionRecord = actionRecord(company=company)
            iteration += 1

            # observe
            curActionRecord.iteration = iteration
            prompt = buildDecisionPrompt(curIcpFit, accumulatedContext)
            try:
                rawText = self.callModel(prompt)
            except Exception as e:
                curActionRecord.error = str(e) + " -- LLM failed"
                curIcpFit.itsActionRecord.append(curActionRecord)
                return curIcpFit
            
            # decide
            parsed = parseDecision(rawText)
            decision = parsed["decision"]
            curActionRecord.decision = decision

            # i am looking up everytime when i run this agent. instead i can cache the data
            if decision == "lookup":
                print("look up")
                curActionRecord.lookupQuery = parsed.get("lookupQuery") or ""
                curActionRecord.decision = "lookup"
                curActionRecord.thought =  parsed.get("thought") or ""
                
                # avoid multiple lookups
                if company in alreadyLookedUp:
                    curActionRecord.error = "already looked up once"  
                    curIcpFit.itsActionRecord.append(curActionRecord)      
                    return curIcpFit

                # act
                lookupResult = self.lookupTool.lookup(company)
                print("result:", lookupResult)
                alreadyLookedUp.add(company)
                curActionRecord.gatheredContext = lookupResult
                accumulatedContext = lookupResult
                curIcpFit.itsActionRecord.append(curActionRecord)
                continue
        
            # decision final
            curActionRecord.success = True
            curIcpFit.fitScore = parsed.get("fitScore") or "low"
            curIcpFit.reasoning = parsed.get("reasoning") or "No reasoning provided."
            curIcpFit.itsActionRecord.append(curActionRecord)
            return curIcpFit

        # loop ended without final decision
        curIcpFit.fitScore = "low"
        curIcpFit.reasoning = f"Could not reach decision within {self.maxIterations}"
        curIcpFit.itsActionRecord.append(curActionRecord)
        return curIcpFit
    

    def evaluateAll(self, companySpeakerMap, icpAgentMemory):
        dedicatedList = []

        # for each company separate LLM evaluation is performed
        for company, speakerTitle in companySpeakerMap.items():

            curIcpFit = icpFit(company=company, speakers=speakerTitle)
            print(f"\n icp agent evaluating: {company}")
            curIcpFit = self.evaluateCompany(company, curIcpFit)
            print(f"[icp agent]   -> {curIcpFit.fitScore}: {curIcpFit.reasoning}")
            dedicatedList.append((curIcpFit.company, curIcpFit.fitScore, curIcpFit.reasoning))
            icpAgentMemory.allFits.append(curIcpFit)

        return icpAgentMemory, dedicatedList
    
