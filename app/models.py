from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, Literal


class FeedbackRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=240)
    emotion: Optional[int] = Field(None, ge=1, le=10, description="Emotional state from 1 (sad) to 10 (very happy)")
    # Anonymous technical context sent by the browser (device, network…)
    client_info: Optional[dict] = None
    fill_seconds: Optional[float] = Field(None, ge=0, le=86400)


class ClientInfoRequest(BaseModel):
    """Anonymous technical context posted when a student joins or leaves."""
    client_info: Optional[dict] = None
    fill_seconds: Optional[float] = Field(None, ge=0, le=86400)
    event: Optional[str] = Field(None, description="join | leave")


class ClientErrorRequest(BaseModel):
    """Browser-side JS error (anonymous)."""
    message: str = Field(..., max_length=500)
    source: Optional[str] = Field(None, max_length=300)
    line: Optional[int] = None
    column: Optional[int] = None
    stack: Optional[str] = Field(None, max_length=1500)
    url: Optional[str] = Field(None, max_length=300)


class ClientInfoResponse(BaseModel):
    status: str = "ok"


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


class ReceiptApprovalRequest(BaseModel):
    amount: int = Field(10, ge=1, description="Number of credits to add")
