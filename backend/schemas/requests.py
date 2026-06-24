"""
Vachan Study Bible Chatbot — Request Schemas
Pydantic models for all incoming API requests.
"""

from typing import List, Optional
from pydantic import BaseModel


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    book: str
    message: str
    history: Optional[List[ChatMessage]] = []
    conversation_state: Optional[dict] = None
    suggested_question_id: Optional[str] = None
    is_suggested_question: Optional[bool] = False


class EnvUpdateRequest(BaseModel):
    key: str
    value: str
