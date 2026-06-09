"""
ocr_engine.py — PaddleOCR Wrapper (Track A: Production)
Hindi + English handwriting aur printed text dono read karta hai.
Pre-trained PP-OCRv4 models use hote hain — no training required!

Dual-pass strategy:
1. Hindi model se text extract karo
2. English model se text extract karo
3. Results merge karo confidence scores ke basis pe
"""

import cv2
import numpy as np
from typing import List, Dict, Tuple, Optional
import logging

logger = logging.getLogger(__name__)

# PaddleOCR lazy import — module load hone mein time lagta hai
_ocr_hi = None
_ocr_en = None


def _get_ocr_engine(lang: str):
    """
    PaddleOCR engine ka lazy singleton.
    Pehli baar call pe model download hota hai (~300MB).
    Baad mein cached rehta hai.
    """
    global _ocr_hi, _ocr_en

    try:
        from paddleocr import PaddleOCR

        if lang == "hi" and _ocr_hi is None:
            logger.info("🔄 Loading Hindi OCR model (first time may download ~300MB)...")
            _ocr_hi = PaddleOCR(
                use_angle_cls=True,    # Rotated text bhi detect karega
                lang='hi',            # Hindi/Devanagari script
                show_log=False,        # Suppress PaddleOCR logs
            )
            logger.info("✅ Hindi OCR model loaded!")

        if lang == "en" and _ocr_en is None:
            logger.info("🔄 Loading English OCR model...")
            _ocr_en = PaddleOCR(
                use_angle_cls=True,
                lang='en',
                show_log=False,
            )
            logger.info("✅ English OCR model loaded!")

        return _ocr_hi if lang == "hi" else _ocr_en

    except ImportError:
        logger.error("❌ PaddleOCR not installed! Run: pip install paddleocr paddlepaddle")
        return None


