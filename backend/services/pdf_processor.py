"""
pdf_processor.py — PDF to Image Converter
Multi-page PDFs ko individual images mein convert karta hai OCR ke liye.
PyMuPDF (fitz) use karta hai — No Poppler dependency needed!
"""

import fitz  # PyMuPDF
import numpy as np
import cv2
import os
import tempfile
from typing import List, Tuple
import logging

logger = logging.getLogger(__name__)


class PDFProcessor:
    """
    PDF files ko images mein convert karta hai.
    Har page ek separate image ban jaata hai.
    High DPI rendering for better OCR accuracy.
    """

    def __init__(self, dpi: int = 300):
        """
        Args:
            dpi: Rendering resolution. 300 DPI standard print quality hai.
                 Higher = better OCR but slower processing.
        """
        self.dpi = dpi
        # DPI ko zoom factor mein convert karo (72 DPI is default)
        self.zoom = dpi / 72.0

    def pdf_to_images(self, pdf_path: str) -> List[np.ndarray]:
        """
        PDF file ko images ki list mein convert karta hai.

        Args:
            pdf_path: PDF file ka path

        Returns:
            List of numpy arrays (OpenCV images) — ek per page
        """
        images = []

        try:
            doc = fitz.open(pdf_path)
            total_pages = len(doc)
            logger.info(f"📄 PDF loaded: {total_pages} pages found")

            for page_num in range(total_pages):
                page = doc.load_page(page_num)

                # High resolution rendering ke liye zoom matrix
                mat = fitz.Matrix(self.zoom, self.zoom)
                pix = page.get_pixmap(matrix=mat)

                # Pixmap ko numpy array mein convert karo
                img_data = pix.samples
                img_array = np.frombuffer(img_data, dtype=np.uint8)

                # Reshape based on channels (RGB ya RGBA)
                if pix.alpha:
                    img_array = img_array.reshape(pix.height, pix.width, 4)
                    # RGBA to BGR (OpenCV format)
                    img_array = cv2.cvtColor(img_array, cv2.COLOR_RGBA2BGR)
                else:
                    img_array = img_array.reshape(pix.height, pix.width, 3)
                    # RGB to BGR (OpenCV format)
                    img_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)

                images.append(img_array)
                logger.info(f"  ✅ Page {page_num + 1}/{total_pages} converted ({pix.width}x{pix.height})")

            doc.close()
            return images

        except Exception as e:
            logger.error(f"❌ PDF processing failed: {e}")
            raise ValueError(f"PDF processing failed: {str(e)}")

    def pdf_bytes_to_images(self, pdf_bytes: bytes) -> List[np.ndarray]:
        """
        PDF bytes (file upload se) ko directly images mein convert karta hai.
        Disk pe save karne ki zaroorat nahi.

        Args:
            pdf_bytes: PDF file ka raw bytes data

        Returns:
            List of numpy arrays (OpenCV images)
        """
        images = []

        try:
            # Bytes se directly PDF open karo
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            total_pages = len(doc)
            logger.info(f"📄 PDF loaded from bytes: {total_pages} pages")

            for page_num in range(total_pages):
                page = doc.load_page(page_num)
                mat = fitz.Matrix(self.zoom, self.zoom)
                pix = page.get_pixmap(matrix=mat)

                img_data = pix.samples
                img_array = np.frombuffer(img_data, dtype=np.uint8)

                if pix.alpha:
                    img_array = img_array.reshape(pix.height, pix.width, 4)
                    img_array = cv2.cvtColor(img_array, cv2.COLOR_RGBA2BGR)
                else:
                    img_array = img_array.reshape(pix.height, pix.width, 3)
                    img_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)

                images.append(img_array)

            doc.close()
            return images

        except Exception as e:
            logger.error(f"❌ PDF bytes processing failed: {e}")
            raise ValueError(f"PDF processing failed: {str(e)}")

    def get_page_count(self, pdf_path: str = None, pdf_bytes: bytes = None) -> int:
        """PDF mein kitne pages hain ye batata hai"""
        try:
            if pdf_bytes:
                doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            elif pdf_path:
                doc = fitz.open(pdf_path)
            else:
                return 0
            count = len(doc)
            doc.close()
            return count
        except Exception:
            return 0
