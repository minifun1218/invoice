"""
PDF engine wrapper using PyMuPDF (fitz)
"""
import fitz
from PIL import Image
from typing import Optional, Tuple
from pathlib import Path


class PDFEngine:
    """Wrapper for PDF operations using PyMuPDF"""

    @staticmethod
    def open_document(path: str) -> Optional[fitz.Document]:
        """
        Open a PDF document

        Args:
            path: Path to PDF file

        Returns:
            fitz.Document or None if failed
        """
        try:
            doc = fitz.open(path)
            if doc.is_encrypted:
                raise ValueError(f"PDF is encrypted: {path}")
            return doc
        except Exception as e:
            raise ValueError(f"Failed to open PDF {path}: {str(e)}")

    @staticmethod
    def get_page_count(doc: fitz.Document) -> int:
        """Get number of pages in document"""
        return len(doc)

    @staticmethod
    def get_page(doc: fitz.Document, page_index: int) -> fitz.Page:
        """Get a specific page from document"""
        if page_index < 0 or page_index >= len(doc):
            raise ValueError(f"Invalid page index: {page_index}")
        return doc[page_index]

    @staticmethod
    def render_thumbnail(page: fitz.Page, max_width: int, max_height: int) -> Image.Image:
        """
        Render page as thumbnail image

        Args:
            page: PDF page
            max_width: Maximum width in pixels
            max_height: Maximum height in pixels

        Returns:
            PIL Image
        """
        page_rect = page.rect
        scale_x = max_width / page_rect.width
        scale_y = max_height / page_rect.height
        scale = min(scale_x, scale_y)

        mat = fitz.Matrix(scale, scale)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        return img

    @staticmethod
    def get_text_blocks(page: fitz.Page) -> list:
        """Get all text blocks from page"""
        return page.get_text("blocks")

    @staticmethod
    def get_drawings(page: fitz.Page) -> list:
        """Get all drawing objects from page"""
        return page.get_drawings()

    @staticmethod
    def get_images(page: fitz.Page) -> list:
        """Get all images from page"""
        return page.get_images(full=True)

    @staticmethod
    def get_image_bbox(page: fitz.Page, xref: int) -> fitz.Rect:
        """Get bounding box of an image by xref"""
        return page.get_image_bbox(xref)

    @staticmethod
    def create_output_document() -> fitz.Document:
        """Create a new empty PDF document"""
        return fitz.open()

    @staticmethod
    def add_page(doc: fitz.Document, width: float, height: float) -> fitz.Page:
        """Add a new page to document"""
        return doc.new_page(width=width, height=height)

    @staticmethod
    def show_pdf_page(
        dest_page: fitz.Page,
        src_doc: fitz.Document,
        src_page_index: int,
        dest_rect: fitz.Rect,
        clip: Optional[fitz.Rect] = None
    ):
        """
        Insert source page content into destination page

        Args:
            dest_page: Destination page
            src_doc: Source document
            src_page_index: Source page index
            dest_rect: Destination rectangle
            clip: Optional clipping rectangle in source page coordinates
        """
        dest_page.show_pdf_page(dest_rect, src_doc, src_page_index, clip=clip)