class OCREngine:
    """
    Production OCR Engine — PaddleOCR ke saath Hindi + English support.
    Pre-trained models use karta hai, koi training ki zaroorat nahi.
    """

    def __init__(self, confidence_threshold: float = 0.5):
        """
        Args:
            confidence_threshold: Minimum confidence score (0-1).
                                  Isse kam confidence wale results discard hote hain.
        """
        self.confidence_threshold = confidence_threshold

    def extract_text(
        self,
        image: np.ndarray,
        languages: List[str] = None
    ) -> Dict:
        """
        Image se text extract karta hai using PaddleOCR.

        Args:
            image: OpenCV image (BGR format)
            languages: List of languages to try ["hi", "en"]. Default: both.

        Returns:
            dict with keys:
                - raw_text: Full extracted text (lines joined)
                - lines: List of {text, confidence, bbox} dicts
                - avg_confidence: Average confidence score
                - detected_language: Primary detected language
        """
        if languages is None:
            languages = ["hi", "en"]

        all_results = []

        for lang in languages:
            ocr = _get_ocr_engine(lang)
            if ocr is None:
                logger.warning(f"⚠️ OCR engine for '{lang}' not available, skipping...")
                continue

            try:
                # PaddleOCR expects numpy array or file path
                result = ocr.ocr(image, cls=True)

                if result and result[0]:
                    for line in result[0]:
                        bbox = line[0]           # [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
                        text = line[1][0]         # Detected text
                        confidence = line[1][1]   # Confidence score (0-1)

                        all_results.append({
                            "text": text,
                            "confidence": confidence,
                            "bbox": bbox,
                            "language": lang,
                        })

            except Exception as e:
                logger.error(f"❌ OCR failed for language '{lang}': {e}")
                continue

        # Results filter karo — low confidence wale hatao
        filtered = [
            r for r in all_results
            if r["confidence"] >= self.confidence_threshold
        ]

        # Duplicate/overlapping text remove karo (dual-pass se aate hain)
        merged = self._merge_results(filtered)

        # Final output build karo
        if merged:
            raw_text = "\n".join([r["text"] for r in merged])
            avg_confidence = sum(r["confidence"] for r in merged) / len(merged)
            # Language detect karo — jis language ke zyada results hain woh primary
            lang_counts = {}
            for r in merged:
                lang_counts[r["language"]] = lang_counts.get(r["language"], 0) + 1
            detected_lang = max(lang_counts, key=lang_counts.get)
        else:
            raw_text = ""
            avg_confidence = 0.0
            detected_lang = "en"

        return {
            "raw_text": raw_text,
            "lines": merged,
            "avg_confidence": round(avg_confidence, 3),
            "detected_language": detected_lang,
        }

    def _merge_results(self, results: List[Dict]) -> List[Dict]:
        """
        Dual-pass (Hindi + English) ke results ko merge karta hai.
        Overlapping bounding boxes wale results mein se
        higher confidence wala rakhta hai.
        """
        if not results:
            return []

        # Sort by vertical position (top to bottom reading order)
        sorted_results = sorted(results, key=lambda r: r["bbox"][0][1])

        merged = []
        used = set()

        for i, res1 in enumerate(sorted_results):
            if i in used:
                continue

            best = res1
            used.add(i)

            # Check overlap with remaining results
            for j, res2 in enumerate(sorted_results):
                if j in used or j == i:
                    continue

                if self._bbox_overlap(res1["bbox"], res2["bbox"]) > 0.5:
                    # Overlapping boxes — higher confidence wala rakho
                    if res2["confidence"] > best["confidence"]:
                        best = res2
                    used.add(j)

            merged.append(best)

        return merged

    def _bbox_overlap(self, bbox1: list, bbox2: list) -> float:
        """
        Do bounding boxes ka overlap ratio calculate karta hai.
        IoU (Intersection over Union) jaisa concept.

        Returns: 0.0 (no overlap) to 1.0 (complete overlap)
        """
        try:
            # Bounding box ko (x_min, y_min, x_max, y_max) mein convert karo
            x1_min = min(p[0] for p in bbox1)
            y1_min = min(p[1] for p in bbox1)
            x1_max = max(p[0] for p in bbox1)
            y1_max = max(p[1] for p in bbox1)

            x2_min = min(p[0] for p in bbox2)
            y2_min = min(p[1] for p in bbox2)
            x2_max = max(p[0] for p in bbox2)
            y2_max = max(p[1] for p in bbox2)

            # Intersection area
            inter_x = max(0, min(x1_max, x2_max) - max(x1_min, x2_min))
            inter_y = max(0, min(y1_max, y2_max) - max(y1_min, y2_min))
            intersection = inter_x * inter_y

            # Union area
            area1 = (x1_max - x1_min) * (y1_max - y1_min)
            area2 = (x2_max - x2_min) * (y2_max - y2_min)
            union = area1 + area2 - intersection

            if union == 0:
                return 0.0

            return intersection / union

        except Exception:
            return 0.0

    def extract_from_multiple_images(
        self,
        images: List[np.ndarray],
        languages: List[str] = None
    ) -> Dict:
        """
        Multiple images (e.g., PDF pages) se text extract karta hai.
        Saare pages ka text combine karta hai.

        Args:
            images: List of OpenCV images
            languages: Languages to use

        Returns:
            Combined OCR result (same format as extract_text)
        """
        all_lines = []
        total_confidence = 0.0
        lang_counts = {}

        for i, image in enumerate(images):
            logger.info(f"📄 Processing page {i + 1}/{len(images)}...")
            result = self.extract_text(image, languages)

            for line in result["lines"]:
                # Page number tag karo
                line["page"] = i + 1
                all_lines.append(line)

            total_confidence += result["avg_confidence"]
            lang = result["detected_language"]
            lang_counts[lang] = lang_counts.get(lang, 0) + 1

        raw_text = "\n".join([line["text"] for line in all_lines])
        avg_confidence = total_confidence / len(images) if images else 0.0
        detected_lang = max(lang_counts, key=lang_counts.get) if lang_counts else "en"

        return {
            "raw_text": raw_text,
            "lines": all_lines,
            "avg_confidence": round(avg_confidence, 3),
            "detected_language": detected_lang,
            "page_count": len(images),
        }
