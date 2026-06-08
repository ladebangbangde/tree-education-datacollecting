from dataclasses import dataclass
from pathlib import Path

from app.core.config import settings


@dataclass
class OcrOutput:
    raw_text: str
    engine: str


class OcrEngine:
    def recognize(self, image_path: Path) -> OcrOutput:
        if settings.ocr_engine.lower() == "paddle":
            return self._paddle(image_path)
        return self._mock(image_path)

    def _mock(self, image_path: Path) -> OcrOutput:
        return OcrOutput(
            raw_text="账号 树教育澳洲留学\n澳洲留学申请避坑指南\n播放 1.2万\n点赞 800\n评论 96\n收藏 300\n分享 20",
            engine="mock",
        )

    def _paddle(self, image_path: Path) -> OcrOutput:
        try:
            from paddleocr import PaddleOCR
        except Exception as exc:
            raise RuntimeError("PaddleOCR is not installed. Use docker-compose.paddle.yml or OCR_ENGINE=mock") from exc

        # 拍屏/手机截图中的指标数字很小，默认 det_limit_side_len=960 会压缩长边，容易漏掉涨粉量这种单个数字。
        # 提高检测长边上限，优先保证运营数据页的小数字被识别出来。
        ocr = PaddleOCR(use_angle_cls=True, lang="ch", det_limit_side_len=1600, det_limit_type="max")
        result = ocr.ocr(str(image_path), cls=True)
        lines: list[str] = []
        for page in result or []:
            for item in page or []:
                if len(item) >= 2 and item[1]:
                    lines.append(str(item[1][0]))
        return OcrOutput(raw_text="\n".join(lines), engine="paddle")
