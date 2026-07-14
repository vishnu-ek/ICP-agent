import json
import re
import time
from google.genai import types
from agent2.data2 import speakerEntry, chunkResult


def buildPrompt(eachPage) -> str:
    prompt = f"""
                You are extracting structured data from one of a page of conference agenda PDF. It is given below.

                From the text below, extract EVERY speaker mentioned, along with their
                job title and company/organization, if present. Some pages may contain
                no speakers at all (agenda headers, sponsor pages, etc.) — in that case
                return an empty list.

                Rules:
                - Only extract real named individuals (not "TBC", "TBA", panel names alone).
                - If a company is mentioned without a named speaker, skip it (we only care
                  about speaker-company pairs).
                - Do not invent or guess missing fields; use an empty string if unknown.
                - Return ONLY valid JSON, no markdown fences, no preamble.

                Output JSON schema:
                {{
                  "speakers": [
                    {{"name": "<full name>", "title": "<job title>", "company": "<company name>"}}
                  ]
                }}

                page of conference agenda PDF:
                {eachPage}
                """
    return prompt


def parseText(pageNo, rawText):
    match = re.search(r"\{.*\}", rawText, re.DOTALL)
    if not match:
        return chunkResult(pageNo, error="No text found in extractor response")

    try:
        data = json.loads(match.group(0))
    except Exception as e:
        return chunkResult(pageNo, error=f"Invalid JSON: {e}")

    speakerCompany = []
    for item in data.get("speakers") or []:
        name = (item.get("name") or "").strip()
        
        if not name:
            continue
        
        title = (item.get("title") or "").strip()
        company = (item.get("company") or "").strip()

        speakerCompany.append(speakerEntry(name=name, title=title, company=company, sourcePage=pageNo))

    return chunkResult(pageNo, speakers=speakerCompany, rawText=rawText, error=None)

class SpeakerExtractor:
    """Runs the LLM extraction call for a single text chunk."""

    def __init__(self, client, model, maxTokens=2048):
        self.client = client
        self.model = model
        self.maxTokens = maxTokens

    def extract(self, pageNo, eachPage):
        prompt = buildPrompt(eachPage)

        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            max_output_tokens=self.maxTokens,
        )
        # rate limit hit and back off routine to be added. 
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=[prompt],
                config=config,
            )
            rawText = response.text
        
        except Exception as e:
            return chunkResult(pageNo, error=f"LLM call failed: {e}")
        return parseText(pageNo, rawText)
