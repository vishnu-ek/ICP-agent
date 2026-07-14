import json
import re
import datetime
import time
from agent1.data import actionRecord
from google.genai import types

def summary(history):
    li = []
    for i in history:
        li.append({
                "step": i.step,
                "action": i.action,
                "selector": i.selector,
                "value": i.value,
                "success": i.success,
                "error": i.error,
            })
        
    return li

def buildPrompt(state, memory, sampleUserData=None):
    userDataJson = json.dumps(sampleUserData, indent=2) if sampleUserData else "{}"

    country_value = sampleUserData.get("country") if isinstance(sampleUserData, dict) else getattr(sampleUserData, "country", "India")

    prompt = f"""
                        You are a browser automation agent.

                        Goal: {memory.goal}

                        Current url:{state.currentUrl}

                        previously visited urls: {memory.visitedUrls}

                        action history/previous steps: {json.dumps(summary(memory.history), default=str)}

                        accessibilityTree: {state.accessibility}

                        DOM: {state.dom}

                        Use the values below when you need to fill inputs on the page: {userDataJson}

                        Determine the SINGLE best next action. Your response must strictly contain all fields listed in the SUGGESTIONS below:

                        Possible actions suggestions:
                        1. Fill a Textbox
                            Use this when you need to enter text into an input field.
                            {{
                                "thought": "I need to fill out the name field.",
                                "action": "fill",
                                "target": "<input_selector_or_id>",
                                "value": "<value_from_user_profile>",
                                "reason": "Filling out required name field."
                            }}
                    
                        2. Click
                            Use this to click links, checkboxes, or buttons (e.g., download buttons).
                            {{
                                "thought": "I need to submit the form to get the agenda.",
                                "action": "click",
                                "target": "<a selector from the dom list above>",
                                "value": "",
                                "reason": "Clicking download button to initiate the PDF download."
                            }}

                        3. Select dropdown
                            Use this to choose an option from a drop-down menu (like country/location). "Country" may be a custom dropdown, not a native select 
                            {{
                                "thought": "I need to set the location to India.",
                                "action": "select",
                                "target": "<selector of the country dropdown container from the dom list>",
                                "value": "{country_value}",
                                "reason": "Selecting India as target location."
                            }}

                        4. Wait
                                {{
                                    "thought": "Waiting for the page redirection or content load.",
                                    "action": "wait",
                                    "target": "",
                                    "value": "2",
                                    "reason": "Giving the page 2 seconds to load dynamically."
                                }}

                        5. Finish
                        Use this only when you verify the PDF download has successfully started or completed.
                        {{
                            "thought": "The PDF was successfully downloaded to the path.",
                            "action": "done",
                            "target": "",
                            "value": "",
                            "reason": "Goal fully achieved."
                        }}

                        Return ONLY a single valid JSON object representing ONE action — not a list, not multiple steps, not an array. Do not plan ahead; decide only the next single action.
                        """

    return prompt


def parseAction(rawText, step, url):
    match = re.search(r"\{.*\}", rawText, re.DOTALL)

    if not match:
        raise Exception(f"Planner did not return JSON-like content.\nRaw: {rawText[:500]}")

    text = match.group(0)

    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise Exception(f"Planner did not return valid JSON: {e}\nRaw: {rawText[:500]}")

    if isinstance(data, list):
        if not data:
            raise Exception(f"Planner returned an empty action list.\nRaw: {rawText[:500]}")
        data = data[0]

    action = actionRecord(
        rawText=rawText,
        step=step,
        timestamp=datetime.datetime.now().isoformat(),
        action=data.get("action") or "",
        thought=data.get("thought") or "",
        value=data.get("value") or "",
        selector=data.get("selector") or data.get("target") or "",
        reason=data.get("reason") or "",
        success=False,  # default
        error=None,  # default
        url=url,
        state=None
    )

    return action


# build prompts, get results and give back
class getDecisions:  
    def __init__(self, client, goal, model, maxTokens=1024):
        self.client = client
        self.goal = goal
        self.model = model
        self.maxTokens = maxTokens

    def decide(self, state, memory, includeScreenShot=False, sampleUserData=None):
        print("\n========== AGENT ==========")
        print("goal", memory.goal)
        print("Current URL:", state.currentUrl)
        print("DOM Elements:", len(state.dom))
        print("AX Nodes:", len(state.accessibility))
        print("Visible Elements:", len(state.boundingBoxes))
        # print("memory fields:", memory.filledFields)

        # build prompt
        prompt = buildPrompt(state, memory, sampleUserData)
        content = [prompt]
        if includeScreenShot and state.screenshot:
            content.append(state.screenshot)


        # config response - json output
        config = types.GenerateContentConfig(response_mime_type="application/json", max_output_tokens=self.maxTokens)
        time.sleep(4)
        response = self.client.models.generate_content(
            model=self.model,
            contents=content,
            config=config)

        rawText = response.text
        return rawText