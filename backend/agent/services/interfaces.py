from dataclasses import dataclass
from typing import List, Optional


@dataclass
class ResearchInput:
    company_name: str
    domain: Optional[str] = None
    country: Optional[str] = None


@dataclass
class ResearchOutput:
    has_website: bool
    detected_industry: str
    detected_tools: List[str]
    summary: str
    confidence: float


@dataclass
class DraftInput:
    research: ResearchOutput
    brain_context: dict


@dataclass
class DraftOutput:
    subject: str
    body: str
    pitch_angle: str
