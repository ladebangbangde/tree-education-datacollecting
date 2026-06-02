# OA 对接说明

## 调用链路

```text
OA 前端 -> tree-education-ioas -> tree-education-datacollecting
```

前端不要直接调用图片识别服务。

## 图片识别服务接口

```http
POST /api/v1/recognize
Authorization: Bearer dev-recognition-token
Content-Type: multipart/form-data
```

字段：

- `file`：截图图片
- `platform`：`XIAOHONGSHU`、`DOUYIN`、`WECHAT_CHANNEL`
- `scene`：`CONTENT_DETAIL`、`CONTENT_LIST`、`ACCOUNT_OVERVIEW`

## OA 后端代理接口

`tree-education-ioas` 已有：

```http
POST /api/v1/recognition/social-metrics
```

OA 后端配置：

```yaml
ioas:
  recognition:
    enabled: true
    base-url: http://localhost:18083
    recognize-path: /api/v1/recognize
    token: dev-recognition-token
```

## 本地联调

先启动图片识别服务：

```bash
cd tree-education-datacollecting
cp .env.example .env
docker compose up -d --build
```

再启动 OA 后端：

```bash
cd tree-education-ioas
mvn spring-boot:run -Dspring-boot.run.profiles=dev
```

然后用 OA token 调用：

```bash
curl -X POST http://localhost:1201/api/v1/recognition/social-metrics \
  -H "Authorization: Bearer <OA_TOKEN>" \
  -F "file=@xiaohongshu.png" \
  -F "platform=XIAOHONGSHU" \
  -F "scene=CONTENT_DETAIL"
```
