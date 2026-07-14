import os
import requests
import asyncio
from agent1.data import ActionType


class executor():
    def __init__(self, page, memory, downloadDir="./downloads", defaultTimeout=10000):
        self.page = page
        self.memory = memory
        self.downloadDir = downloadDir
        self.defaultTimeout = defaultTimeout
        self.savePath = None

    async def execute(self, action):
        os.makedirs(self.downloadDir, exist_ok=True)
        self.savePath = None

        # page action 
        try:
            act = action.action.lower()
        # navigation
            if act == ActionType.GOTO:
                await self.page.goto(action.value, wait_until="domcontentloaded")
                self.memory.visitedUrls.add(action.value)
        # fill
            elif act == ActionType.FILL:
                await self.page.wait_for_selector(action.selector, state="visible", timeout=self.defaultTimeout)
                await self.page.locator(action.selector).fill(action.value, timeout=self.defaultTimeout)
                self.memory.filledFields[action.selector] = action.value
        # select
            elif act == ActionType.SELECT:
                await self.page.wait_for_selector(action.selector, state="visible", timeout=self.defaultTimeout)

                try:
                    await self.page.select_option(action.selector, label=action.value)
                except Exception:
                    await self.page.select_option(action.selector, value=action.value)
                self.memory.filledFields[action.selector] = action.value
        # click
            elif act == ActionType.CLICK:
                await self.page.wait_for_selector(action.selector, state="visible", timeout=self.defaultTimeout)

                try:
                    async with self.page.context.expect_page(timeout=self.defaultTimeout) as newPageInfo:
                        await self.page.click(action.selector)

                    # Case A: Click opened a new tab (e.g. PDF viewer)
                    newTab = await newPageInfo.value
                    await newTab.wait_for_load_state()
                    pdfUrl = newTab.url
                    print(f"New tab detected: {pdfUrl}")

                    self.savePath = os.path.join(self.downloadDir, "agenda.pdf")

                    print("Downloading PDF from tab...") 
                    response = requests.get(pdfUrl, timeout=10)
                    response.raise_for_status()
                    with open(self.savePath, "wb") as f:
                            f.write(response.content)

                    # response = await self.page.context.request.get(pdfUrl)
                    # pdf_bytes = await response.body()

                    # with open(self.savePath, "wb") as f:
                    #     f.write(pdf_bytes)

                    print(f"PDF successfully saved to: {self.savePath}")
                    self.memory.extractedData["downloadedFilePath"] = self.savePath
                    await newTab.close()
                    return "downloaded", self.savePath

                except asyncio.TimeoutError:
                    #Case B: direct file download in the same tab
                    print("No new tab opened. Checking for standard direct file download stream...")
                    try:
                        async with self.page.expect_download(timeout=self.defaultTimeout) as download_info:
                            await self.page.click(action.selector)

                        download = await download_info.value
                        self.savePath = os.path.join(self.downloadDir, "agenda.pdf")
                        await download.save_as(self.savePath)
                        print(f"Direct download successfully saved to: {self.savePath}")
                        self.memory.extractedData["downloadedFilePath"] = self.savePath
                        return "downloaded", self.savePath

                    except Exception:
                        print("Regular click completed (no download triggered).")
            # wait
            elif act == ActionType.WAIT:
                waitSeconds = int(action.value) if str(action.value).isdigit() else 2
                print(f"Sleeping for {waitSeconds} seconds...")
                await asyncio.sleep(waitSeconds)
            # finish or abort
            elif act in (ActionType.DONE, ActionType.ABORT):
                print(f"Finish action declared. Reason: {action.reason}")
                return "done/abort", self.savePath

            else:
                raise ValueError(f"Unsupported action type: {action.action}")

        except Exception as e:
            raise Exception(f"Failed to execute {action.action} on '{action.selector}': {e}")

        return "not_downloaded", None
