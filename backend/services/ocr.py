import io
import logging
import re
from typing import List, Dict, Optional, Tuple
from PIL import Image, ImageEnhance, ImageFilter
import cv2
import numpy as np
from rapidocr_onnxruntime import RapidOCR
from rapidfuzz import fuzz
from datetime import datetime, timezone

from core.config import settings

from services.aadhaar_utils import extract_mobile_from_aadhaar
logger = logging.getLogger("loanease.ocr")

# Memory guardrails for OCR preprocessing
MAX_IMAGE_SIDE = 2200
MAX_IMAGE_PIXELS = 4_500_000
MIN_WIDTH = 1200


def _is_bad_allocation_error(exc: Exception) -> bool:
    message = str(exc).lower()
    return "bad allocation" in message or "onnxruntimeerror" in message


def _downscale_for_onnx(candidate: np.ndarray, max_side: int = 1280) -> np.ndarray:
    height, width = candidate.shape[:2]
    longest_side = max(height, width)
    if longest_side <= max_side:
        return candidate

    scale = max_side / float(longest_side)
    new_width = max(320, int(width * scale))
    new_height = max(320, int(height * scale))
    return cv2.resize(candidate, (new_width, new_height), interpolation=cv2.INTER_AREA)

# Global OCR engine
_ocr_engine: Optional[RapidOCR] = None

def init_ocr():
    """Initialize RapidOCR engine"""
    global _ocr_engine
    try:
        _ocr_engine = RapidOCR()
        logger.info("RapidOCR engine initialized")
    except Exception as e:
        logger.error(f"Failed to initialize OCR: {e}")
        _ocr_engine = None

def ocr_ready() -> bool:
    """Check if OCR engine is ready"""
    return _ocr_engine is not None

def preprocess_pdf(file_bytes: bytes) -> List[np.ndarray]:
    """Extract and preprocess images from PDF files using PyMuPDF"""
    logger.info(f"Starting PDF processing, file size: {len(file_bytes)} bytes")
    
    try:
        import fitz  # PyMuPDF
        import io
        
        # Load PDF from bytes
        pdf_document = fitz.open(stream=file_bytes, filetype="pdf")
        logger.info(f"PDF loaded successfully, pages: {len(pdf_document)}")
        
        candidates = []
        
        # Process first few pages (usually PAN cards are 1-2 pages)
        max_pages = min(len(pdf_document), 3)
        
        for page_num in range(max_pages):
            try:
                page = pdf_document[page_num]
                logger.info(f"Processing PDF page {page_num + 1}")
                
                # Get page as image with high DPI
                mat = fitz.Matrix(3.0, 3.0)  # 3x zoom for better quality
                pix = page.get_pixmap(matrix=mat)
                
                # Convert to PIL Image
                img_data = pix.tobytes("ppm")
                pil_image = Image.open(io.BytesIO(img_data))
                
                if pil_image.mode != 'RGB':
                    pil_image = pil_image.convert('RGB')
                
                logger.info(f"PDF page {page_num + 1} converted to image, size: {pil_image.size}")
                
                # Convert to numpy array
                img_array = np.array(pil_image)
                
                # Apply basic preprocessing
                gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
                
                # Multiple preprocessing methods for PDF
                # Method 1: Adaptive threshold
                thresh1 = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
                candidates.append(cv2.cvtColor(thresh1, cv2.COLOR_GRAY2RGB))
                
                # Method 2: Otsu's thresholding
                _, thresh2 = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                candidates.append(cv2.cvtColor(thresh2, cv2.COLOR_GRAY2RGB))
                
                # Add original
                candidates.append(img_array)
                
                logger.info(f"Successfully processed PDF page {page_num + 1}")
                
            except Exception as e:
                logger.warning(f"Failed to process PDF page {page_num}: {e}")
                continue
        
        # Close PDF
        pdf_document.close()
        
        if not candidates:
            raise ValueError("No valid images found in PDF")
            
        logger.info(f"PDF preprocessing completed, {len(candidates)} candidates generated")
        return candidates
        
    except ImportError:
        logger.error("PyMuPDF (fitz) not available for PDF processing")
        raise ValueError("PDF processing requires PyMuPDF. Please install it with: pip install PyMuPDF")
    except Exception as e:
        logger.error(f"PDF preprocessing failed: {e}")
        raise ValueError(f"Could not process PDF: {str(e)}")

