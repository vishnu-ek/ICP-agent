import os
import requests

class CompanyLookupTool:
    def __init__(self, apiKey=None, timeout=10):
        self.apiKey = apiKey or os.environ.get("SERPER_API_KEY")
        self.timeout = timeout

    def available(self) -> bool:
        return bool(self.apiKey)

    # to get a snippet of what the company does
    def lookup(self, companyName: str) -> str:
        if not companyName.strip():
            return "No company name provided; cannot look up."

        if not self.available():
            return ("No search backend configured (missing SERPER_API_KEY). "
                     "Proceed using only the information already available.")

        # getting details
        try:
            return self._searchWeb(companyName)
        except Exception as e:
            return f"Lookup failed for '{companyName}': {e}"

    def _searchWeb(self, companyName: str) -> str:
        query = f"{companyName} company industry what they do"

        response = requests.post(
            "https://google.serper.dev/search",
            headers={"X-API-KEY": self.apiKey, "Content-Type": "application/json"},
            json={"q": query, "num": 5},
            timeout=self.timeout,
        )
        response.raise_for_status()
        data = response.json()

        snippets = []

        # extracting snippets
        if "knowledgeGraph" in data:
            kg = data["knowledgeGraph"]
            title = kg.get("title", "")
            desc = kg.get("description", "")
            if title or desc:
                snippets.append(f"{title}: {desc}")

        for item in data.get("organic", [])[:3]:
            title = item.get("title", "")
            snippet = item.get("snippet", "")
            if snippet:
                snippets.append(f"{title} — {snippet}")

        if not snippets:
            return f"No useful search results found for '{companyName}'."

        return "\n".join(snippets)