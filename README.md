# tree-education-datacollecting

纯图片识别能力服务，用于给 Tree Education OA 后端调用。

这个项目只做一件事：

```text
图片 / 截图 -> OCR识别 -> 结构化字段抽取 -> JSON返回给OA后端
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
返回 OCR原文 + 结构化运营数据 + 置信度
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
  -F "scene=CONTENT_DETAIL"
```

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

- `rawText`：OCR 原始文本
- `textBlocks`：文本块、置信度、坐标
- `result.accountName`：账号名
- `result.contentTitle`：作品标题
- `result.metrics.viewCount`：播放/浏览/阅读数
- `result.metrics.likeCount`：点赞数
- `result.metrics.commentCount`：评论数
- `result.metrics.favoriteCount`：收藏数
- `result.metrics.shareCount`：分享/转发数
- `result.metrics.followerCount`：粉丝数
- `result.confidence`：综合置信度

## OA 对接原则

前端不要直接调用本服务。正确链路是：

```text
OA前端 -> tree-education-ioas -> tree-education-datacollecting
```

OA 后端负责登录鉴权、保存识别结果、人工审核、最终入库。