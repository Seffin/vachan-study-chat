"""
Vachan Study Bible Chatbot — Core Models
Defines ConversationState and ResponseMode Enum to prevent topic drift and manage elaboration workflows.
"""

from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any
from enum import Enum


class ResponseMode(str, Enum):
    DIRECT_HIT = "direct_hit"
    ELABORATE = "elaborate"
    GENERATE = "generate"


@dataclass
class ConversationState:
    original_question: str
    last_user_question: str
    previous_assistant_answer: str
    dataset_answer_reference: Optional[str]
    elaboration_depth: int
    detected_language: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConversationState":
        return cls(
            original_question=data.get("original_question", ""),
            last_user_question=data.get("last_user_question", ""),
            previous_assistant_answer=data.get("previous_assistant_answer", ""),
            dataset_answer_reference=data.get("dataset_answer_reference"),
            elaboration_depth=int(data.get("elaboration_depth", 0)),
            detected_language=data.get("detected_language", "en")
        )
