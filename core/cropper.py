"""
Cropping algorithms for invoice content detection
"""
import fitz
import numpy as np
from typing import Optional
from .models import CropConfig, InvoiceItem
from .pdf_engine import PDFEngine


class Cropper:
    """Handles automatic and manual cropping of invoice PDFs"""

    def __init__(self, config: CropConfig = None):
        """Initialize cropper with configuration"""
        self.config = config or CropConfig()
        self.engine = PDFEngine()

    def compute_crop_rect(
        self,
        doc: fitz.Document,
        page_index: int,
        item: InvoiceItem
    ) -> fitz.Rect:
        """
        Compute crop rectangle based on item's crop mode

        Args:
            doc: PDF document
            page_index: Page index
            item: Invoice item with crop settings

        Returns:
            Crop rectangle in page coordinates
        """
        page = self.engine.get_page(doc, page_index)

        if item.crop_mode == "manual" and item.manual_norm:
            return self._manual_crop(page, item.manual_norm)
        elif item.crop_mode == "top":
            return self._top_half_crop(page)
        else:  # auto
            return self._auto_crop(page)

    def _manual_crop(self, page: fitz.Page, norm_coords: tuple) -> fitz.Rect:
        """Convert normalized coordinates to page rect"""
        x0, y0, x1, y1 = norm_coords
        page_rect = page.rect
        rect = fitz.Rect(
            x0 * page_rect.width,
            y0 * page_rect.height,
            x1 * page_rect.width,
            y1 * page_rect.height
        )
        return rect & page_rect  # Clamp to page bounds

    def _top_half_crop(self, page: fitz.Page) -> fitz.Rect:
        """Crop to top half of page"""
        page_rect = page.rect
        return fitz.Rect(
            0,
            0,
            page_rect.width,
            page_rect.height * self.config.top_half_ratio
        )

    def _auto_crop(self, page: fitz.Page) -> fitz.Rect:
        """Automatically detect content boundaries"""
        # Try object-based detection first
        rect = self._detect_object_bounds(page)

        # If failed, try pixel-based detection
        if rect.is_empty or rect.get_area() < 100:
            rect = self._detect_pixel_bounds(page)

        # If still failed, return full page
        if rect.is_empty:
            return page.rect

        # Add margin and clamp to page
        rect = self._expand_rect(rect, self.config.auto_margin)
        return rect & page.rect

    def _detect_object_bounds(self, page: fitz.Page) -> fitz.Rect:
        """Detect content bounds using PDF objects (text, drawings, images)"""
        rects = []

        # Collect text blocks
        try:
            blocks = self.engine.get_text_blocks(page)
            for block in blocks:
                if len(block) >= 4:
                    rects.append(fitz.Rect(block[:4]))
        except Exception:
            pass

        # Collect drawings
        try:
            drawings = self.engine.get_drawings(page)
            for drawing in drawings:
                if "rect" in drawing:
                    rects.append(drawing["rect"])
        except Exception:
            pass

        # Collect images
        try:
            images = self.engine.get_images(page)
            for img in images:
                xref = img[0]
                bbox = self.engine.get_image_bbox(page, xref)
                if not bbox.is_empty:
                    rects.append(bbox)
        except Exception:
            pass

        # Union all rects
        if not rects:
            return fitz.Rect()

        result = rects[0]
        for rect in rects[1:]:
            result |= rect
        return result

    def _detect_pixel_bounds(self, page: fitz.Page) -> fitz.Rect:
        """Detect content bounds using pixel analysis (for scanned PDFs)"""
        try:
            # Render page at moderate resolution
            mat = fitz.Matrix(self.config.pixel_zoom, self.config.pixel_zoom)
            pix = page.get_pixmap(matrix=mat, alpha=False)

            # Convert to numpy array and grayscale
            img_array = np.frombuffer(pix.samples, dtype=np.uint8)
            img_array = img_array.reshape(pix.height, pix.width, 3)
            gray = np.mean(img_array, axis=2).astype(np.uint8)

            # Threshold to find content
            mask = gray < self.config.pixel_threshold
            if not mask.any():
                return fitz.Rect()

            # Find bounding box of content
            rows = np.any(mask, axis=1)
            cols = np.any(mask, axis=0)
            y_min, y_max = np.where(rows)[0][[0, -1]]
            x_min, x_max = np.where(cols)[0][[0, -1]]

            # Convert back to page coordinates
            zoom = self.config.pixel_zoom
            rect = fitz.Rect(
                x_min / zoom,
                y_min / zoom,
                (x_max + 1) / zoom,
                (y_max + 1) / zoom
            )
            return rect

        except Exception:
            return fitz.Rect()

    def _expand_rect(self, rect: fitz.Rect, margin: float) -> fitz.Rect:
        """Expand rectangle by margin on all sides"""
        return fitz.Rect(
            rect.x0 - margin,
            rect.y0 - margin,
            rect.x1 + margin,
            rect.y1 + margin
        )
