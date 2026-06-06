# tree-education-datacollecting

纯图片识别能力服务，用于给 Tree Education OA 后端调用。

这个项目只做一件事：

```text
图片 / 截图 -> OCR识别 -> 判断内容类型 -> 结构化字段抽取 -> JSON返回给OA后端
```

它不负责人工审核、运营任务管理、最终业务入库、报表展示、OA 权限体系。这些都由 `tree-education-ioas` 和 `tree-education-ioas-frontend` 负责。

## 推荐架构

```text
OA后台前端
  ↓ 上传截图
OA后端 tree-education-ioas
  ↓ multipart/form-data 调用
图片识别服务 tree-education-datacollecting
  ↓
返回 OCR原文 + 内容类型 + 图文/视频结构化运营数据 + 置信度
  ↓
OA后端保存、审核、入库、统计
```

## 技术栈

- Python 3.10+
- FastAPI
- PaddleOCR，可选
- OpenCV / Pillow
- Docker

## 快速启动：Mock 模式

Mock 模式不依赖 PaddleOCR，适合先和 OA 后端联调接口。

```bash
cp .env.example .env
docker compose up -d --build
```

健康检查：

```bash
curl http://localhost:18083/api/v1/health
```

图片识别：

```bash
curl -X POST http://localhost:18083/api/v1/recognize \
  -H "Authorization: Bearer dev-recognition-token" \
  -F "file=@demo.png" \
  -F "platform=XIAOHONGSHU" \
  -F "scene=CONTENT_DETAIL" \
  -F "contentType=AUTO"
```

显式指定图文：

```bash
curl -X POST http://localhost:18083/api/v1/recognize \
  -H "Authorization: Bearer dev-recognition-token" \
  -F "file=@image-text.png" \
  -F "platform=DOUYIN" \
  -F "scene=CONTENT_DETAIL" \
  -F "contentType=IMAGE_TEXT"
```

显式指定视频：

```bash
curl -X POST http://localhost:18083/api/v1/recognize \
  -H "Authorization: Bearer dev-recognition-token" \
  -F "file=@video.png" \
  -F "platform=DOUYIN" \
  -F "scene=CONTENT_DETAIL" \
  -F "contentType=VIDEO"
```

## contentType 说明

| 值 | 说明 |
|---|---|
| `AUTO` | 自动识别图文/视频，默认值 |
| `IMAGE_TEXT` | 图文、笔记、图片类作品截图 |
| `VIDEO` | 短视频作品截图 |
| `ACCOUNT_OVERVIEW` | 账号主页 / 账号概览截图 |

## PaddleOCR 模式

```bash
docker compose -f docker-compose.paddle.yml up -d --build
```

## 核心接口

| 方法 | 路径 | 用途 |
|---|---|---|
| GET | `/api/v1/health` | 健康检查 |
| POST | `/api/v1/recognize` | 单图识别 |
| POST | `/api/v1/recognize/batch` | 批量识别 |

## 返回字段

通用字段：

- `rawText`：OCR 原始文本
- `contentType`：最终识别出来的内容类型
- `result.accountName`：账号名
- `result.accountId`：平台账号 ID
- `result.contentTitle`：作品标题
- `result.candidateTitles`：候选标题
- `result.confidence`：综合置信度
- `result.metrics`：兼容旧版 OA 的通用指标
- `result.keyValueMetrics`：中文指标名和值，适合直接给人工校验页展示

图文字段：

- `result.imageTextStats.readCount`：阅读量
- `result.imageTextStats.viewCount`：播放/浏览量
- `result.imageTextStats.likeCount`：点赞量
- `result.imageTextStats.commentCount`：评论量
- `result.imageTextStats.favoriteCount`：收藏量
- `result.imageTextStats.shareCount`：分享量
- `result.imageTextStats.imageCount`：图片数
- `result.imageTextStats.coverClickRate`：封面点击率
- `result.imageTextStats.copyExpandRate`：文案展开率
- `result.imageTextStats.copyFinishRate`：文案完读率
- `result.imageTextStats.commentEnterRate`：评论进入率
- `result.imageTextStats.slideAwayRate`：划走率
- `result.imageTextStats.followerGain`：涨粉量

视频字段：

- `result.videoStats.playCount`：播放量
- `result.videoStats.exposureCount`：曝光量
- `result.videoStats.likeCount`：点赞量
- `result.videoStats.commentCount`：评论量
- `result.videoStats.favoriteCount`：收藏量
- `result.videoStats.shareCount`：分享量
- `result.videoStats.completionRate`：完播率
- `result.videoStats.fiveSecondCompletionRate`：5s 完播率
- `result.videoStats.averageWatchSeconds`：平均观看秒数
- `result.videoStats.averageWatchText`：平均观看时长原文
- `result.videoStats.durationSeconds`：视频秒数
- `result.videoStats.durationText`：视频时长原文
- `result.videoStats.interactionRate`：互动率
- `result.videoStats.followerGain`：涨粉量
- `result.videoStats.profileVisitCount`：主页访问量

## OA 对接原则

前端不要直接调用本服务。正确链路是：

```text
OA前端 -> tree-education-ioas -> tree-education-datacollecting
```

OA 后端负责登录鉴权、保存识别结果、人工审核、最终入库。

建议 OA 后端入库时按 `contentType` 分流：

```text
contentType = IMAGE_TEXT -> 保存 image_text_stats
contentType = VIDEO      -> 保存 video_stats
contentType = UNKNOWN    -> 进入人工校验队列
```