def preprocess_image(file_bytes: bytes, extension: str) -> List[np.ndarray]:
    """Enhanced image preprocessing for OCR with PDF support"""
    
    try:
        # Handle PDF files separately
        if extension == 'pdf':
            return preprocess_pdf(file_bytes)
        
        # Load image with better error handling
        img = Image.open(io.BytesIO(file_bytes))
        if img.mode != 'RGB':
            img = img.convert('RGB')

        # Downscale very large inputs to prevent ONNX bad allocation
        width, height = img.size
        pixel_count = width * height

        if width > MAX_IMAGE_SIDE or height > MAX_IMAGE_SIDE or pixel_count > MAX_IMAGE_PIXELS:
            side_scale = min(MAX_IMAGE_SIDE / max(width, height), 1.0)
            pixel_scale = min((MAX_IMAGE_PIXELS / float(pixel_count)) ** 0.5, 1.0)
            scale = min(side_scale, pixel_scale)
            target_w = max(600, int(width * scale))
            target_h = max(600, int(height * scale))
            img = img.resize((target_w, target_h), Image.Resampling.LANCZOS)
        
        # Enhance image
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.5)
        
        enhancer = ImageEnhance.Sharpness(img)
        img = enhancer.enhance(1.2)
        
        # Denoise
        img = img.filter(ImageFilter.MedianFilter(size=3))
        
        # Upscale for better OCR
        if img.width < MIN_WIDTH:
            scale = MIN_WIDTH / img.width
            new_height = int(img.height * scale)
            img = img.resize((MIN_WIDTH, new_height), Image.Resampling.LANCZOS)
        
        # Convert to numpy array
        img_array = np.array(img)
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        
        # Multiple preprocessing methods
        candidates = []
        
        # Method 1: Adaptive Gaussian
        thresh1 = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
        candidates.append(cv2.cvtColor(thresh1, cv2.COLOR_GRAY2RGB))
        
        # Method 2: Adaptive Mean
        thresh2 = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 11, 2)
        candidates.append(cv2.cvtColor(thresh2, cv2.COLOR_GRAY2RGB))
        
        # Method 3: Otsu's thresholding
        _, thresh3 = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        candidates.append(cv2.cvtColor(thresh3, cv2.COLOR_GRAY2RGB))
        
        # Add original
        candidates.append(img_array)
        
        return candidates
        
    except Exception as e:
        logger.error(f"Image preprocessing failed: {e}")
        # Return a simple fallback - just convert to array without processing
        try:
            img = Image.open(io.BytesIO(file_bytes))
            if img.mode != 'RGB':
                img = img.convert('RGB')
            return [np.array(img)]
        except Exception as fallback_e:
            logger.error(f"Fallback preprocessing also failed: {fallback_e}")
            raise ValueError(f"Unable to process image: {str(e)}")

