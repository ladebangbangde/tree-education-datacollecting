import json
import logging
import time
import uuid
from pathlib import Path

from fastapi import UploadFile

from app.core.config import settings
from app.core.errors import BadRequestError
from app.schemas.recognition import RecognitionResponse
from app.services.ocr_engine import OcrEngine
from app.services.social_metrics_extractor import SocialMetricsExtractor

logger = logging.getLogger("tree_education_datacollecting.recognition")


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
        logger.info(
            "recognition_start requestId=%s filename=%s contentType=%s size=%s platform=%s scene=%s normalizedScene=%s engine=%s",
            request_id,
            original_filename,
            file.content_type,
            len(content),
            platform,
            scene,
            normalized_scene,
            settings.ocr_engine,
        )
        try:
            ocr = self.ocr.recognize(image_path)
            logger.info(
                "ocr_raw_text requestId=%s filename=%s engine=%s rawTextLength=%s\n===== OCR RAW TEXT BEGIN =====\n%s\n===== OCR RAW TEXT END =====",
                request_id,
                original_filename,
                ocr.engine,
                len(ocr.raw_text or ""),
                ocr.raw_text or "",
            )
            result = self.extractor.extract(ocr.raw_text, platform=platform, scene=normalized_scene)
            logger.info(
                "ocr_parsed_result requestId=%s filename=%s result=%s",
                request_id,
                original_filename,
                json.dumps(result.model_dump(), ensure_ascii=False),
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
        finally:
            try:
                image_path.unlink(missing_ok=True)
            except Exception:
                pass

    def _normalize_scene_by_filename(self, filename: str, scene: str) -> str:
        if any(keyword in filename for keyword in ["账号页面", "账号页", "账号封面", "主页", "首页资料", "个人页", "个人主页"]):
            return "ACCOUNT_OVERVIEW"
        return scene
