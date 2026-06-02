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
        try:
            ocr = self.ocr.recognize(image_path)
            result = self.extractor.extract(ocr.raw_text, platform=platform, scene=normalized_scene)
            return RecognitionResponse(
                requestId=uuid.uuid4().hex,
                engine=ocr.engine,
                platform=platform,
                scene=normalized_scene,
                rawText=ocr.raw_text,
                result=result,
                warnings=[],
                elapsedMs=int((time.time() - start) * 1000),
            )
        finally:
            try:
                image_path.unlink(missing_ok=True)
            except Exception:
                pass

    def _normalize_scene_by_filename(self, filename: str, scene: str) -> str:
        if "账号页面" in filename or "账号页" in filename:
            return "ACCOUNT_OVERVIEW"
        return scene
