import asyncio
import os
import requests
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

async def agendaDownloader():
    downloadedStatus = False
    os.makedirs("./downloads", exist_ok=True)
    path = os.path.join("./downloads", "agenda.pdf")
    try:
        async with async_playwright() as p:
            # Launch headed browser so you can watch the action (set headless=True for background runs)
            browser = await p.chromium.launch(headless=False)
            
            # Configure context to accept file downloads
            context = await browser.new_context(accept_downloads=True)
            page = await context.new_page()

            # 1. Navigate to the page
            print("Navigating to the page...")
            await page.goto("https://fieldserviceusa.wbresearch.com/agenda-mc", wait_until = 'domcontentloaded',timeout=60000)

            # 2. Enter details (Adjust the selectors 'input[name=...]' to match your target website)
            print("Filling in form details...")
            await page.locator("input[name='email']").fill("userName@gmail.com")

            # 3. Click the initial submit/download button
            print("Submitting the form...")
            await page.locator("button.step-1-cont").click()
            
            print("Checking if the download button is already present...")
            download_btn_selector = "a.btn.btn-lg.btn-danger" 
            try:
                await page.wait_for_selector(download_btn_selector, state="visible", timeout=40000)
                needsFullForm = False
            except PlaywrightTimeoutError:
                needsFullForm = True

            if needsFullForm:
                await page.locator("input[name='first_name']").fill("john")
                await page.locator("input[name='last_name']").fill("doe")
                await page.locator("input[name='tel']").fill("865664564")
                await page.locator("input[name='job_title']").fill("reasearcher")
                await page.locator("input[name='organization']").fill("ascendo.ai")

                # Open dropdown
                await page.locator("div.multiselect.custom-select").click()

                # Wait until dropdown becomes visible
                await page.wait_for_selector(".multiselect__content", state="visible", timeout=10000)
                await page.locator("span.multiselect__option >> text='India'").click()
                await page.locator("button.step-2-cont").click()

                # 4. Wait for the download page to appear and capture the download event
                print("Waiting for download page and trigger...")

                await page.wait_for_url("**?-ty-b", timeout=60000)
                await page.wait_for_selector(download_btn_selector, state="visible", timeout=60000)
            else:
                print("enter details skipped")

            # Wait until the Download Agenda button appears
            download_btn = page.locator("a.btn.btn-lg.btn-danger")
            try:               
                async with page.expect_download() as download_info:
                    await download_btn.click()
                  
                download = await download_info.value
                
                await download.save_as(path)
                print("Download complete: agenda.pdf")
            
            except PlaywrightTimeoutError:
                if len(context.pages) > 1:

                    newTab = context.pages[-1]
                    await newTab.wait_for_load_state()
                    
                    pdfUrl = newTab.url

                    response = requests.get(pdfUrl, timeout=10)
                    response.raise_for_status()
                    
                    path = os.path.join("./downloads", "agenda.pdf")
                    with open(path, "wb") as f:
                            f.write(response.content)

                    print(f"PDF successfully saved from tab to: {[path]}")
                    await newTab.close()
                else:
                    print("Error: No standard download detected and no new tab was opened.")
                    return False

            await context.close()
            await browser.close()

            return True, path
        
    except Exception as e:
        print(e)
        return False, path