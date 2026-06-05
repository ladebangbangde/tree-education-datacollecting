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
        "创作者服务中心", "数据中心", "作品数据", "查看更多", "暂无", "加载", "发布", "私信", "添加朋友", "编辑主页",
        "作品数据详情", "总览", "流量分析", "观众分析", "切换作品", "设置观测>", "新增累计", "每小时", "每天", "DOUO", "DOU+"
    ]

    ACCOUNT_PAGE_HINTS = [
        "抖音号", "视频号", "微信号", "小红书号", "获赞", "互关", "粉丝", "编辑主页", "编辑资料", "添加朋友", "创作者中心", "我的钱包"
    ]

    NUMBER_RE = re.compile(r"[+\-]?[0-9][0-9,]*(?:\.[0-9]+)?\s*(?:%|万|千|w|W|k|K)?")

    def extract(self, text: str, platform: str | None = None, scene: str | None = None) -> RecognitionResult:
        clean = self._normalize_text(text or "")
        lines = self._lines(clean)
        platform_upper = (platform or "").upper()
        scene_upper = (scene or "").upper()

        if scene_upper == "ACCOUNT_OVERVIEW" or self._looks_like_account_page(clean, lines):
            return self._extract_account_overview(clean, lines, platform=platform)

        if platform_upper == "DOUYIN" and self._looks_like_douyin_data_page(clean):
            page_type = self._douyin_data_page_type(clean)
            metrics, key_value_metrics = self._extract_douyin_required_metrics(clean, lines, page_type)
        else:
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
            key_value_metrics = self._metrics_to_key_value(metrics)

        candidates = self._title_candidates(lines, platform=platform)
        title = candidates[0] if candidates else None
        account_name = self._extract_account_name(lines)
        account_id = self._extract_account_id(clean, platform=platform)
        filled = sum(1 for v in metrics.model_dump().values() if v is not None) + len(key_value_metrics)
        confidence = min(0.96, 0.35 + filled * 0.04 + (0.20 if title else 0) + (0.08 if account_name else 0) + (0.05 if account_id else 0))
        return RecognitionResult(
            accountName=account_name,
            accountId=account_id,
            douyinId=account_id if platform_upper == "DOUYIN" else None,
            wechatChannelId=account_id if platform_upper == "WECHAT_CHANNEL" else None,
            contentTitle=title,
            candidateTitles=candidates[:5],
            metrics=metrics,
            keyValueMetrics=key_value_metrics,
            confidence=confidence,
        )

    def _looks_like_douyin_data_page(self, clean: str) -> bool:
        return "作品数据详情" in clean and ("总览" in clean or "流量分析" in clean or "观众分析" in clean)

    def _douyin_data_page_type(self, clean: str) -> str:
        if any(word in clean for word in ["内容吸引力", "封面点击率", "文案完读率", "评论进入率", "流量上涨"]):
            return "FLOW"
        if "涨粉量" in clean or "粉丝播放占比" in clean:
            return "CHART"
        return "OVERVIEW"

    def _extract_douyin_required_metrics(self, clean: str, lines: list[str], page_type: str) -> tuple[Metrics, dict[str, object]]:
        metrics = Metrics()
        kv: dict[str, object] = {}

        if page_type == "OVERVIEW":
            self._extract_overview(lines, clean, metrics, kv)
        elif page_type == "CHART":
            self._extract_chart(lines, metrics, kv)
        else:
            self._extract_flow(lines, clean, metrics, kv)

        return metrics, kv

    def _extract_overview(self, lines: list[str], clean: str, metrics: Metrics, kv: dict[str, object]) -> None:
        primary = self._values_after_label_sequence(lines, ["播放量", "点赞量", "评论量"], 3)
        if len(primary) >= 1:
            metrics.viewCount = self._parse_number(primary[0])
            self._put_kv(kv, "播放量", primary[0])
        if len(primary) >= 2:
            metrics.likeCount = self._parse_number(primary[1])
            self._put_kv(kv, "点赞量", primary[1])
        if len(primary) >= 3:
            metrics.commentCount = self._parse_number(primary[2])
            self._put_kv(kv, "评论量", primary[2])

        secondary = self._values_after_label_sequence(lines, ["分享量", "收藏量", "划走率"], 3)
        if len(secondary) == 2 and self._looks_percent(secondary[1]):
            metrics.shareCount = self._parse_number(secondary[0])
            self._put_kv(kv, "分享量", secondary[0])
            self._put_kv(kv, "划走率", secondary[1])
        elif secondary:
            if len(secondary) >= 1:
                metrics.shareCount = self._parse_number(secondary[0])
                self._put_kv(kv, "分享量", secondary[0])
            if len(secondary) >= 2 and not self._looks_percent(secondary[1]):
                metrics.favoriteCount = self._parse_number(secondary[1])
                self._put_kv(kv, "收藏量", secondary[1])
            if len(secondary) >= 3 and self._looks_percent(secondary[2]):
                self._put_kv(kv, "划走率", secondary[2])

        copy = self._values_after_label_sequence(lines, ["文案展开率", "平均浏览图片数"], 2)
        if len(copy) >= 1:
            self._put_kv(kv, "文案展开率", copy[0])
        if len(copy) >= 2:
            self._put_kv(kv, "平均浏览图片数", copy[1])

        completion = self._find_inline_value(clean, "完播率") or self._find_percent(clean, ["完播率", "播放完成率", "看完率"])
        if completion:
            metrics.completionRate = completion
            self._put_kv(kv, "完播率", completion)

    def _extract_chart(self, lines: list[str], metrics: Metrics, kv: dict[str, object]) -> None:
        trend = self._leading_trend_values(lines)
        if trend:
            kv["趋势曲线数值"] = trend

        fan = self._values_after_label_sequence(lines, ["涨粉量", "脱粉量", "粉丝播放占比"], 3)
        if not fan:
            return
        metrics.followerGain = self._parse_number(fan[0])
        self._put_kv(kv, "涨粉量", fan[0])
        if len(fan) >= 2 and self._looks_percent(fan[1]):
            self._put_kv(kv, "粉丝播放占比", fan[1])
        elif len(fan) >= 2:
            self._put_kv(kv, "脱粉量", fan[1])
        if len(fan) >= 3:
            self._put_kv(kv, "粉丝播放占比", fan[2])

    def _extract_flow(self, lines: list[str], clean: str, metrics: Metrics, kv: dict[str, object]) -> None:
        view = self._find_inline_value(clean, "播放量")
        if view:
            metrics.viewCount = self._parse_number(view)
            self._put_kv(kv, "播放量", view)
        uplift = self._find_inline_value(clean, "播放量较往期上涨") or self._find_inline_value(clean, "播放量较往期")
        if uplift:
            self._put_kv(kv, "播放量较往期上涨", uplift)

        attraction = self._values_after_label_sequence(lines, ["封面点击率", "文案展开率", "划走率"], 3)
        if len(attraction) >= 1:
            self._put_kv(kv, "封面点击率", attraction[0])
        if len(attraction) >= 2:
            self._put_kv(kv, "文案展开率", attraction[1])
        if len(attraction) >= 3:
            self._put_kv(kv, "划走率", attraction[2])

        reading = self._values_after_label_sequence(lines, ["平均浏览图片数", "文案完读率", "评论进入率"], 3)
        if len(reading) >= 1:
            self._put_kv(kv, "平均浏览图片数", reading[0])
        if len(reading) >= 2:
            self._put_kv(kv, "文案完读率", reading[1])
        if len(reading) >= 3:
            self._put_kv(kv, "评论进入率", reading[2])

        for label in ["完播率", "5s完播率", "5S完播率", "评论率", "分享率"]:
            value = self._find_inline_value(clean, label)
            if value:
                key = "5s完播率" if label == "5S完播率" else label
                self._put_kv(kv, key, value)
                if key == "完播率":
                    metrics.completionRate = value
                if key in ["评论率", "分享率"] and metrics.interactionRate is None:
                    metrics.interactionRate = value

    def _metrics_to_key_value(self, metrics: Metrics) -> dict[str, object]:
        mapping = {
            "viewCount": "播放量",
            "likeCount": "点赞量",
            "commentCount": "评论量",
            "favoriteCount": "收藏量",
            "shareCount": "分享量",
            "followerCount": "粉丝数",
            "followerGain": "涨粉量",
            "completionRate": "完播率",
            "interactionRate": "互动率",
            "averageWatchSeconds": "平均观看时长",
            "profileVisitCount": "主页访问量",
        }
        data = metrics.model_dump()
        return {cn: value for field, cn in mapping.items() if (value := data.get(field)) is not None}

    def _put_kv(self, kv: dict[str, object], key: str, value: object | None) -> None:
        if key and value is not None and str(value).strip() and str(value).strip().lower() != "null":
            kv[key] = str(value).strip() if not isinstance(value, list) else value

    def _find_inline_value(self, text: str, label: str) -> str | None:
        pattern = rf"{re.escape(label)}[^0-9+\-]*([+\-]?[0-9][0-9,]*(?:\.[0-9]+)?\s*(?:%|万|千|w|W|k|K)?)"
        m = re.search(pattern, text, re.IGNORECASE)
        return m.group(1).replace(" ", "") if m else None

    def _leading_trend_values(self, lines: list[str]) -> list[str]:
        marker = self._index_of_any(lines, ["观众分析", "流量分析", "总览"])
        if marker < 0:
            return []
        values: list[str] = []
        for line in lines[marker + 1:]:
            if self._is_label_like(line) or "05-" in line or "06-" in line or "DOU" in line or "粉丝" in line:
                break
            if self._first_number_token(line) == line.strip():
                values.append(line.strip())
            elif values:
                break
            if len(values) >= 10:
                break
        return values

    def _values_after_label_sequence(self, lines: list[str], labels: list[str], desired: int) -> list[str]:
        start = self._index_of_sequence(lines, labels)
        if start < 0:
            return []
        values: list[str] = []
        for line in lines[start + len(labels):]:
            if self._is_label_like(line) and values:
                break
            number = self._first_number_token(line)
            if number is not None:
                values.append(number)
            if len(values) >= desired:
                break
        return values

    def _index_of_sequence(self, lines: list[str], labels: list[str]) -> int:
        normalized_labels = [self._normalize_key(v) for v in labels]
        for i in range(0, len(lines) - len(labels) + 1):
            if [self._normalize_key(v) for v in lines[i:i + len(labels)]] == normalized_labels:
                return i
        return -1

    def _index_of_any(self, lines: list[str], labels: list[str]) -> int:
        normalized = {self._normalize_key(v) for v in labels}
        for i, line in enumerate(lines):
            if self._normalize_key(line) in normalized:
                return i
        return -1

    def _is_label_like(self, value: str) -> bool:
        if not value or self._first_number_token(value) == value.strip():
            return False
        labels = [
            "播放量", "点赞量", "评论量", "分享量", "收藏量", "划走率", "文案展开率", "平均浏览图片数",
            "涨粉量", "脱粉量", "粉丝播放占比", "封面点击率", "文案完读率", "评论进入率", "完播率", "5s完播率",
            "新增累计", "每小时", "每天", "设置观测>", "观看趋势", "留存分析", "内容吸引力", "流量上涨"
        ]
        return any(label in value for label in labels)

    def _first_number_token(self, value: str) -> str | None:
        if not value:
            return None
        m = self.NUMBER_RE.search(value.replace("％", "%"))
        return m.group(0).replace(" ", "") if m else None

    def _find_inline_number(self, text: str, patterns: list[str]) -> int | None:
        for pattern in patterns:
            m = re.search(pattern, text, re.IGNORECASE)
            if m:
                return self._parse_number(m.group(1))
        return None

    def _looks_percent(self, value: str | None) -> bool:
        return bool(value and "%" in value)

    def _looks_like_account_page(self, clean: str, lines: list[str]) -> bool:
        if not clean:
            return False
        hit_count = sum(1 for word in self.ACCOUNT_PAGE_HINTS if word in clean)
        if "抖音号" in clean or "视频号" in clean or "微信号" in clean or "小红书号" in clean:
            return True
        if hit_count >= 2 and any(word in clean for word in ["粉丝", "关注", "获赞", "互关"]):
            return True
        first_text = "\n".join(lines[:16])
        return hit_count >= 2 and any(word in first_text for word in ["编辑主页", "编辑资料", "添加朋友", "我的订单", "创作者中心"])

    def _extract_account_overview(self, clean: str, lines: list[str], platform: str | None = None) -> RecognitionResult:
        platform_upper = (platform or "").upper()
        account_id = self._extract_account_id(clean, platform=platform)
        account_name = self._extract_account_name_from_account_page(lines, account_id)
        confidence = min(0.96, 0.35 + (0.35 if account_id else 0) + (0.25 if account_name else 0))
        return RecognitionResult(
            accountName=account_name,
            accountId=account_id,
            douyinId=account_id if platform_upper == "DOUYIN" else None,
            wechatChannelId=account_id if platform_upper == "WECHAT_CHANNEL" else None,
            contentTitle=None,
            candidateTitles=[],
            metrics=Metrics(),
            keyValueMetrics={},
            confidence=confidence,
        )

    def _normalize_text(self, text: str) -> str:
        value = text.replace("｜", "|").replace("：", ":").replace("，", ",")
        value = value.replace("％", "%").replace("Ｗ", "W").replace("ｗ", "w")
        value = value.replace("抖音 号", "抖音号").replace("抖 音号", "抖音号").replace("抖音帳", "抖音号")
        value = value.replace("视频 号", "视频号").replace("视 频号", "视频号")
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

    def _parse_number(self, value: str | None) -> int | None:
        if value is None:
            return None
        s = value.strip().replace(" ", "").replace(",", "").lower()
        if s.endswith("%"):
            return None
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

    def _extract_account_id(self, text: str, platform: str | None = None) -> str | None:
        patterns = [
            r"抖音号\s*[:：]?\s*([A-Za-z0-9_.\-]{4,40})",
            r"抖音\s*ID\s*[:：]?\s*([A-Za-z0-9_.\-]{4,40})",
            r"Douyin\s*ID\s*[:：]?\s*([A-Za-z0-9_.\-]{4,40})",
            r"视频号\s*[:：]?\s*([A-Za-z0-9_.\-]{4,60})",
            r"微信号\s*[:：]?\s*([A-Za-z0-9_.\-]{4,60})",
            r"小红书号\s*[:：]?\s*([A-Za-z0-9_.\-]{4,60})",
            r"ID\s*[:：]?\s*([A-Za-z0-9_.\-]{6,60})",
        ]
        for pattern in patterns:
            m = re.search(pattern, text, re.IGNORECASE)
            if m:
                return m.group(1).strip(" ._-")[:60]
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
        return None

    def _extract_account_name_from_account_page(self, lines: list[str], account_id: str | None = None) -> str | None:
        for idx, line in enumerate(lines):
            if any(label in line for label in ["抖音号", "视频号", "微信号", "小红书号"]):
                same_line = re.split(r"抖音号|视频号|微信号|小红书号", line, maxsplit=1)[0].strip(" :|@")
                candidate = self._clean_account_page_name(same_line, account_id)
                if candidate:
                    return candidate
                for back in range(idx - 1, max(-1, idx - 6), -1):
                    candidate = self._clean_account_page_name(lines[back], account_id)
                    if candidate:
                        return candidate
        for line in lines[:14]:
            candidate = self._clean_account_page_name(line, account_id)
            if candidate:
                return candidate
        return None

    def _clean_account_page_name(self, value: str | None, account_id: str | None = None) -> str | None:
        if not value:
            return None
        text = re.sub(r"\s+", " ", value).strip(" :|@")
        text = re.sub(r"^(账号|昵称|作者|用户)\s*", "", text).strip(" :|@")
        text = re.sub(r"(抖音号|视频号|微信号|小红书号).*$", "", text).strip(" :|@")
        text = text.replace("已关注", "").replace("关注", "").strip(" :|@")
        if account_id and account_id in text:
            return None
        if len(text) < 2 or len(text) > 40:
            return None
        if re.fullmatch(r"[0-9A-Za-z_.\-]+", text):
            return None
        noise_words = [
            "中国联通", "中国移动", "中国电信", "添加朋友", "新访客", "搜索", "首页", "消息", "朋友", "我的订单", "观看历史", "创作者中心",
            "我的钱包", "全部功能", "作品", "日常", "收藏", "喜欢", "获赞", "互关", "粉丝", "关注", "编辑主页", "编辑资料",
            "添加性别", "标签", "私密作品", "抖音商城", "商品橱窗", "企业服务中心", "地址", "IP属地", "去发布"
        ]
        if any(word in text for word in noise_words):
            return None
        if re.search(r"^[0-9]+$", text):
            return None
        return text

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

    def _normalize_key(self, value: str) -> str:
        return re.sub(r"[\s:_：/\-+>√]", "", value or "")
