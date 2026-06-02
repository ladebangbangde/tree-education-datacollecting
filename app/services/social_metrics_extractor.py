import re
from app.schemas.recognition import Metrics, RecognitionResult


class SocialMetricsExtractor:
    def extract(self, text: str, platform: str | None = None, scene: str | None = None) -> RecognitionResult:
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
        title = self._guess_title(clean, platform=platform, scene=scene)
        return RecognitionResult(
            accountName=self._line_after(clean, ["账号", "昵称", "作者", "抖音号"]),
            contentTitle=title,
            metrics=metrics,
            confidence=min(0.95, 0.45 + filled * 0.08 + (0.18 if title else 0)),
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
        for line in self._lines(text):
            for label in labels:
                if label in line:
                    value = line.split(label, 1)[-1].strip(" ：:|@")
                    if value and self._is_valid_title_line(value):
                        return value[:80]
        return None

    def _guess_title(self, text: str, platform: str | None = None, scene: str | None = None) -> str | None:
        lines = self._lines(text)
        explicit = self._explicit_title(lines)
        if explicit:
            return explicit
        if (platform or "").upper() == "DOUYIN":
            douyin_title = self._douyin_cover_title(lines)
            if douyin_title:
                return douyin_title
        for line in lines:
            if self._is_valid_title_line(line):
                return line[:120]
        return None

    def _explicit_title(self, lines: list[str]) -> str | None:
        labels = ["作品标题", "视频标题", "封面标题", "标题", "文案", "内容标题"]
        for line in lines:
            for label in labels:
                if label in line:
                    value = line.split(label, 1)[-1].strip(" ：:|《》")
                    if self._is_valid_title_line(value):
                        return value[:120]
            m = re.search(r"《(.{4,80})》", line)
            if m and self._is_valid_title_line(m.group(1)):
                return m.group(1)[:120]
        return None

    def _douyin_cover_title(self, lines: list[str]) -> str | None:
        candidates: list[str] = []
        for line in lines:
            cleaned = self._clean_douyin_line(line)
            if self._is_valid_title_line(cleaned):
                candidates.append(cleaned)
        if not candidates:
            return None
        candidates.sort(key=lambda x: (self._title_score(x), len(x)), reverse=True)
        return candidates[0][:120]

    def _clean_douyin_line(self, line: str) -> str:
        value = line.strip()
        value = re.sub(r"^[@#][^\s]+\s*", "", value)
        value = re.sub(r"^[0-9]+[.、]\s*", "", value)
        value = value.strip(" ：:|《》[]【】")
        return value

    def _title_score(self, line: str) -> int:
        score = 0
        if re.search(r"[\u4e00-\u9fa5]", line):
            score += 20
        if any(word in line for word in ["留学", "申请", "澳洲", "英国", "美国", "欧洲", "院校", "专业", "签证", "避坑"]):
            score += 20
        if 8 <= len(line) <= 40:
            score += 15
        if any(mark in line for mark in ["？", "?", "！", "!", "：", ":"]):
            score += 5
        return score

    def _is_valid_title_line(self, line: str | None) -> bool:
        if not line:
            return False
        value = line.strip()
        if len(value) < 4 or len(value) > 120:
            return False
        noise = [
            "抖音", "douyin", "关注", "粉丝", "点赞", "评论", "收藏", "分享", "转发", "播放", "浏览", "观看", "获赞",
            "首页", "推荐", "朋友", "消息", "我", "扫一扫", "直播", "广告", "打开", "复制", "搜索", "音乐", "拍同款"
        ]
        lower = value.lower()
        if any(word.lower() in lower for word in noise):
            return False
        if re.fullmatch(r"[0-9.万千kwKW\s]+", value):
            return False
        if len(re.findall(r"[\u4e00-\u9fa5A-Za-z]", value)) < 3:
            return False
        return True

    def _lines(self, text: str) -> list[str]:
        result: list[str] = []
        for line in (text or "").splitlines():
            value = re.sub(r"\s+", " ", line).strip()
            if value:
                result.append(value)
        return result
