from __future__ import annotations

import io
import logging
import cv2
import numpy as np
from PIL import Image

logger = logging.getLogger("kyc.ocr")

MAX_UPLOAD_BYTES = 5 * 1024 * 1024
_rapidocr_engine = None


class UnsupportedDocumentError(ValueError):
    pass


def _load_pdf_with_pymupdf(file_bytes: bytes) -> Image.Image:
    try:
        import fitz  # PyMuPDF
    except ImportError:
        raise UnsupportedDocumentError(
            "PDF upload requires PyMuPDF. Run: pip install pymupdf"
        )

    doc = fitz.open(stream=file_bytes, filetype="pdf")
    if len(doc) == 0:
        raise UnsupportedDocumentError("PDF has no pages")

    page = doc[0]
    # Render at 2x scale for better OCR quality
    mat = fitz.Matrix(2.0, 2.0)
    pix = page.get_pixmap(matrix=mat)
    img_bytes = pix.tobytes("png")
    doc.close()

    nparr = np.frombuffer(img_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        raise UnsupportedDocumentError("Failed to decode PDF page as image")

    logger.info(f"PDF converted via PyMuPDF, shape: {img.shape}")
    return Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))


def _load_image_from_bytes(file_bytes: bytes, extension: str) -> Image.Image:
    ext = extension.lower().strip(".")
    if ext in {"jpg", "jpeg", "png", "bmp"}:
        img = Image.open(io.BytesIO(file_bytes)).convert("RGB")
        logger.info(f"Image loaded: {img.size}")
        return img
    if ext == "pdf":
        return _load_pdf_with_pymupdf(file_bytes)
    raise UnsupportedDocumentError(
        f"Unsupported file type: .{ext}. Upload JPG, PNG or PDF."
    )


def _upscale_for_ocr(img: Image.Image) -> Image.Image:
    min_width = 800
    if img.width >= min_width:
        return img
    scale = min_width / float(img.width)
    new_height = int(img.height * scale)
    return img.resize((min_width, new_height), Image.Resampling.LANCZOS)


def preprocess_image(file_bytes: bytes, extension: str) -> list[np.ndarray]:
    """Convert file bytes to multiple preprocessed image variants for OCR."""
    pil_img = _load_image_from_bytes(file_bytes, extension)
    pil_img = _upscale_for_ocr(pil_img)
    img = np.array(pil_img)  # RGB

    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)

    # CLAHE contrast enhancement
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    contrast = clahe.apply(gray)

    # Denoise
    denoised = cv2.fastNlMeansDenoising(contrast, h=10)

    # Adaptive threshold
    thresh = cv2.adaptiveThreshold(
        denoised, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY, 11, 2
    )

    # Convert all variants back to RGB for RapidOCR
    gray_rgb = cv2.cvtColor(gray, cv2.COLOR_GRAY2RGB)
    contrast_rgb = cv2.cvtColor(contrast, cv2.COLOR_GRAY2RGB)
    thresh_rgb = cv2.cvtColor(thresh, cv2.COLOR_GRAY2RGB)

    return [img, gray_rgb, contrast_rgb, thresh_rgb]


def run_ocr(preprocessed_img: np.ndarray | list[np.ndarray]) -> tuple[str, float]:
    """Run OCR across all image variants and return the best result."""
    global _rapidocr_engine

    try:
        from rapidocr_onnxruntime import RapidOCR
    except ImportError:
        raise RuntimeError(
            "RapidOCR not available. Install: pip install rapidocr-onnxruntime"
        )

    if _rapidocr_engine is None:
        logger.info("Initializing RapidOCR engine...")
        _rapidocr_engine = RapidOCR()
        logger.info("RapidOCR ready")

    candidates = (
        preprocessed_img if isinstance(preprocessed_img, list) else [preprocessed_img]
    )
    best_text = ""
    best_conf = 0.0
    best_score = -1.0

    for i, candidate in enumerate(candidates):
        try:
            rapid_result, elapse = _rapidocr_engine(candidate)
        except Exception as e:
            logger.warning(f"OCR failed on variant {i}: {e}")
            continue

        if not rapid_result:
            continue

        text_lines = []
        conf_vals = []
        for item in rapid_result:
            if len(item) >= 2:
                text_lines.append(str(item[1]))
            if len(item) >= 3:
                try:
                    conf_vals.append(float(item[2]))
                except Exception:
                    pass

        text = "\n".join(text_lines).strip()
        avg_conf = sum(conf_vals) / len(conf_vals) if conf_vals else 0.0
        score = avg_conf + min(len(text) / 250.0, 0.25)

        elapsed_value = elapse
        if isinstance(elapsed_value, (list, tuple)):
            try:
                elapsed_value = sum(float(item) for item in elapsed_value)
            except (TypeError, ValueError):
                elapsed_value = len(elapsed_value)

        logger.info(
            f"OCR variant {i}: {len(text_lines)} lines, "
            f"conf={avg_conf:.2f}, score={score:.2f}, "
            f"elapsed={float(elapsed_value):.2f}s"
        )

        if score > best_score:
            best_score = score
            best_text = text
            best_conf = avg_conf

    if best_text:
        logger.info(
            f"OCR complete. Best text ({len(best_text)} chars), "
            f"conf={best_conf:.2f}\nPreview: {best_text[:300]}"
        )
        return best_text, round(max(0.0, min(1.0, best_conf)), 2)

    logger.warning("OCR found no text in any variant")
    return "", 0.0
