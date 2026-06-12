"""
Vachan Study Bible Chatbot — Response Schemas
Pydantic models for all outgoing API responses.
"""

from typing import List, Optional
from pydantic import BaseModel


class ChatError(BaseModel):
    status: bool = False
    tag: Optional[str] = None
    message: Optional[str] = None


class ChatResponse(BaseModel):
    answer: str
    reference: str
    suggested_questions: List[str]
    is_general_knowledge: bool = False
    tokens_used: int = 0
    total_tokens_used: int = 0
    pending_tokens: int = 0
    requests_today: int = 0
    requests_this_minute: int = 0
    source: Optional[str] = None
    error: Optional[ChatError] = None


class SuggestedQuestionsOutput(BaseModel):
    suggested_questions: List[str]


class QARecord(BaseModel):
    Reference: str
    Question: str
    Response: str


class BookDatasetResponse(BaseModel):
    book: str
    total_questions: int
    data: List[QARecord]


class TokenStatusResponse(BaseModel):
    total_tokens_used: int
    pending_tokens: int
    limit: int
    requests_today: int
    requests_this_minute: int
    rpm_limit: int = 15
    rpd_limit: int = 1500
