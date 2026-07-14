from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class speakerEntry:
    name: str = ""
    title: str = ""
    company: str = ""
    sourcePage: int = -1

@dataclass
class chunkResult:
    pageNo: int
    speakers: List[speakerEntry] = field(default_factory=list)
    rawText: str = ""
    error: Optional[str] = None


@dataclass
class extractionMemory:
    goal: str
    pdfPath: str
    totalPages: int = 0
    chunkResults: List[chunkResult] = field(default_factory=list)


#########################################################################

@dataclass
class actionRecord:
    company: str
    iteration: int = 0
    success: bool = False
    decision: str = ""
    thought: str = ""
    lookupQuery: str = ""
    error: Optional[str] = None
    gatheredContext: Optional[str] = None

@dataclass
class icpFit:
    company: str
    speakers: list[tuple[str, str]]
    fitScore: str = ""          # e.g. "high" / "medium" / "low"
    reasoning: str = ""
    itsActionRecord: List[actionRecord] = field(default_factory=list)
    

@dataclass
class icpAgentMemory:
    goal:str = ""
    pdfPath:str = ""
    allFits: List[icpFit] = field(default_factory=list)
