import re

from app.services.social_metrics_extractor import SocialMetricsExtractor
from app.schemas.recognition import ImageTextStats, Metrics, VideoStats


class PatchedSocialMetricsExtractor(SocialMetricsExtractor):
    def _extract_image_text(self, clean: str, lines: list[str], platform_upper: str) -> tuple[Metrics, ImageTextStats, dict[str, object]]:
        metrics, stats, key_value_metrics = super()._extract_image_text(clean, lines, platform_upper)
        if platform_upper == "XIAOHONGSHU":
            self._patch_xiaohongshu_image_text(clean, lines, stats)
            metrics = Metrics(
                viewCount=stats.viewCount or stats.readCount,
                likeCount=stats.likeCount,
                commentCount=stats.commentCount,
                favoriteCount=stats.favoriteCount,
                shareCount=stats.shareCount,
                followerGain=stats.followerGain,
            )
            key_value_metrics = self._stats_to_key_value(
                stats,
                {
                    "readCount": "阅读量",
                    "viewCount": "播放/观看量",
                    "likeCount": "点赞量",
                    "commentCount": "评论量",
                    "favoriteCount": "收藏量",
                    "shareCount": "分享量",
                    "imageCount": "图片数",
                    "coverClickRate": "封面点击率",
                    "copyExpandRate": "文案展开率",
                    "copyFinishRate": "文案完读率",
                    "commentEnterRate": "评论进入率",
                    "slideAwayRate": "划走率",
                    "followerGain": "涨粉量",
                },
            )
        return metrics, stats, key_value_metrics

    def _extract_video(self, clean: str, lines: list[str], platform_upper: str) -> tuple[Metrics, VideoStats, dict[str, object]]:
        metrics, stats, key_value_metrics = super()._extract_video(clean, lines, platform_upper)
        if platform_upper == "XIAOHONGSHU":
            self._patch_xiaohongshu_video(clean, lines, stats)
            metrics = Metrics(
                viewCount=stats.playCount,
                likeCount=stats.likeCount,
                commentCount=stats.commentCount,
                favoriteCount=stats.favoriteCount,
                shareCount=stats.shareCount,
                followerGain=stats.followerGain,
                completionRate=stats.completionRate,
                interactionRate=stats.interactionRate,
                averageWatchSeconds=stats.averageWatchSeconds,
                profileVisitCount=stats.profileVisitCount,
            )
            key_value_metrics = self._stats_to_key_value(
                stats,
                {
                    "playCount": "播放量",
                    "exposureCount": "曝光量",
                    "likeCount": "点赞量",
                    "commentCount": "评论量",
                    "favoriteCount": "收藏量",
                    "shareCount": "分享量",
                    "completionRate": "完播率",
                    "fiveSecondCompletionRate": "5s完播率",
                    "averageWatchText": "平均观看时长",
                    "durationText": "视频时长",
                    "interactionRate": "互动率",
                    "followerGain": "涨粉量",
                    "profileVisitCount": "主页访问量",
                },
            )
        return metrics, stats, key_value_metrics

    def _title_candidates(self, lines: list[str], platform: str | None = None) -> list[str]:
        candidates = super()._title_candidates(lines, platform=platform)
        if (platform or "").upper() != "XIAOHONGSHU":
            return candidates
        patched: list[str] = []
        for line in lines:
            value = self._clean_xhs_title_line(line)
            if value and value not in patched:
                patched.append(value)
        return patched + [candidate for candidate in candidates if candidate not in patched]

    def _clean_xhs_title_line(self, line: str | None) -> str | None:
        if not line:
            return None
        value = re.sub(r"\s+", " ", line).strip().strip(" :：|《》[]【】")
        for prefix in ["标题", "笔记标题", "作品标题", "图文", "视频"]:
            if value.startswith(prefix):
                value = value[len(prefix):].strip(" :：|《》[]【】")
        value = re.sub(r"^#\d+\s*", "", value).strip()
        value = re.sub(r"#\S+", "", value).strip()
        if not value:
            return None
        noise = [
            "小红书", "笔记分析", "笔记分析详情", "数据表现", "数据总览", "整体数据", "实时", "近7天", "近30天",
            "曝光", "曝光量", "观看", "观看数", "播放", "播放量", "点赞", "点赞数", "评论", "评论数", "收藏", "收藏数", "分享", "分享数",
            "封面点击率", "文案展开率", "评论进入率", "平均观看时长", "平均观看时长", "涨粉数", "粉丝占", "查看趋势图",
        ]
        if any(item in value for item in noise):
            return None
        if len(value) < 4 or len(value) > 120:
            return None
        if re.fullmatch(r"[0-9.万千kwKW%+\-\s秒sS:：]+", value):
            return None
        if len(re.findall(r"[\u4e00-\u9fa5A-Za-z]", value)) < 3:
            return None
        return value

    def _patch_xiaohongshu_image_text(self, clean: str, lines: list[str], stats: ImageTextStats) -> None:
        # 小红书图文数据页同时有“曝光量”和“观看数”。日报里的播放量应取“观看数”，不能取曝光量。
        exposure_view_cover = self._xhs_values_after_label_sequence(lines, ["曝光量", "观看数", "封面点击率"], 3)
        if len(exposure_view_cover) >= 2:
            stats.viewCount = self._parse_number(exposure_view_cover[1]) or stats.viewCount
            stats.readCount = stats.viewCount if stats.readCount is None else stats.readCount
        if len(exposure_view_cover) >= 3 and self._looks_percent(exposure_view_cover[2]):
            stats.coverClickRate = exposure_view_cover[2]

        primary = self._first_xhs_sequence(
            lines,
            [
                ["观看数", "点赞数", "评论数"],
                ["观看量", "点赞数", "评论数"],
                ["观看数", "点赞量", "评论量"],
                ["播放量", "点赞量", "评论量"],
            ],
            3,
        )
        if len(primary) >= 1:
            stats.viewCount = self._parse_number(primary[0]) or stats.viewCount
            stats.readCount = stats.viewCount if stats.readCount is None else stats.readCount
        if len(primary) >= 2:
            stats.likeCount = self._parse_number(primary[1]) if self._parse_number(primary[1]) is not None else stats.likeCount
        if len(primary) >= 3:
            stats.commentCount = self._parse_number(primary[2]) if self._parse_number(primary[2]) is not None else stats.commentCount

        social = self._first_xhs_sequence(
            lines,
            [
                ["点赞数", "评论数", "收藏数", "分享数"],
                ["点赞量", "评论量", "收藏量", "分享量"],
                ["点赞数", "评论数", "收藏数"],
            ],
            4,
        )
        if len(social) >= 1:
            stats.likeCount = self._parse_number(social[0]) if self._parse_number(social[0]) is not None else stats.likeCount
        if len(social) >= 2:
            stats.commentCount = self._parse_number(social[1]) if self._parse_number(social[1]) is not None else stats.commentCount
        if len(social) >= 3:
            stats.favoriteCount = self._parse_number(social[2]) if self._parse_number(social[2]) is not None else stats.favoriteCount
        if len(social) >= 4:
            stats.shareCount = self._parse_number(social[3]) if self._parse_number(social[3]) is not None else stats.shareCount

        favorite_share = self._first_xhs_sequence(lines, [["收藏数", "分享数"], ["收藏量", "分享量"]], 2)
        if len(favorite_share) >= 1:
            stats.favoriteCount = self._parse_number(favorite_share[0]) if self._parse_number(favorite_share[0]) is not None else stats.favoriteCount
        if len(favorite_share) >= 2:
            stats.shareCount = self._parse_number(favorite_share[1]) if self._parse_number(favorite_share[1]) is not None else stats.shareCount

        stats.coverClickRate = self._xhs_percent_after_label(clean, lines, ["封面点击率"]) or stats.coverClickRate
        stats.copyExpandRate = self._xhs_percent_after_label(clean, lines, ["文案展开率"]) or stats.copyExpandRate
        stats.copyFinishRate = self._xhs_percent_after_label(clean, lines, ["文案完读率", "文案阅读完成率"]) or stats.copyFinishRate
        stats.commentEnterRate = self._xhs_percent_after_label(clean, lines, ["评论进入率"]) or stats.commentEnterRate
        stats.slideAwayRate = self._xhs_percent_after_label(clean, lines, ["划走率"]) or stats.slideAwayRate

        follower = self._first_xhs_sequence(lines, [["平均观看时长", "涨粉数"], ["平均观看时长", "单帖涨粉量"], ["平均观看时长", "涨粉量"]], 2)
        if len(follower) >= 2:
            stats.followerGain = self._parse_number(follower[1]) if self._parse_number(follower[1]) is not None else stats.followerGain
        else:
            follower_value = self._xhs_number_after_label(lines, ["涨粉数", "单帖涨粉量", "涨粉量"], reject_duration=True)
            if follower_value is not None:
                stats.followerGain = follower_value

        # 强兜底：图文不允许把曝光量塞进封面点击率；封面点击率必须是百分比。
        if stats.coverClickRate is not None and not self._looks_percent(str(stats.coverClickRate)):
            stats.coverClickRate = None

    def _patch_xiaohongshu_video(self, clean: str, lines: list[str], stats: VideoStats) -> None:
        primary = self._first_xhs_sequence(
            lines,
            [["播放量", "点赞量", "评论量"], ["观看数", "点赞数", "评论数"], ["观看量", "点赞量", "评论量"]],
            3,
        )
        if len(primary) >= 1:
            stats.playCount = self._parse_number(primary[0]) or stats.playCount
        if len(primary) >= 2:
            stats.likeCount = self._parse_number(primary[1]) if self._parse_number(primary[1]) is not None else stats.likeCount
        if len(primary) >= 3:
            stats.commentCount = self._parse_number(primary[2]) if self._parse_number(primary[2]) is not None else stats.commentCount

        social = self._first_xhs_sequence(lines, [["收藏量", "分享量"], ["收藏数", "分享数"]], 2)
        if len(social) >= 1:
            stats.favoriteCount = self._parse_number(social[0]) if self._parse_number(social[0]) is not None else stats.favoriteCount
        if len(social) >= 2:
            stats.shareCount = self._parse_number(social[1]) if self._parse_number(social[1]) is not None else stats.shareCount

        follower = self._first_xhs_sequence(lines, [["平均观看时长", "涨粉数"], ["平均播放时长", "涨粉数"]], 2)
        if len(follower) >= 2:
            stats.followerGain = self._parse_number(follower[1]) if self._parse_number(follower[1]) is not None else stats.followerGain
        stats.completionRate = self._xhs_percent_after_label(clean, lines, ["整体完播率", "完播率", "播放完成率"]) or stats.completionRate
        stats.fiveSecondCompletionRate = self._xhs_percent_after_label(clean, lines, ["5s完播率", "5S完播率", "5秒完播率"]) or stats.fiveSecondCompletionRate

    def _first_xhs_sequence(self, lines: list[str], sequences: list[list[str]], desired: int) -> list[str]:
        for labels in sequences:
            values = self._xhs_values_after_label_sequence(lines, labels, desired)
            if len(values) >= min(desired, len(labels)):
                return values
        return []

    def _xhs_values_after_label_sequence(self, lines: list[str], labels: list[str], desired: int) -> list[str]:
        label_positions: list[int] = []
        search_from = 0
        for label in labels:
            found = -1
            for index in range(search_from, min(len(lines), search_from + 12)):
                if label in lines[index]:
                    found = index
                    break
            if found < 0:
                return []
            label_positions.append(found)
            search_from = found + 1
        values: list[str] = []
        start = label_positions[-1] + 1
        for line in lines[start:start + 24]:
            if self._xhs_is_noise_metric_line(line):
                continue
            if self._is_label_like(line) and values:
                break
            for token in self._xhs_number_tokens(line):
                values.append(token)
                if len(values) >= desired:
                    return values
        return values

    def _xhs_number_after_label(self, lines: list[str], labels: list[str], reject_duration: bool = False) -> int | None:
        for label in labels:
            for index, line in enumerate(lines):
                if label not in line:
                    continue
                after = line.split(label, 1)[-1]
                for token in self._xhs_number_tokens(after):
                    if reject_duration and self._xhs_looks_duration_token(token, after):
                        continue
                    parsed = self._parse_number(token)
                    if parsed is not None:
                        return parsed
                for next_line in lines[index + 1:index + 6]:
                    if self._xhs_is_noise_metric_line(next_line):
                        continue
                    if reject_duration and any(word in next_line for word in ["平均观看时长", "平均播放时长", "秒"]):
                        continue
                    for token in self._xhs_number_tokens(next_line):
                        parsed = self._parse_number(token)
                        if parsed is not None:
                            return parsed
        return None

    def _xhs_percent_after_label(self, clean: str, lines: list[str], labels: list[str]) -> str | None:
        for label in labels:
            pattern = rf"{re.escape(label)}[^0-9%]{{0,24}}([0-9]+(?:\.[0-9]+)?\s*%)"
            match = re.search(pattern, clean, re.IGNORECASE)
            if match:
                return match.group(1).replace(" ", "")
            for index, line in enumerate(lines):
                if label not in line:
                    continue
                for token in self._xhs_number_tokens(line.split(label, 1)[-1]):
                    if self._looks_percent(token):
                        return token
                for next_line in lines[index + 1:index + 8]:
                    if self._xhs_is_noise_metric_line(next_line):
                        continue
                    for token in self._xhs_number_tokens(next_line):
                        if self._looks_percent(token):
                            return token
                        # 如果先遇到非百分比数字，继续找；封面点击率不能拿曝光量兜底。
        return None

    def _xhs_number_tokens(self, value: str) -> list[str]:
        if not value:
            return []
        text = value.replace("％", "%")
        tokens = [match.group(0).replace(" ", "") for match in self.NUMBER_RE.finditer(text)]
        return [token for token in tokens if token]

    def _xhs_is_noise_metric_line(self, line: str) -> bool:
        text = line or ""
        return "粉丝占" in text or text.strip() in {"实时", "查看趋势图", "查看趋势", "点击展开"}

    def _xhs_looks_duration_token(self, token: str, context: str) -> bool:
        return bool(token and any(unit in context for unit in ["秒", "分钟", "平均观看时长", "平均播放时长"]))

    def _patch_douyin_image_text(self, clean: str, lines: list[str], stats: ImageTextStats) -> None:
        # 数据页1：播放量 / 点赞量 / 评论量
        primary = self._values_after_label_sequence(lines, ["播放量", "点赞量", "评论量"], 3)
        if len(primary) >= 1:
            stats.viewCount = self._parse_number(primary[0])
        if len(primary) >= 2:
            stats.likeCount = self._parse_number(primary[1])
        if len(primary) >= 3:
            stats.commentCount = self._parse_number(primary[2])

        # 数据页1：分享量 / 收藏量 / 划走率
        secondary = self._values_after_label_sequence(lines, ["分享量", "收藏量", "划走率"], 3)
        if len(secondary) >= 1:
            stats.shareCount = self._parse_number(secondary[0]) or stats.shareCount
        if len(secondary) >= 2 and not self._looks_percent(secondary[1]):
            stats.favoriteCount = self._parse_number(secondary[1]) or stats.favoriteCount
        if len(secondary) >= 3 and self._looks_percent(secondary[2]):
            stats.slideAwayRate = secondary[2]

        # 数据页3：封面点击率 / 文案展开率 / 划走率 -> 0% / 7.19% / 45.01%
        first_row = self._values_after_label_sequence(lines, ["封面点击率", "文案展开率", "划走率"], 3)
        if len(first_row) >= 3:
            if self._looks_percent(first_row[0]):
                stats.coverClickRate = first_row[0]
            if self._looks_percent(first_row[1]):
                stats.copyExpandRate = first_row[1]
            if self._looks_percent(first_row[2]):
                stats.slideAwayRate = first_row[2]

        # 数据页3：平均浏览图片数 / 文案完读率 / 评论进入率 -> 2.5 / 71.01% / 8.13%
        second_row = self._values_after_label_sequence(lines, ["平均浏览图片数", "文案完读率", "评论进入率"], 3)
        if len(second_row) >= 3:
            stats.imageCount = self._parse_number(second_row[0]) or stats.imageCount
            if self._looks_percent(second_row[1]):
                stats.copyFinishRate = second_row[1]
            if self._looks_percent(second_row[2]):
                stats.commentEnterRate = second_row[2]

    def _patch_douyin_video(self, clean: str, lines: list[str], stats: VideoStats) -> None:
        # 数据页1：评论量 / 点赞量 / 播放量 -> 4 / 723 / 7
        primary = self._values_after_label_sequence(lines, ["评论量", "点赞量", "播放量"], 3)
        if len(primary) >= 3:
            stats.commentCount = self._parse_number(primary[0])
            stats.playCount = self._parse_number(primary[1])
            stats.likeCount = self._parse_number(primary[2])
        else:
            primary = self._values_after_label_sequence(lines, ["播放量", "点赞量", "评论量"], 3)
            if len(primary) >= 1:
                stats.playCount = self._parse_number(primary[0])
            if len(primary) >= 2:
                stats.likeCount = self._parse_number(primary[1])
            if len(primary) >= 3:
                stats.commentCount = self._parse_number(primary[2])

        # 数据页1：弹幕量 / 收藏量 / 分享量 -> 0 / 6 / 0
        secondary = self._values_after_label_sequence(lines, ["弹幕量", "收藏量", "分享量"], 3)
        if len(secondary) >= 3:
            stats.favoriteCount = self._parse_number(secondary[1])
            stats.shareCount = self._parse_number(secondary[2])
        else:
            secondary = self._values_after_label_sequence(lines, ["分享量", "收藏量", "弹幕量"], 3)
            if len(secondary) >= 1:
                stats.shareCount = self._parse_number(secondary[0]) or stats.shareCount
            if len(secondary) >= 2 and not self._looks_percent(secondary[1]):
                stats.favoriteCount = self._parse_number(secondary[1]) or stats.favoriteCount

        # 数据页2：粉丝播放占比 / 脱粉量 / 涨粉量 -> 0.69% / 0 / 2
        follower = self._values_after_label_sequence(lines, ["粉丝播放占比", "脱粉量", "涨粉量"], 3)
        if len(follower) >= 3:
            stats.followerGain = self._parse_number(follower[2])

        # 数据页3：完播率 / 平均播放时长 / 2s跳出率 -> 4.99% / 18秒 / 30.38%
        attraction = self._values_after_label_sequence(lines, ["完播率", "平均播放时长", "2s跳出率"], 3)
        if len(attraction) >= 3:
            if self._looks_percent(attraction[0]):
                stats.completionRate = attraction[0]
            stats.averageWatchText = attraction[1]
            stats.averageWatchSeconds = self._duration_text_to_seconds(attraction[1])

        # 数据页3：5s完播率 / 平均播放占比 -> 40.16% / 22.88%
        flow = self._values_after_label_sequence(lines, ["5s完播率", "平均播放占比"], 2)
        if len(flow) >= 1 and self._looks_percent(flow[0]):
            stats.fiveSecondCompletionRate = flow[0]
        flow = self._values_after_label_sequence(lines, ["5秒完播率", "平均播放占比"], 2)
        if len(flow) >= 1 and self._looks_percent(flow[0]):
            stats.fiveSecondCompletionRate = flow[0]
