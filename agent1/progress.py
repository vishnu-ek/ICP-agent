from agent1.data import ActionType


def progressCheck(curActionRecord, beforePageState, afterPageState, savePath):
    # change in url, dom or dom elements
    urlChanged = beforePageState.currentUrl != afterPageState.currentUrl
    domLenChanged = len(beforePageState.dom) != len(afterPageState.dom)
    domElementChanged = any(
        b != a for b, a in zip(beforePageState.dom, afterPageState.dom)
    )
    domChanged = domLenChanged or domElementChanged
    pathChanged = savePath is not None

    # return based on action for checking progess and exit
    if curActionRecord.action == ActionType.DOWNLOAD:
        info = "download process captured" if pathChanged else "no download detected"
        return (True, info, urlChanged, domChanged, pathChanged)

    if curActionRecord.action == ActionType.GOTO:
        info = "navigated" if urlChanged else "url did not change"
        return (True, info, urlChanged, domChanged, pathChanged)

    if curActionRecord.action in (ActionType.DONE, ActionType.ABORT):
        info = "terminated action"
        return (True, info, urlChanged, domChanged, pathChanged)

    if not urlChanged and not domChanged:
        info = "no observable change"
        return (False, info, urlChanged, domChanged, pathChanged)

    return (True, "page state changed", urlChanged, domChanged, pathChanged)
