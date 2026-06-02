from typing import Any
from pydantic import BaseModel, Field


class Metrics(BaseModel):
    viewCount: int | None = None
    likeCount: int | None = None
    commentCount: int | None = None
    favoriteCount: int | None = None
    shareCount: int | None = None
    followerCount: int | None = None


class RecognitionResult(BaseModel):
    accountName: str | None = None
    contentTitle: str | None = None
    metrics: Metrics = Field(default_factory=Metrics)
    confidence: float = 0.0


class RecognitionResponse(BaseModel):
    requestId: str
    engine: str
    platform: str
    scene: str
    rawText: str
    result: RecognitionResult
    warnings: list[str] = Field(default_factory=list)
    elapsedMs: int = 0


class BatchRecognitionResponse(BaseModel):
    total: int
    results: list[RecognitionResponse]
