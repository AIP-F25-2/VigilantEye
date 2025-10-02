from pydantic import BaseModel
from typing import List, Optional, Literal

Role = Literal["system", "user", "assistant"]

class Message(BaseModel):
    role: Role
    content: str

class ChatRequest(BaseModel):
    model: Optional[str] = None
    messages: List[Message]
    max_tokens: int = 512
    temperature: float = 0.7
    stream: bool = False
    session_id: Optional[str] = None

class ChatChunk(BaseModel):
    content: str