"""
image_preprocessor.py — OpenCV Image Preprocessing Pipeline
"Dirty" handwritten invoices ko clean karta hai OCR se pehle.
Shadow removal, binarization, deskew — sab yahan hota hai.

Pipeline Steps:
1. Grayscale conversion
2. Shadow removal (median blur + divide)
3. Noise reduction (Non-Local Means Denoising)
4. Contrast enhancement (CLAHE)
5. Adaptive thresholding (Binarization)
6. Deskew (angle correction)
"""

import cv2
import numpy as np
from typing import Tuple
import logging

logger = logging.getLogger(__name__)


class ImagePreprocessor:
    """
    Invoice image ko OCR-ready banata hai.
    Handwritten + printed dono ke liye optimized hai.
    """

    def preprocess(self, image: np.ndarray) -> np.ndarray:
        """
        Full preprocessing pipeline — ek image input, cleaned image output.

        Args:
            image: OpenCV image (BGR format, jaise cv2.imread se aata hai)

        Returns:
            Preprocessed image ready for OCR
        """
        try:
            # Step 1: Grayscale mein convert karo
            gray = self._to_grayscale(image)

            # Step 2: Shadows hatao (important for phone camera captures)
            no_shadow = self._remove_shadows(gray)

            # Step 3: Noise reduce karo (handwriting ke liye zaroori)
            denoised = self._denoise(no_shadow)

            # Step 4: Contrast badhaao (faded ink ke liye)
            enhanced = self._enhance_contrast(denoised)

            # Step 5: Binarize karo (black text on white background)
            binary = self._adaptive_threshold(enhanced)

            # Step 6: Deskew — tedhi image seedhi karo
            deskewed = self._deskew(binary)

            logger.info("✅ Image preprocessing complete!")
            return deskewed

        except Exception as e:
            logger.warning(f"⚠️ Preprocessing failed, returning grayscale: {e}")
            # Fallback: At least convert to grayscale
            return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image

    def _to_grayscale(self, image: np.ndarray) -> np.ndarray:
        """Step 1: Color image ko grayscale mein convert karo"""
        if len(image.shape) == 3:
            return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        return image

    def _remove_shadows(self, gray: np.ndarray) -> np.ndarray:
        """
        Step 2: Shadow Removal — Phone se click ki photos mein shadows aati hain.
        Technique: Median blur se background estimate karo, phir divide karo.
        Result: Even lighting across the entire image.
        """
        # Large kernel se blur karo — ye background/shadow estimate hai
        bg = cv2.medianBlur(gray, 21)

        # Original ko background se divide karo — shadows cancel ho jaati hain
        # 255 se multiply isliye ki result 0-255 range mein rahe
        no_shadow = cv2.divide(gray, bg, scale=255)

        return no_shadow

    def _denoise(self, image: np.ndarray) -> np.ndarray:
        """
        Step 3: Noise Reduction — Grainy images ko smooth karo.
        Non-Local Means Denoising use karta hai (best for text images).
        """
        # h=10: filter strength, templateWindowSize=7, searchWindowSize=21
        denoised = cv2.fastNlMeansDenoising(image, None, h=10, templateWindowSize=7, searchWindowSize=21)
        return denoised

    def _enhance_contrast(self, image: np.ndarray) -> np.ndarray:
        """
        Step 4: CLAHE (Contrast Limited Adaptive Histogram Equalization)
        Faded ink ya low contrast images ke liye useful hai.
        Regular histogram equalization se better hai kyunki
        ye locally adapt hota hai (tile-based).
        """
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(image)
        return enhanced

    def _adaptive_threshold(self, image: np.ndarray) -> np.ndarray:
        """
        Step 5: Adaptive Thresholding — Binary image banata hai.
        Adaptive isliye kyunki uneven lighting handle karta hai.
        Gaussian method smooth results deta hai.
        """
        binary = cv2.adaptiveThreshold(
            image,
            255,                                # Maximum value (white)
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,     # Gaussian weighted sum
            cv2.THRESH_BINARY,                  # Binary output
            11,                                 # Block size (neighborhood size)
            2                                   # Constant subtracted from mean
        )
        return binary

    def _deskew(self, image: np.ndarray) -> np.ndarray:
        """
        Step 6: Deskew — Tedhi (rotated) image ko seedha karta hai.
        Hough Line Transform se dominant angle detect karta hai.
        ±45° tak correction karta hai.
        """
        # Edges detect karo
        edges = cv2.Canny(image, 50, 150, apertureSize=3)

        # Hough Transform se lines dhundho
        lines = cv2.HoughLinesP(
            edges, 1, np.pi / 180,
            threshold=100,
            minLineLength=100,
            maxLineGap=10
        )

        if lines is None or len(lines) == 0:
            return image  # Koi lines nahi mili, deskew skip karo

        # Saari lines ke angles calculate karo
        angles = []
        for line in lines:
            x1, y1, x2, y2 = line[0]
            angle = np.degrees(np.arctan2(y2 - y1, x2 - x1))
            # Sirf near-horizontal lines consider karo (text lines)
            if abs(angle) < 45:
                angles.append(angle)

        if not angles:
            return image

        # Median angle lo (outliers se bachne ke liye)
        median_angle = np.median(angles)

        # Agar angle bahut chhota hai toh skip karo (already straight)
        if abs(median_angle) < 0.5:
            return image

        # Image rotate karo
        (h, w) = image.shape[:2]
        center = (w // 2, h // 2)
        rotation_matrix = cv2.getRotationMatrix2D(center, median_angle, 1.0)
        rotated = cv2.warpAffine(
            image, rotation_matrix, (w, h),
            flags=cv2.INTER_CUBIC,
            borderMode=cv2.BORDER_REPLICATE  # Edges fill with nearest pixel
        )

        logger.info(f"🔄 Image deskewed by {median_angle:.1f}°")
        return rotated

    def resize_for_ocr(self, image: np.ndarray, max_size: int = 2000) -> np.ndarray:
        """
        OCR ke liye image resize karo agar bahut badi hai.
        Aspect ratio maintain hota hai.
        """
        h, w = image.shape[:2]
        if max(h, w) <= max_size:
            return image

        scale = max_size / max(h, w)
        new_w = int(w * scale)
        new_h = int(h * scale)
        resized = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)
        return resized
