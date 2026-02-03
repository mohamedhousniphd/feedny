from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, Literal


class FeedbackRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=240)


class FeedbackResponse(BaseModel):
    id: int
    content: str
    device_id: str
    created_at: datetime
    included_in_analysis: bool


class FeedbackListResponse(BaseModel):
    feedbacks: list[FeedbackResponse]
    total: int


class TeacherLoginRequest(BaseModel):
    password: str


class TeacherLoginResponse(BaseModel):
    success: bool
    token: Optional[str] = None
    message: str


class AnalyzeRequest(BaseModel):
    feedback_ids: list[int]
    context: str = Field(..., min_length=1, max_length=1000)


class AnalyzeResponse(BaseModel):
    summary: str
    wordcloud_data: dict


class StatusResponse(BaseModel):
    collection_open: bool
    message: str


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