def run_ocr(preprocessed_img: List[np.ndarray]) -> Tuple[str, float]:
    """Run OCR on preprocessed images"""
    global _ocr_engine
    
    if not _ocr_engine:
        raise RuntimeError("OCR engine not initialized")
    
    best_text = ""
    best_conf = 0.0
    
    for idx, candidate in enumerate(preprocessed_img):
        try:
            # Secondary safety check before ONNX inference
            if candidate.shape[0] * candidate.shape[1] > MAX_IMAGE_PIXELS:
                scale = (MAX_IMAGE_PIXELS / float(candidate.shape[0] * candidate.shape[1])) ** 0.5
                new_w = max(600, int(candidate.shape[1] * scale))
                new_h = max(600, int(candidate.shape[0] * scale))
                candidate = cv2.resize(candidate, (new_w, new_h), interpolation=cv2.INTER_AREA)

            candidate = np.ascontiguousarray(candidate.astype(np.uint8, copy=False))

            result, _ = _ocr_engine(candidate)
            if result:
                text_lines = [item[1] for item in result]
                text = "\n".join(text_lines).strip()
                
                # Calculate confidence
                conf_values = []
                for item in result:
                    if len(item) >= 3:
                        try:
                            conf_values.append(float(item[2]))
                        except (ValueError, TypeError):
                            pass
                
                avg_conf = sum(conf_values) / len(conf_values) if conf_values else 0.0
                
                if avg_conf > best_conf:
                    best_text = text
                    best_conf = avg_conf
                    
        except Exception as e:
            if _is_bad_allocation_error(e):
                try:
                    emergency_candidate = _downscale_for_onnx(candidate, max_side=960)
                    emergency_candidate = np.ascontiguousarray(emergency_candidate.astype(np.uint8, copy=False))
                    result, _ = _ocr_engine(emergency_candidate)
                    if result:
                        text_lines = [item[1] for item in result]
                        text = "\n".join(text_lines).strip()

                        conf_values = []
                        for item in result:
                            if len(item) >= 3:
                                try:
                                    conf_values.append(float(item[2]))
                                except (ValueError, TypeError):
                                    pass

                        avg_conf = sum(conf_values) / len(conf_values) if conf_values else 0.0
                        if avg_conf > best_conf:
                            best_text = text
                            best_conf = avg_conf
                        logger.info("OCR recovered after emergency downscale (candidate=%s, conf=%.2f)", idx, avg_conf)
                        continue
                except Exception as emergency_exc:
                    logger.warning(
                        "OCR memory error on candidate %s; emergency retry failed (%s)",
                        idx,
                        str(emergency_exc).splitlines()[0],
                    )
                    continue

            logger.warning("OCR attempt failed (candidate=%s): %s", idx, str(e).splitlines()[0])
            continue
    
    return best_text, round(max(0.0, min(1.0, best_conf)), 2)

# Enhanced extractors
def extract_pan(ocr_text: str) -> Dict:
    """Extract PAN card information with relaxed validation"""
    lines = [line.strip() for line in ocr_text.splitlines() if line.strip()]
    
    # More flexible PAN pattern - allow spaces and mixed case
    pan_patterns = [
        re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b"),  # Standard format
        re.compile(r"\b[A-Z]{5}\s?[0-9]{4}\s?[A-Z]\b"),  # With spaces
        re.compile(r"\b[a-zA-Z]{5}\s?[0-9]{4}\s?[a-zA-Z]\b"),  # Mixed case
    ]
    
    pan_number = None
    for pattern in pan_patterns:
        pan_match = pattern.search(ocr_text)
        if pan_match:
            pan_number = re.sub(r"\s", "", pan_match.group(0).upper())
            break
    
    # More flexible name extraction
    name = None
    name_keywords = ["NAME", "INCOME TAX", "DEPARTMENT", "PERMANENT", "ACCOUNT"]
    
    # Try multiple approaches for name extraction
    for i, line in enumerate(lines):
        line_upper = line.upper()
        # Check for name keywords
        if any(keyword in line_upper for keyword in name_keywords):
            # Look at next few lines for potential name
            for j in range(i + 1, min(i + 4, len(lines))):
                potential_name = lines[j].strip()
                # More relaxed name validation
                if (len(potential_name) >= 3 and 
                    len(potential_name.split()) >= 2 and  # At least 2 words
                    any(c.isalpha() for c in potential_name) and  # Contains letters
                    len(re.sub(r"[^a-zA-Z\s]", "", potential_name)) > len(potential_name) * 0.7):  # Mostly letters
                    name = potential_name.title()
                    break
            if name:
                break
    
    # If no name found with keywords, try heuristic approach
    if not name:
        for line in lines:
            # Skip lines with numbers or common non-name words
            if (len(line) >= 3 and 
                len(line.split()) >= 2 and
                not any(char.isdigit() for char in line) and
                not any(keyword in line.upper() for keyword in ["GOVERNMENT", "INDIA", "DEPARTMENT", "TAX", "CARD", "PAN"])):
                name = line.title()
                break
    
    # More flexible DOB extraction
    dob_patterns = [
        r"\b(\d{2}/\d{2}/\d{4})\b",
        r"\b(\d{2}-\d{2}-\d{4})\b",
        r"\b(\d{2}\s+\d{2}\s+\d{4})\b",  # Space separated
        r"\bDOB[:\s]*(\d{2}/\d{2}/\d{4})\b",  # With DOB prefix
    ]
    
    dob = None
    for pattern in dob_patterns:
        match = re.search(pattern, ocr_text)
        if match:
            dob = match.group(1)
            break
    
    # Calculate age with more flexible parsing
    age = None
    if dob:
        try:
            # Try different date formats
            for fmt in ["%d/%m/%Y", "%d-%m-%Y", "%d %m %Y"]:
                try:
                    dob_dt = datetime.strptime(dob, fmt)
                    now = datetime.now(timezone.utc)
                    age = now.year - dob_dt.year - ((now.month, now.day) < (dob_dt.month, dob_dt.day))
                    break
                except ValueError:
                    continue
        except Exception:
            pass
    
    # If DOB can't be read from OCR, don't block — assume eligible
    age_eligible = True
    if age is not None:
        age_eligible = 18 <= age <= 75

    return {
        "pan_number": pan_number,
        "name": name,
        "date_of_birth": dob,
        "age": age,
        "age_eligible": age_eligible
    }

