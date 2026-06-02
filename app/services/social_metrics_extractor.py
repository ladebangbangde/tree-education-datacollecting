import re
from app.schemas.recognition import Metrics, RecognitionResult


class SocialMetricsExtractor:
    BUSINESS_WORDS = [
        "留学", "申请", "澳洲", "英国", "美国", "欧洲", "加拿大", "新西兰", "香港", "新加坡",
        "院校", "专业", "签证", "移民", "雅思", "托福", "硕士", "本科", "预科", "博士",
        "避坑", "择校", "排名", "费用", "预算", "GPA", "均分", "保录", "背景", "文书"
    ]

    TITLE_NOISE = [
        "关注", "粉丝", "点赞", "评论", "收藏", "分享", "转发", "播放", "浏览", "观看", "获赞", "阅读",
        "首页", "推荐", "朋友", "消息", "扫一扫", "直播", "广告", "打开", "复制", "搜索", "音乐", "拍同款",
        "创作者服务中心", "数据中心", "作品数据", "查看更多", "暂无", "加载", "发布", "私信"
    ]

    def extract(self, text: str, platform: str | None = None, scene: str | None = None) -> RecognitionResult:
        clean = self._normalize_text(text or "")
        lines = self._lines(clean)
        metrics = Metrics(
            viewCount=self._find_number(clean, ["播放", "浏览", "阅读", "观看", "展现", "曝光"]),
            likeCount=self._find_number(clean, ["点赞", "获赞", "赞"]),
            commentCount=self._find_number(clean, ["评论"]),
            favoriteCount=self._find_number(clean, ["收藏"]),
            shareCount=self._find_number(clean, ["分享", "转发"]),
            followerCount=self._find_number(clean, ["粉丝"]),
            followerGain=self._find_number(clean, ["涨粉", "新增粉丝", "转粉", "粉丝增量", "净增粉丝"]),
            profileVisitCount=self._find_number(clean, ["主页访问", "主页访客", "主页浏览", "主页访问量"]),
            completionRate=self._find_percent(clean, ["完播率", "播放完成率", "看完率"]),
            interactionRate=self._find_percent(clean, ["互动率", "互动转化率"]),
            averageWatchSeconds=self._find_seconds(clean, ["平均播放时长", "平均观看时长", "人均观看时长", "平均看播时长"]),
        )
        candidates = self._title_candidates(lines, platform=platform)
        title = candidates[0] if candidates else None
        account_name = self._extract_account_name(lines)
        douyin_id = self._extract_douyin_id(clean)
        filled = sum(1 for v in metrics.model_dump().values() if v is not None)
        confidence = min(0.96, 0.35 + filled * 0.055 + (0.20 if title else 0) + (0.08 if account_name else 0) + (0.05 if douyin_id else 0))
        return RecognitionResult(
            accountName=account_name,
            douyinId=douyin_id,
            contentTitle=title,
            candidateTitles=candidates[:5],
            metrics=metrics,
            confidence=confidence,
        )

    def _normalize_text(self, text: str) -> str:
        value = text.replace("｜", "|").replace("：", ":").replace("，", ",")
        value = value.replace("％", "%").replace("Ｗ", "W").replace("ｗ", "w")
        return value

    def _find_number(self, text: str, labels: list[str]) -> int | None:
        for label in labels:
            patterns = [
                rf"{label}[^0-9一二三四五六七八九十百千万kwKW\.\-+]*([+\-]?[0-9]+(?:\.[0-9]+)?\s*[万千kwKW]?)",
                rf"([+\-]?[0-9]+(?:\.[0-9]+)?\s*[万千kwKW]?)[^0-9一二三四五六七八九十百千万kwKW\.]*{label}",
            ]
            for pattern in patterns:
                m = re.search(pattern, text, re.IGNORECASE)
                if m:
                    return self._parse_number(m.group(1))
        return None

    def _find_percent(self, text: str, labels: list[str]) -> str | None:
        for label in labels:
            patterns = [
                rf"{label}[^0-9\.]*([0-9]+(?:\.[0-9]+)?\s*%)",
                rf"([0-9]+(?:\.[0-9]+)?\s*%)[^0-9%]*{label}",
            ]
            for pattern in patterns:
                m = re.search(pattern, text, re.IGNORECASE)
                if m:
                    return m.group(1).replace(" ", "")
        return None

    def _find_seconds(self, text: str, labels: list[str]) -> float | None:
        for label in labels:
            patterns = [
                rf"{label}[^0-9\.]*([0-9]+(?:\.[0-9]+)?)\s*(秒|s|S)?",
                rf"([0-9]+(?:\.[0-9]+)?)\s*(秒|s|S)[^0-9]*{label}",
            ]
            for pattern in patterns:
                m = re.search(pattern, text, re.IGNORECASE)
                if m:
                    try:
                        return float(m.group(1))
                    except ValueError:
                        return None
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

    def _extract_account_name(self, lines: list[str]) -> str | None:
        labels = ["账号", "昵称", "作者", "账号名称", "达人名称", "用户"]
        for line in lines:
            for label in labels:
                if label in line:
                    value = line.split(label, 1)[-1].strip(" :|@")
                    value = self._clean_name(value)
                    if value:
                        return value[:80]
        for line in lines:
            value = self._clean_name(line)
            if value and value.startswith("@"):
                return value.strip("@")[:80]
        return None

    def _extract_douyin_id(self, text: str) -> str | None:
        patterns = [
            r"抖音号\s*[:：]?\s*([A-Za-z0-9_.\-]{4,40})",
            r"Douyin\s*ID\s*[:：]?\s*([A-Za-z0-9_.\-]{4,40})",
            r"ID\s*[:：]?\s*([A-Za-z0-9_.\-]{6,40})",
        ]
        for pattern in patterns:
            m = re.search(pattern, text, re.IGNORECASE)
            if m:
                return m.group(1).strip(" ._-")[:40]
        return None

    def _title_candidates(self, lines: list[str], platform: str | None = None) -> list[str]:
        explicit = self._explicit_titles(lines)
        candidates: dict[str, int] = {}
        for title in explicit:
            candidates[title] = max(candidates.get(title, 0), 120 + self._title_score(title))
        for line in lines:
            for part in self._split_title_like_line(line):
                title = self._clean_title_line(part)
                if self._is_valid_title_line(title):
                    candidates[title] = max(candidates.get(title, 0), self._title_score(title))
        if (platform or "").upper() == "DOUYIN":
            for line in lines:
                title = self._clean_douyin_line(line)
                if self._is_valid_title_line(title):
                    candidates[title] = max(candidates.get(title, 0), self._title_score(title) + 10)
        return [item[0] for item in sorted(candidates.items(), key=lambda x: (x[1], len(x[0])), reverse=True)]

    def _explicit_titles(self, lines: list[str]) -> list[str]:
        result: list[str] = []
        labels = ["作品标题", "视频标题", "封面标题", "内容标题", "图文标题", "标题", "文案"]
        for line in lines:
            for label in labels:
                if label in line:
                    value = line.split(label, 1)[-1].strip(" :|《》[]【】")
                    value = self._clean_title_line(value)
                    if self._is_valid_title_line(value):
                        result.append(value)
            for m in re.finditer(r"《(.{4,80})》", line):
                value = self._clean_title_line(m.group(1))
                if self._is_valid_title_line(value):
                    result.append(value)
        return result

    def _split_title_like_line(self, line: str) -> list[str]:
        pieces = re.split(r"[|｜]", line)
        result: list[str] = []
        for piece in pieces:
            piece = piece.strip()
            if len(piece) > 70:
                result.extend([p.strip() for p in re.split(r"[。；;]", piece) if p.strip()])
            else:
                result.append(piece)
        return result

    def _clean_douyin_line(self, line: str) -> str:
        value = self._clean_title_line(line)
        value = re.sub(r"^[@#][^\s]+\s*", "", value)
        value = re.sub(r"^[0-9]+[.、]\s*", "", value)
        return value.strip(" :|《》[]【】")

    def _clean_title_line(self, line: str | None) -> str:
        if not line:
            return ""
        value = re.sub(r"\s+", " ", line).strip()
        value = re.sub(r"^[-—_·•]+", "", value).strip()
        value = value.strip(" :|《》[]【】")
        value = re.sub(r"#\S+", "", value).strip()
        return value

    def _clean_name(self, line: str | None) -> str | None:
        if not line:
            return None
        value = re.sub(r"\s+", " ", line).strip()
        value = value.strip(" :|@")
        if not value or len(value) < 2:
            return None
        if any(word in value for word in ["关注", "粉丝", "点赞", "评论", "分享", "播放", "首页", "推荐"]):
            return None
        return value

    def _title_score(self, line: str) -> int:
        score = 0
        if re.search(r"[\u4e00-\u9fa5]", line):
            score += 25
        if any(word in line for word in self.BUSINESS_WORDS):
            score += 30
        if 6 <= len(line) <= 45:
            score += 18
        elif 46 <= len(line) <= 70:
            score += 8
        if any(mark in line for mark in ["？", "?", "！", "!", ":"]):
            score += 5
        if re.search(r"[0-9]", line) and any(word in line for word in ["年", "万", "GPA", "QS", "Top", "top"]):
            score += 4
        return score

    def _is_valid_title_line(self, line: str | None) -> bool:
        if not line:
            return False
        value = line.strip()
        if len(value) < 4 or len(value) > 120:
            return False
        lower = value.lower()
        if re.fullmatch(r"[0-9.万千kwKW%+\-\s秒sS]+", value):
            return False
        if len(re.findall(r"[\u4e00-\u9fa5A-Za-z]", value)) < 3:
            return False
        if any(word.lower() == lower for word in self.TITLE_NOISE):
            return False
        if any(word in value for word in ["点赞", "评论", "收藏", "分享", "播放", "粉丝", "获赞"]):
            return False
        if "抖音" in value and not any(word in value for word in self.BUSINESS_WORDS):
            return False
        return True

    def _lines(self, text: str) -> list[str]:
        result: list[str] = []
        for line in (text or "").splitlines():
            value = re.sub(r"\s+", " ", line).strip()
            if value:
                result.append(value)
        return result
