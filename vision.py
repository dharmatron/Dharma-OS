"""
Guardian Bot - Vision Module
OCR reading of the YK-8000C monitor screen.
Designed to be improved over time as you refine the color masks.
"""
import logging
import re
import cv2
import numpy as np

logger = logging.getLogger(__name__)

# Color ranges for the YK-8000C display (HSV)
# These match the standard Yonker color scheme:
#   Green  = Heart Rate (HR)
#   Cyan   = SpO2
#   Yellow = NIBP
#   White  = Temperature / PI

COLOR_MASKS = {
    "hr": {
        "lower": np.array([35,  50,  50]),
        "upper": np.array([85, 255, 255]),
        "label": "HR",
    },
    "spo2": {
        "lower": np.array([85,  50,  50]),
        "upper": np.array([130, 255, 255]),
        "label": "SpO2",
    },
    "pi": {
        "lower": np.array([0,   0,  200]),
        "upper": np.array([180, 30, 255]),
        "label": "PI",
    },
}

def _extract_number(text: str) -> str | None:
    """Pull the first plausible number from OCR text."""
    nums = re.findall(r'\b\d{1,3}\b', text)
    return nums[0] if nums else None

def ocr_vitals(img_path: str) -> dict | None:
    """
    Read vital signs from a monitor photo.
    Returns dict like: {"hr": "72", "spo2": "98", "pi": "2.1"}
    or None if the image can't be processed.
    """
    try:
        import pytesseract
    except ImportError:
        logger.warning("pytesseract not installed. OCR unavailable.")
        return None

    try:
        img = cv2.imread(img_path)
        if img is None:
            logger.error(f"Could not read image: {img_path}")
            return None

        # Upscale for better OCR accuracy on small monitor text
        scale = 2
        img = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)

        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        results = {}

        for vital_key, params in COLOR_MASKS.items():
            mask = cv2.inRange(hsv, params["lower"], params["upper"])

            # Morphological cleanup to remove noise
            kernel = np.ones((3, 3), np.uint8)
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

            # Apply mask to image
            extracted = cv2.bitwise_and(img, img, mask=mask)
            gray = cv2.cvtColor(extracted, cv2.COLOR_BGR2GRAY)
            _, thresh = cv2.threshold(gray, 50, 255, cv2.THRESH_BINARY)

            text = pytesseract.image_to_string(thresh, config="--psm 7 -c tessedit_char_whitelist=0123456789.")
            number = _extract_number(text.strip())

            if number:
                results[vital_key] = number
                logger.info(f"OCR {params['label']}: {number}")

        return results if results else None

    except Exception as e:
        logger.error(f"OCR error: {e}")
        return None

def validate_vitals(vitals: dict) -> tuple[bool, list[str]]:
    """
    Basic sanity check on OCR results.
    Returns (is_valid, list_of_warnings).
    Useful for catching misreads before logging.
    """
    warnings = []

    if "hr" in vitals:
        hr = int(vitals["hr"])
        if not (30 <= hr <= 220):
            warnings.append(f"HR {hr} outside plausible range (30-220)")

    if "spo2" in vitals:
        spo2 = int(vitals["spo2"])
        if not (70 <= spo2 <= 100):
            warnings.append(f"SpO2 {spo2} outside plausible range (70-100)")

    return len(warnings) == 0, warnings
