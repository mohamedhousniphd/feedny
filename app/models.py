from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, Literal


class FeedbackRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=240)
    emotion: Optional[int] = Field(None, ge=1, le=10, description="Emotional state from 1 (sad) to 10 (very happy)")


class FeedbackResponse(BaseModel):
    id: int
    content: str
    device_id: str
    created_at: datetime
    included_in_analysis: bool
    emotion: Optional[int] = None


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


class ImportFeedbackItem(BaseModel):
    content: str
    device_id: Optional[str] = None
    created_at: Optional[datetime] = None
    included_in_analysis: Optional[bool] = False
    emotion: Optional[int] = Field(None, ge=1, le=10)
