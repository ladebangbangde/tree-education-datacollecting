from typing import Any
from pydantic import BaseModel, Field


class Metrics(BaseModel):
    """Backward-compatible common metrics.

    OA can keep reading this object during migration. New code should prefer
    imageTextStats / videoStats according to result.contentType.
    """

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


class ImageTextStats(BaseModel):
    """Stats that only make sense for image-text / note content."""

    readCount: int | None = None
    viewCount: int | None = None
    likeCount: int | None = None
    commentCount: int | None = None
    favoriteCount: int | None = None
    shareCount: int | None = None
    imageCount: int | None = None
    coverClickRate: str | None = None
    copyExpandRate: str | None = None
    copyFinishRate: str | None = None
    commentEnterRate: str | None = None
    slideAwayRate: str | None = None
    followerGain: int | None = None


class VideoStats(BaseModel):
    """Stats that only make sense for video content."""

    playCount: int | None = None
    exposureCount: int | None = None
    likeCount: int | None = None
    commentCount: int | None = None
    favoriteCount: int | None = None
    shareCount: int | None = None
    completionRate: str | None = None
    fiveSecondCompletionRate: str | None = None
    averageWatchSeconds: float | None = None
    averageWatchText: str | None = None
    durationSeconds: float | None = None
    durationText: str | None = None
    interactionRate: str | None = None
    followerGain: int | None = None
    profileVisitCount: int | None = None


class RecognitionResult(BaseModel):
    accountName: str | None = None
    accountId: str | None = None
    douyinId: str | None = None
    wechatChannelId: str | None = None
    contentType: str | None = None  # IMAGE_TEXT / VIDEO / ACCOUNT_OVERVIEW / UNKNOWN
    contentTitle: str | None = None
    candidateTitles: list[str] = Field(default_factory=list)
    metrics: Metrics = Field(default_factory=Metrics)
    imageTextStats: ImageTextStats | None = None
    videoStats: VideoStats | None = None
    keyValueMetrics: dict[str, Any] = Field(default_factory=dict)
    confidence: float = 0.0


class RecognitionResponse(BaseModel):
    requestId: str
    engine: str
    platform: str
    scene: str
    contentType: str | None = None
    rawText: str
    result: RecognitionResult
    warnings: list[str] = Field(default_factory=list)
    elapsedMs: int = 0


class BatchRecognitionResponse(BaseModel):
    total: int
    results: list[RecognitionResponse]
