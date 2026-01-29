from typing import List, Dict, TypedDict

class FailureReport(TypedDict):
    files: List[str]
    summary: str

SectionReport = Dict[str, FailureReport]
TestReport = Dict[str, SectionReport]