def extract_aadhaar(ocr_text: str) -> Dict:
    """Extract Aadhaar card information with relaxed validation"""
    lines = [line.strip() for line in ocr_text.splitlines() if line.strip()]
    normalized_lines = [re.sub(r"\s+", " ", line).strip() for line in lines]
    
    # More flexible Aadhaar patterns
    aadhaar_patterns = [
        re.compile(r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}\b"),  # Standard format
        re.compile(r"\b\d{2}[\s-]?\d{2}[\s-]?\d{2}[\s-]?\d{2}[\s-]?\d{2}[\s-]?\d{2}\b"),  # 2-digit groups
        re.compile(r"\b\d{12}\b"),  # Continuous 12 digits
        re.compile(r"\b(\d{4}\s\d{4}\s\d{4})\b"),  # Space separated
    ]
    
    aadhaar_number = None
    aadhaar_last4 = None
    
    for pattern in aadhaar_patterns:
        matches = pattern.findall(ocr_text)
        if matches:
            # Take the first valid match
            for match in matches:
                aadhaar_clean = re.sub(r"[\s-]", "", match)
                if len(aadhaar_clean) == 12 and aadhaar_clean.isdigit():
                    aadhaar_number = aadhaar_clean
                    aadhaar_last4 = aadhaar_clean[-4:]
                    break
            if aadhaar_number:
                break
    
    # More flexible name extraction
    name = None
    excluded_keywords = ["GOVERNMENT", "INDIA", "UIDAI", "AADHAAR", "MALE", "FEMALE", "UNIQUE", "IDENTIFICATION", "AUTHORITY"]
    relation_keywords = ["S/O", "D/O", "W/O", "C/O", "HUSBAND", "FATHER", "MOTHER"]
    
    # Try multiple approaches for name
    for idx, line in enumerate(normalized_lines):
        if len(line) >= 3:
            # More relaxed name validation
            line_upper = line.upper()
            if not any(keyword in line_upper for keyword in excluded_keywords):
                # Direct labeled forms like "Name: Rahul Kumar".
                labeled_match = re.search(r"\bname\b\s*[:\-]?\s*(.+)$", line, flags=re.IGNORECASE)
                if labeled_match:
                    candidate = re.sub(r"[^a-zA-Z\s]", " ", labeled_match.group(1)).strip()
                    if len(candidate) >= 3:
                        name = re.sub(r"\s+", " ", candidate).title()
                        break

                # Prefer the line immediately after a name label.
                if idx > 0 and "NAME" in normalized_lines[idx - 1].upper():
                    candidate = re.sub(r"[^a-zA-Z\s]", " ", line).strip()
                    if len(candidate) >= 3:
                        name = re.sub(r"\s+", " ", candidate).title()
                        break

                # Mixed label/value on the same line.
                if "NAME" in line_upper:
                    candidate = re.sub(r"(?i).*?\bname\b\s*[:\-]?\s*", "", line)
                    candidate = re.sub(r"[^a-zA-Z\s]", " ", candidate).strip()
                    if len(candidate) >= 3:
                        name = re.sub(r"\s+", " ", candidate).title()
                        break

                # Check if line looks like a name (mostly letters, allow single-word names too)
                words = line.split()
                letter_ratio = len(re.sub(r"[^a-zA-Z\s]", "", line)) / max(1, len(line))
                if (
                    len(words) >= 1
                    and not any(char.isdigit() for char in line)
                    and letter_ratio >= 0.35
                    and not any(keyword in line_upper for keyword in relation_keywords)
                ):
                    candidate = re.sub(r"[^a-zA-Z\s]", " ", line).strip()
                    if len(candidate) >= 3:
                        name = re.sub(r"\s+", " ", candidate).title()
                        break
    
    # If no name found, try heuristic approach
    if not name:
        for i, line in enumerate(normalized_lines):
            # Look for lines that might contain names
            if (len(line) >= 3 and 
                not any(char.isdigit() for char in line) and
                i < len(lines) - 1):  # Not the last line
                candidate = re.sub(r"[^a-zA-Z\s]", " ", line).strip()
                if len(candidate) >= 3:
                    name = re.sub(r"\s+", " ", candidate).title()
                break

    if not name:
        # Final fallback: pick the strongest all-alpha line that is not a keyword blob.
        best_candidate = ""
        best_score = 0
        for line in normalized_lines:
            if any(keyword in line.upper() for keyword in excluded_keywords):
                continue
            candidate = re.sub(r"[^a-zA-Z\s]", " ", line).strip()
            if not candidate:
                continue
            alpha_count = len(re.sub(r"[^a-zA-Z]", "", candidate))
            word_count = len(candidate.split())
            score = alpha_count + (word_count * 3)
            if score > best_score and alpha_count >= 3:
                best_score = score
                best_candidate = candidate
        if best_candidate:
            name = re.sub(r"\s+", " ", best_candidate).title()

    if not name:
        # Last fallback: inspect the first few OCR lines for a short name-like token.
        for line in normalized_lines[:8]:
            candidate = re.sub(r"[^a-zA-Z\s]", " ", line).strip()
            if not candidate:
                continue
            words = candidate.split()
            if 1 <= len(words) <= 4 and len(candidate) >= 3:
                upper = candidate.upper()
                if not any(keyword in upper for keyword in excluded_keywords) and not any(char.isdigit() for char in candidate):
                    name = re.sub(r"\s+", " ", candidate).title()
                    break

    # Cleanup noisy OCR name tokens frequently seen on Aadhaar
    if name:
        cleaned = re.sub(r"\b(S/O|D/O|W/O|C/O|DOB|YO|YOB|YEAR OF BIRTH)\b", " ", name, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s+", " ", cleaned).strip(" -:,")
        name = cleaned if cleaned else name
    
    # More flexible DOB extraction
    dob_patterns = [
        r"\b(\d{2}/\d{2}/\d{4})\b",
        r"\b(\d{2}-\d{2}-\d{4})\b",
        r"\b(\d{2}\s+\d{2}\s+\d{4})\b",  # Space separated
        r"\bDOB[:\s]*(\d{2}/\d{2}/\d{4})\b",  # With DOB prefix
        r"\bDate of Birth[:\s]*(\d{2}/\d{2}/\d{4})\b",  # Full prefix
    ]
    
    dob = None
    for pattern in dob_patterns:
        match = re.search(pattern, ocr_text, re.IGNORECASE)
        if match:
            dob = match.group(1)
            break
    
    # Calculate age with more flexible parsing
    age = None
    if dob:
        try:
            # Try different date formats
            for fmt in ["%d/%m/%Y", "%d-%m-%Y", "%d %m %Y"]:
                try:
                    dob_dt = datetime.strptime(dob, fmt)
                    now = datetime.now(timezone.utc)
                    age = now.year - dob_dt.year - ((now.month, now.day) < (dob_dt.month, dob_dt.day))
                    break
                except ValueError:
                    continue
        except Exception:
            pass
    
    # More flexible gender extraction
    gender = "Unknown"
    text_upper = ocr_text.upper()
    if "MALE" in text_upper or "M" in text_upper:
        gender = "Male"
    elif "FEMALE" in text_upper or "F" in text_upper:
        gender = "Female"
    
    # If DOB can't be read from OCR, don't block — assume eligible
    age_eligible = True

    mobile_number = extract_mobile_from_aadhaar(ocr_text)
    mobile_last4 = mobile_number[-4:] if mobile_number else None
    if age is not None:
        age_eligible = 18 <= age <= 75
    return {
        "aadhaar_number": aadhaar_number,
        "aadhaar_last4": aadhaar_last4,
        "name": name,
        "date_of_birth": dob,
        "age": age,
        "gender": gender,
        "age_eligible": age_eligible,
        "mobile_number": mobile_number,
        "mobile_last4": mobile_last4,
    }

def cross_validate_kyc(pan_data: Dict, aadhaar_data: Dict) -> Dict:
    """Cross-validate PAN and Aadhaar data"""
    def _normalize_name(raw: str) -> str:
        text = (raw or "").upper()
        # Remove relation/date markers and common honorifics that reduce fuzzy score.
        text = re.sub(r"\b(S/O|D/O|W/O|C/O|DOB|YOB|YEAR OF BIRTH|MR|MRS|MS|MISS|SHRI|SMT|KUMARI)\b", " ", text)
        text = re.sub(r"[^A-Z\s]", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    pan_name = _normalize_name(pan_data.get("name", ""))
    aadhaar_name = _normalize_name(aadhaar_data.get("name", ""))
    
    # Name matching
    name_score = 0
    name_status = "MISMATCH"
    
    if pan_name and aadhaar_name:
        # Multiple fuzzy matching methods
        scores = [
            fuzz.token_sort_ratio(pan_name, aadhaar_name),
            fuzz.token_set_ratio(pan_name, aadhaar_name),
            fuzz.partial_ratio(pan_name, aadhaar_name),
            fuzz.ratio(pan_name, aadhaar_name)
        ]
        
        name_score = int(round(sum(scores) / len(scores)))

        # Containment boost for OCR cases like "RAHUL KUMAR" vs "RAHUL"
        if len(pan_name) >= 4 and len(aadhaar_name) >= 4:
            if pan_name in aadhaar_name or aadhaar_name in pan_name:
                name_score = max(name_score, 75)

        # Token overlap boost for reordered/partially missed names
        pan_tokens = {t for t in pan_name.split() if len(t) >= 2}
        aadhaar_tokens = {t for t in aadhaar_name.split() if len(t) >= 2}
        if pan_tokens and aadhaar_tokens:
            overlap = len(pan_tokens & aadhaar_tokens) / max(1, min(len(pan_tokens), len(aadhaar_tokens)))
            if overlap >= 0.5:
                name_score = max(name_score, 70)
            elif overlap >= 0.34:
                name_score = max(name_score, 58)
        
        if name_score >= 65:
            name_status = "MATCH"
        elif name_score >= 45:
            name_status = "PARTIAL"
    
    # DOB matching
    dob_match = False
    pan_dob = pan_data.get("date_of_birth")
    aadhaar_dob = aadhaar_data.get("date_of_birth")
    
    if pan_dob and aadhaar_dob:
        dob_match = pan_dob == aadhaar_dob
    
    age_eligible = (
        pan_data.get("age_eligible", True) or
        aadhaar_data.get("age_eligible", True)
    )

    # Overall KYC status - relaxed for noisy Aadhaar OCR
    if name_score >= 55 and (dob_match or age_eligible):
        kyc_status = "VERIFIED"
    elif name_score >= 40 or (name_score >= 30 and dob_match):
        kyc_status = "PARTIAL"
    else:
        kyc_status = "FAILED"
    
    return {
        "kyc_status": kyc_status,
        "name_match_score": name_score,
        "name_match_status": name_status,
        "dob_match": dob_match,
        "age_eligible": age_eligible,
        "overall_kyc_passed": (kyc_status in ["VERIFIED", "PARTIAL"]) or (name_score >= 35 and age_eligible)
    }
