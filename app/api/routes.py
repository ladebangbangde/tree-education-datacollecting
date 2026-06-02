from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Header, UploadFile

from app.core.config import settings
from app.core.errors import UnauthorizedError
from app.schemas.recognition import BatchRecognitionResponse, RecognitionResponse
from app.services.recognition_service import RecognitionService

router = APIRouter()
service = RecognitionService()


def verify_internal_token(authorization: Annotated[str | None, Header()] = None) -> None:
    if not settings.internal_api_token:
        return
    if authorization != f"Bearer {settings.internal_api_token}":
        raise UnauthorizedError("invalid internal api token")


@router.get("/health")
def health() -> dict:
    return {"code": 0, "message": "ok", "data": {"service": settings.app_name, "engine": settings.ocr_engine, "status": "UP"}}


@router.post("/recognize", response_model=RecognitionResponse)
async def recognize_image(
    _: Annotated[None, Depends(verify_internal_token)],
    file: UploadFile = File(...),
    platform: str = Form("UNKNOWN"),
    scene: str = Form("UNKNOWN"),
) -> RecognitionResponse:
    return await service.recognize_upload(file=file, platform=platform, scene=scene)


@router.post("/recognize/batch", response_model=BatchRecognitionResponse)
async def recognize_batch(
    _: Annotated[None, Depends(verify_internal_token)],
    files: list[UploadFile] = File(...),
    platform: str = Form("UNKNOWN"),
    scene: str = Form("UNKNOWN"),
) -> BatchRecognitionResponse:
    results = []
    for file in files:
        results.append(await service.recognize_upload(file=file, platform=platform, scene=scene))
    return BatchRecognitionResponse(total=len(results), results=results)
