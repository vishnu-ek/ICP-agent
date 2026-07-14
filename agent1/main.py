import os
import logging
import asyncio

from google import genai

from agent1.agent import browserAgent
from dotenv import load_dotenv
from tools.wrbTool import agendaDownloader
from playwright.async_api import async_playwright


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

load_dotenv()

async def main():
    # attempting rule based downloader:
    downloaded = await agendaDownloader()

    if downloaded:
        print("downloader succeeded - skipping llm")
        return
    
    print("downloader failed — using llm")

    # creating a client
    client = genai.Client(api_key=os.environ.get("API_KEY"))
    deploymentName = "gemini-2.0-flash" # just a place holder

    # initiating browser agent
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto("https://fieldserviceusa.wbresearch.com/agenda-mc", wait_until="domcontentloaded")

        goal = "Download the agenda PDF"
        agent1 = browserAgent(page, client, goal, deploymentName, maxTokens=1024, maxSteps=10, maxErrors=3, maxSameActions=3)
        result = await agent1.run()

        print("Success:", result.success)
        print("Steps taken:", result.steps)
        if result.downloadedPath:
            print("Downloaded:", result.downloadedPath)
        if result.info:
            print("Info:", result.info)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
