import json
import time
import uuid
from pathlib import Path

from fastapi import UploadFile

from app.core.config import settings
from app.core.errors import BadRequestError
from app.schemas.recognition import RecognitionResponse
from app.services.ocr_engine import OcrEngine
from app.services.douyin_metric_patch import PatchedSocialMetricsExtractor


class RecognitionService:
    def __init__(self) -> None:
        self.ocr = OcrEngine()
        self.extractor = PatchedSocialMetricsExtractor()
        self.temp_dir = Path("/tmp/tree-education-datacollecting")
        self.temp_dir.mkdir(parents=True, exist_ok=True)

    async def recognize_upload(self, file: UploadFile, platform: str, scene: str, content_type: str = "AUTO") -> RecognitionResponse:
        start = time.time()
        if not file.content_type or not file.content_type.startswith("image/"):
            raise BadRequestError("file must be an image")
        content = await file.read()
        if len(content) > settings.max_image_mb * 1024 * 1024:
            raise BadRequestError("image is too large")
        original_filename = file.filename or "image.png"
        normalized_scene = self._normalize_scene_by_filename(original_filename, scene)
        normalized_content_type = self._normalize_content_type_by_filename(original_filename, content_type)
        suffix = Path(original_filename).suffix or ".png"
        image_path = self.temp_dir / f"{uuid.uuid4().hex}{suffix}"
        image_path.write_bytes(content)
        request_id = uuid.uuid4().hex
        self._debug_print(
            "RECOGNITION START",
            {
                "requestId": request_id,
                "filename": original_filename,
                "contentTypeHeader": file.content_type,
                "size": len(content),
                "platform": platform,
                "scene": scene,
                "normalizedScene": normalized_scene,
                "contentType": content_type,
                "normalizedContentType": normalized_content_type,
                "ocrEngineSetting": settings.ocr_engine,
                "tempPath": str(image_path),
            },
        )
        ocr = self.ocr.recognize(image_path)
        print("\n===== OCR RAW TEXT BEGIN =====", flush=True)
        print(ocr.raw_text or "", flush=True)
        print("===== OCR RAW TEXT END =====\n", flush=True)
        result = self.extractor.extract(
            ocr.raw_text,
            platform=platform,
            scene=normalized_scene,
            content_type=normalized_content_type,
        )
        self._debug_print(
            "RECOGNITION PARSED RESULT",
            {
                "requestId": request_id,
                "filename": original_filename,
                "engine": ocr.engine,
                "rawTextLength": len(ocr.raw_text or ""),
                "result": result.model_dump(),
            },
        )
        warnings = []
        if not (ocr.raw_text or "").strip():
            warnings.append("OCR 未识别出任何文字，请检查图片清晰度、裁剪范围、是否为截图/拍屏、是否存在强反光或压缩。")
        if result.contentType in {"UNKNOWN", None} and normalized_scene != "ACCOUNT_OVERVIEW":
            warnings.append("未能明确判断内容类型，建议 OA 后台人工选择图文或视频后重新解析/校验。")
        if result.pageType == "UNKNOWN" or result.nextAction == "NEED_MANUAL_REVIEW":
            warnings.append("未能明确判断截图页面类型，请人工确认后再进入下一步。")
        try:
            image_path.unlink(missing_ok=True)
        except Exception:
            pass
        return RecognitionResponse(
            requestId=request_id,
            engine=ocr.engine,
            platform=platform,
            scene=normalized_scene,
            pageType=result.pageType,
            contentType=result.contentType,
            nextAction=result.nextAction,
            rawText=ocr.raw_text,
            result=result,
            warnings=warnings,
            elapsedMs=int((time.time() - start) * 1000),
        )

    def _normalize_scene_by_filename(self, filename: str, scene: str) -> str:
        scene_upper = (scene or "UNKNOWN").upper().replace("-", "_")
        scene_aliases = {
            "DOUYIN_OVERVIEW": "DATA_OVERVIEW",
            "OVERVIEW": "DATA_OVERVIEW",
            "DOUYIN_OVERVIEW_CHART": "DATA_CHART",
            "OVERVIEW_CHART": "DATA_CHART",
            "DOUYIN_FLOW_ANALYSIS": "FLOW_ANALYSIS",
        }
        if scene_upper in scene_aliases:
            return scene_aliases[scene_upper]
        if scene_upper in {"ACCOUNT_OVERVIEW", "CONTENT_PAGE", "DATA_OVERVIEW", "DATA_CHART", "FLOW_ANALYSIS"}:
            return scene_upper
        if any(keyword in filename for keyword in ["账号页面", "账号页", "账号封面", "主页", "首页资料", "个人页", "个人主页"]):
            return "ACCOUNT_OVERVIEW"
        if any(keyword in filename for keyword in ["数据页1", "总览", "overview", "播放量", "点赞量"]):
            return "DATA_OVERVIEW"
        if any(keyword in filename for keyword in ["数据页2", "趋势", "图表", "chart", "粉丝播放"]):
            return "DATA_CHART"
        if any(keyword in filename for keyword in ["数据页3", "流量分析", "flow", "封面点击", "评论进入"]):
            return "FLOW_ANALYSIS"
        return scene

    def _normalize_content_type_by_filename(self, filename: str, content_type: str) -> str:
        upper = (content_type or "AUTO").upper().replace("-", "_")
        if upper in {"IMAGE_TEXT", "VIDEO", "ACCOUNT_OVERVIEW"}:
            return upper
        if any(keyword in filename for keyword in ["图文", "笔记", "图片", "小红书笔记"]):
            return "IMAGE_TEXT"
        if any(keyword in filename for keyword in ["视频", "短视频", "播放", "完播"]):
            return "VIDEO"
        if any(keyword in filename for keyword in ["账号页面", "账号页", "账号封面", "主页", "首页资料", "个人页", "个人主页"]):
            return "ACCOUNT_OVERVIEW"
        return "AUTO"

    def _debug_print(self, title: str, payload: dict) -> None:
        print(f"\n===== {title} =====", flush=True)
        print(json.dumps(payload, ensure_ascii=False, default=str, indent=2), flush=True)
        print(f"===== {title} END =====\n", flush=True)
