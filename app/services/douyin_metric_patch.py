from app.services.social_metrics_extractor import SocialMetricsExtractor
from app.schemas.recognition import ImageTextStats, VideoStats


class PatchedSocialMetricsExtractor(SocialMetricsExtractor):
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
