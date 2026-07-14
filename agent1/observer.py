import base64
from agent1.data import pageState

class StateBuilder:

    # DOM
    async def get_dom(self, page):
        # return await page.evaluate("""
        # () => [...document.querySelectorAll(
        #     "a, button, input, textarea, select"
        # )].map(el => ({
        #     tag: el.tagName,
        #     text: (el.innerText || "").trim(),
        #     placeholder: el.placeholder || "",
        #     type: el.type || "",
        #     id: el.id,
        #     href: el.href || null
        # }))
        # """)

        return await page.evaluate("""
    () => [...document.querySelectorAll(
        "a, button, input, textarea, select, div.multiselect, [role='combobox'], [role='listbox']"
    )].map(el => {
        let selector;
        if (el.id) {
            selector = `#${el.id}`;
        } else if (el.name) {
            selector = `${el.tagName.toLowerCase()}[name='${el.name}']`;
        } else if (el.className && typeof el.className === "string" && el.className.trim()) {
            selector = `${el.tagName.toLowerCase()}.${el.className.trim().split(/\\s+/).join('.')}`;
        } else {
            selector = null;
        }
        return {
            tag: el.tagName,
            text: (el.innerText || "").trim(),
            placeholder: el.placeholder || "",
            type: el.type || "",
            id: el.id,
            name: el.name || "",
            className: el.className || "",
            href: el.href || null,
            value: el.value || "",
            selector: selector
        };
    })
    """)

    # bounding box
    async def get_bounding_boxes(self, page):

        return await page.evaluate("""
        () => [...document.querySelectorAll(
            "a, button, input, textarea, select"
        )]
        .map(el => {
            const r = el.getBoundingClientRect();

            return {
                tag: el.tagName,
                text: (el.innerText || "").trim(),

                x: r.x,
                y: r.y,
                width: r.width,
                height: r.height,

                visible: r.width > 0 && r.height > 0
            };
        })
        .filter(e => e.visible)
        """)

    # accessibility tree download
    async def get_accessibility(self, page):

        client = await page.context.new_cdp_session(page)

        tree = await client.send("Accessibility.getFullAXTree")

        interesting = {
            "button",
            "link",
            "textbox",
            "checkbox",
            "heading"
        }

        nodes = []

        for node in tree["nodes"]:

            role = node.get("role", {}).get("value")
            name = node.get("name", {}).get("value")

            if role in interesting:
                nodes.append({
                    "role": role,
                    "name": name
                })

        return nodes

    # get screenshot, i have collect screenshot, yet not used them in the logic, to be incorporated
    async def get_screenshot(self, page):
        image = await page.screenshot()

        return base64.b64encode(image).decode()

    # buiilding page state
    async def build(self, page, memory):
        state = pageState()

        if len(memory.history) == 0:
            state.previousAction = None
            state.lastError = None
        else:
            previousActionRecord = memory.history[-1]
            state.previousAction = previousActionRecord.action
            state.lastError = previousActionRecord.error

        state.currentUrl = page.url
        state.dom = await self.get_dom(page)
        state.accessibility = await self.get_accessibility(page)
        state.boundingBoxes = await self.get_bounding_boxes(page)
        state.screenshot = await self.get_screenshot(page)

        return state
