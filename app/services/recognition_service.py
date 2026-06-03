import json
import time
import uuid
from pathlib import Path

from fastapi import UploadFile

from app.core.config import settings
from app.core.errors import BadRequestError
from app.schemas.recognition import RecognitionResponse
from app.services.ocr_engine import OcrEngine
from app.services.social_metrics_extractor import SocialMetricsExtractor


class RecognitionService:
    def __init__(self) -> None:
        self.ocr = OcrEngine()
        self.extractor = SocialMetricsExtractor()
        self.temp_dir = Path("/tmp/tree-education-datacollecting")
        self.temp_dir.mkdir(parents=True, exist_ok=True)

    async def recognize_upload(self, file: UploadFile, platform: str, scene: str) -> RecognitionResponse:
        start = time.time()
        if not file.content_type or not file.content_type.startswith("image/"):
            raise BadRequestError("file must be an image")
        content = await file.read()
        if len(content) > settings.max_image_mb * 1024 * 1024:
            raise BadRequestError("image is too large")
        original_filename = file.filename or "image.png"
        normalized_scene = self._normalize_scene_by_filename(original_filename, scene)
        suffix = Path(original_filename).suffix or ".png"
        image_path = self.temp_dir / f"{uuid.uuid4().hex}{suffix}"
        image_path.write_bytes(content)
        request_id = uuid.uuid4().hex
        self._debug_print(
            "RECOGNITION START",
            {
                "requestId": request_id,
                "filename": original_filename,
                "contentType": file.content_type,
                "size": len(content),
                "platform": platform,
                "scene": scene,
                "normalizedScene": normalized_scene,
                "ocrEngineSetting": settings.ocr_engine,
                "tempPath": str(image_path),
            },
        )
        try:
            ocr = self.ocr.recognize(image_path)
            print("\n===== OCR RAW TEXT BEGIN =====", flush=True)
            print(ocr.raw_text or "", flush=True)
            print("===== OCR RAW TEXT END =====\n", flush=True)
            result = self.extractor.extract(ocr.raw_text, platform=platform, scene=normalized_scene)
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
            return RecognitionResponse(
                requestId=request_id,
                engine=ocr.engine,
                platform=platform,
                scene=normalized_scene,
                rawText=ocr.raw_text,
                result=result,
                warnings=warnings,
                elapsedMs=int((time.time() - start) * 1000),
            )
        except Exception as exc:
            self._debug_print(
                "RECOGNITION ERROR",
                {
                    "requestId": request_id,
                    "filename": original_filename,
                    "errorType": type(exc).__name__,
                    "error": str(exc),
                },
            )
            raise
        finally:
            try:
                image_path.unlink(missing_ok=True)
            except Exception:
                pass

    def _normalize_scene_by_filename(self, filename: str, scene: str) -> str:
        if any(keyword in filename for keyword in ["账号页面", "账号页", "账号封面", "主页", "首页资料", "个人页", "个人主页"]):
            return "ACCOUNT_OVERVIEW"
        return scene

    def _debug_print(self, title: str, payload: dict) -> None:
        print(f"\n===== {title} =====", flush=True)
        print(json.dumps(payload, ensure_ascii=False, default=str, indent=2), flush=True)
        print(f"===== {title} END =====\n", flush=True)
