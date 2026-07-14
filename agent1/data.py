from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Set


class ActionType(str, Enum):
    CLICK = "click"
    FILL = "fill"
    PRESS = "press"
    SELECT = "select"
    WAIT = "wait"
    GOTO = "goto"
    SCROLL = "scroll"
    DOWNLOAD = "download"
    DONE = "done"
    ABORT = "abort"

@dataclass
class pageState:
    currentUrl: str = ""
    previousAction: Optional[str] = None
    lastError: Optional[str] = None

    dom: List[Dict] = field(default_factory=list)
    accessibility: List[Dict] = field(default_factory=list)
    boundingBoxes: List[Dict] = field(default_factory=list)
    screenshot: str = ""       # base64 string


@dataclass
class actionRecord:
    step: int
    timestamp: str
    action: str = ""
    rawText: str = ""
    thought: str = ""
    value: str = ""
    selector: str = ""
    reason: str = ""
    success: bool = False
    error: Optional[str] = None
    url: str = ""
    state: Optional[pageState] = None
    validation: Optional[list] = None
    


@dataclass
class agentMemory:
    goal: str
    visitedUrls: Set[str] = field(default_factory=set)
    filledFields: Dict[str, str] = field(default_factory=dict)
    extractedData: Dict = field(default_factory=dict)
    notes: List[str] = field(default_factory=list)
    history: List[actionRecord] = field(default_factory=list)


@dataclass
class returnResult:
    success: bool
    steps: int
    memory: agentMemory
    downloadedPath: Optional[str] = None
    info: Optional[str] = None
