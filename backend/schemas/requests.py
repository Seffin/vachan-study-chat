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


class EnvUpdateRequest(BaseModel):
    key: str
    value: str
