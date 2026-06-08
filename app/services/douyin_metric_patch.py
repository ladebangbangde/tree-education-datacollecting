from app.services.social_metrics_extractor import SocialMetricsExtractor
from app.schemas.recognition import VideoStats


class PatchedSocialMetricsExtractor(SocialMetricsExtractor):
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
