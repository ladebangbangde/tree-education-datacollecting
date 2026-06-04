from typing import Any
from pydantic import BaseModel, Field


class Metrics(BaseModel):
    viewCount: int | None = None
    likeCount: int | None = None
    commentCount: int | None = None
    favoriteCount: int | None = None
    shareCount: int | None = None
    followerCount: int | None = None
    followerGain: int | None = None
    completionRate: str | None = None
    interactionRate: str | None = None
    averageWatchSeconds: float | None = None
    profileVisitCount: int | None = None


class RecognitionResult(BaseModel):
    accountName: str | None = None
    accountId: str | None = None
    douyinId: str | None = None
    wechatChannelId: str | None = None
    contentTitle: str | None = None
    candidateTitles: list[str] = Field(default_factory=list)
    metrics: Metrics = Field(default_factory=Metrics)
    keyValueMetrics: dict[str, Any] = Field(default_factory=dict)
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
