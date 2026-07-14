import os
import asyncio

from google import genai
from dotenv import load_dotenv
from playwright.async_api import async_playwright

from agent1.agent import browserAgent
from tools.wrbTool import agendaDownloader
from agent2.icpAgent import icpAgent
from tools.saveResult import exportToExcel

load_dotenv()
# stage 1
async def runDownloadStage(client, model):

    # Try the cheap rule-based downloader first.
    downloaded, downloadedPath = await agendaDownloader()
    if downloaded:
        print("rule based downloader success")
        return True, downloadedPath, "rule based download"

    print("rule based failed, using llm")

    # fall back to LLM
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        await page.goto("https://fieldserviceusa.wbresearch.com/agenda-mc", wait_until="domcontentloaded") # domcontentloaded

        goal = "Download the agenda PDF"
        agent1 = browserAgent(page, client, goal, model, maxTokens=1024, maxSteps=10, maxErrors=3, maxSameActions=3)
        result1 = await agent1.run()

        await browser.close()

        print(f"agent1 success={result1.success} steps={result1.steps} info={result1.info}")

        if not result1.success or not result1.downloadedPath:
            return False, None, result1.info

        return True, result1.downloadedPath, "agent based download"


# stage 2
def runExtractionStage(client, model, pdfPath):
    # run extraction and ICP evaluation pipeline
    goal = "Extract speakers and companies and find ICP fit for ascendo.ai"
    agent2 = icpAgent(client, model, goal, pdfPath, maxTokens=1024)
    return agent2.run()


async def runPipeline():

    client = genai.Client(api_key=os.environ.get("GEMINI_KEY"))
    deploymentName = "gemini-2.0-flash"  # NOTE: placeholder — any relevant model can be used.
    
    # stage1
    downloadOk, pdfPath, downloadInfo = await runDownloadStage(client, deploymentName)

    if not downloadOk:
        print(f"\nPipeline stoped at stage 1. Reason: {downloadInfo}")
        return {"success": False, "stage": "download", "info": downloadInfo}

    if not os.path.exists(pdfPath):
        print(f"\nPipeline aborted: stage 1 reported success but file not found at {pdfPath}")
        return {"success": False, "stage": "download",  "info": f"reported success but file missing at {pdfPath}"}

    print(f"\n stage 1 complete ({downloadInfo}). PDF at: {pdfPath}")

    # stage2
    result2 = runExtractionStage(client, deploymentName, pdfPath)
    exportToExcel(result2)

if __name__ == "__main__":
    asyncio.run(runPipeline())