# Agenda ICP Pipeline

I have built a two-stage pipeline that downloads a conference agenda PDF, extracts speaker/company
data from it, and evaluates which companies fit ascendo.ai's Ideal Customer Profile (ICP).

## What it does

1. **Stage 1 — Download (`agent1/`)**
   First it just tries the fast way: `tools/wrbTool.py` fills out the form with
   Playwright and clicks download. Works most of the time. If the site layout changes
   or the form breaks, it falls back to an actual LLM agent (`agent1/agent.py`) that
   looks at the page, decides what to click/fill next, does it, checks if anything
   changed, and repeats until it either gets the PDF or gives up after a few errors.

2. **Stage 2 — Extract & Validate (`agent2/`)**
   Goes through the PDF page by page (can't dump the whole thing into one prompt,
   it's too long), asks the LLM to pull out speaker name / title / company for each
   page. Once we've got everyone, it groups people by company and runs each company
   through a little decision loop - the model either says "I know enough about this
   company already" or "let me look this up first" (uses `companyLookUp.py`, a Serper
   search wrapper) before giving a final high/medium/low verdict.

   I made this one an actual loop instead of just dumping every company into one
   giant prompt because otherwise the model just guesses on unfamiliar names instead
   of admitting it doesn't know.

3. **`pipeline.py`** (project root) ties both stages together: it runs stage 1, checks
   the result was actually successful and the file exists, then hands the real PDF
   path into stage 2. No file-path guessing between stages.

## Project structure

```
.
├── .env
├── pipeline.py              # entry point — run this
├── agent1/                  # PDF download agent
│   ├── agent.py             # browserAgent: observe → decide → act → check loop
│   ├── data.py               # dataclasses: pageState, actionRecord, agentMemory, returnResult
│   ├── executor.py           # executes click/fill/select/wait/goto/download actions
│   ├── observer.py           # builds page state (DOM, accessibility tree, screenshot)
│   ├── planner.py             # prompts the LLM for the next action
│   ├── progress.py            # checks whether the last action actually changed anything
│   ├── memoryManager.py        # helper for recording/querying agent history
│   └── main.py                 # standalone runner for agent1 only (see note below)
├── agent2/                  # PDF extraction + ICP validation agent
│   ├── icpAgent.py             # orchestrator: read PDF → extract speakers → run ICP loop
│   ├── pdfReader.py             # pdfplumber wrapper, extracts text per page
│   ├── namedEntityExtractor.py   # LLM call: extract speakers/titles/companies from a page
│   ├── icpvalidatorAgent.py       # per-company agentic ICP decision loop
│   ├── companyLookUp.py            # web search tool used when a company is unfamiliar
│   └── data2.py                     # dataclasses: speakerEntry, icpFit, actionRecord, etc.
└── tools/
    └── wrbTool.py             # rule-based Playwright downloader (fast path, tried first)
```

## Setup

```bash
pip install playwright pdfplumber requests python-dotenv google-genai openpyxl
playwright install chromium
```
or 

```bash
pip install -r requirements.txt
playwright install chromium


Create a `.env` file in the project root:

```
API_KEY=your_gemini_api_key
SERPER_API_KEY=your_serper_api_key   # optional — enables real company lookups
```

If `SERPER_API_KEY` isn't set, the ICP agent still runs — it just tells the model that no
external lookup is available, so the model has to reason from speaker titles and
company-name recognition alone.

## Running it

From the project root:

```bash
python pipeline.py
```
This runs both stages end to end and prints:
- Download stage result (which method succeeded, and the PDF path)
- Total unique companies found
- Per-company ICP fit verdict with reasoning

### Running a single stage

Stage 1 only:
```bash
python -m agent1.main
```
(has to be run with -m from the root, not `python agent1/main.py` directly, since
the imports assume the project root is on the path)

Stage 2 only (if you already have a PDF):
```python
from google import genai
from agent2.icpAgent import icpAgent

client = genai.Client(api_key="...")
agent = icpAgent(client, "gemini-2.0-flash", goal="Extract speakers and find ICP fit for ascendo.ai",
                  pdfPath="./downloads/agenda.pdf")
memory, results = agent.run()
```

## Notes / known limitations

- `deploymentName = "gemini-2.0-flash"` is a placeholder in both `pipeline.py` and
  `agent1/main.py` — confirm the actual model id you want before deploying.
- The ICP validator makes one LLM call per company per iteration (up to
  `maxIterations`, default 3)


## usage of agents for field service community:
Field service teams are drowning in information. but they are scattered across PDFs, CRMs, knowledge bases, and as raw knowledge in technician's brain. AI agents can be build to efficiently put that knowledge to use.
- Agents make their life easy by acting as frontline responders, active 24/7, instantly deciding, responding to queries, and     perform actions.
- Agents augument technician's work by serving as intelligent assistant. It can run through tonnes of knowlege and tell in instant what can be done to fix the issue thereby imporving first-time fix rates. This is something that we are trying to do in my company Bosch.
- it can do prediction by monitoring the fieild variables and can take preventive actions, and make corrections to avoid future occurance all together

 