from app.services.social_metrics_extractor import SocialMetricsExtractor


def test_extract_wan_values():
    text = "账号 树教育澳洲留学\n澳洲留学申请避坑指南\n播放 1.2万\n点赞 800\n评论 96\n收藏 300\n分享 20"
    result = SocialMetricsExtractor().extract(text)
    assert result.metrics.viewCount == 12000
    assert result.metrics.likeCount == 800
    assert result.metrics.commentCount == 96
    assert result.metrics.favoriteCount == 300
    assert result.metrics.shareCount == 20
