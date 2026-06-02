import re
from app.schemas.recognition import Metrics, RecognitionResult


class SocialMetricsExtractor:
    def extract(self, text: str) -> RecognitionResult:
        clean = text or ""
        metrics = Metrics(
            viewCount=self._find(clean, ["播放", "浏览", "阅读", "观看"]),
            likeCount=self._find(clean, ["点赞", "获赞", "赞"]),
            commentCount=self._find(clean, ["评论"]),
            favoriteCount=self._find(clean, ["收藏"]),
            shareCount=self._find(clean, ["分享", "转发"]),
            followerCount=self._find(clean, ["粉丝"]),
        )
        filled = sum(1 for v in metrics.model_dump().values() if v is not None)
        return RecognitionResult(
            accountName=self._line_after(clean, ["账号", "昵称"]),
            contentTitle=self._guess_title(clean),
            metrics=metrics,
            confidence=min(0.95, 0.35 + filled * 0.1),
        )

    def _find(self, text: str, labels: list[str]) -> int | None:
        for label in labels:
            patterns = [
                rf"{label}[^0-9一二三四五六七八九十百千万kwKW\.]*([0-9]+(?:\.[0-9]+)?\s*[万千kwKW]?)",
                rf"([0-9]+(?:\.[0-9]+)?\s*[万千kwKW]?)[^0-9一二三四五六七八九十百千万kwKW\.]*{label}",
            ]
            for pattern in patterns:
                m = re.search(pattern, text)
                if m:
                    return self._parse_number(m.group(1))
        return None

    def _parse_number(self, value: str) -> int | None:
        s = value.strip().replace(" ", "").lower()
        multiplier = 1
        if s.endswith("万") or s.endswith("w"):
            multiplier = 10000
            s = s[:-1]
        elif s.endswith("千") or s.endswith("k"):
            multiplier = 1000
            s = s[:-1]
        try:
            return int(float(s) * multiplier)
        except ValueError:
            return None

    def _line_after(self, text: str, labels: list[str]) -> str | None:
        for line in text.splitlines():
            for label in labels:
                if label in line:
                    value = line.split(label, 1)[-1].strip(" ：:|")
                    if value:
                        return value[:80]
        return None

    def _guess_title(self, text: str) -> str | None:
        for line in text.splitlines():
            line = line.strip()
            if len(line) >= 6 and not any(x in line for x in ["点赞", "评论", "收藏", "播放", "粉丝"]):
                return line[:120]
        return None
