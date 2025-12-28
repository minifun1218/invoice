"""
Merge export logic for combining invoices into PDF
"""
import fitz
from typing import List, Callable
from pathlib import Path
from .models import InvoiceItem, LayoutConfig, ExportProgress
from .pdf_engine import PDFEngine
from .cropper import Cropper
from .layout import LayoutCalculator


class MergeExporter:
    """Handles merging invoices into a single PDF"""

    def __init__(self, layout_config: LayoutConfig):
        """Initialize exporter with layout configuration"""
        self.layout_config = layout_config
        self.engine = PDFEngine()
        self.cropper = Cropper()
        self.layout = LayoutCalculator(layout_config)

    def merge_to_pdf(
        self,
        items: List[InvoiceItem],
        output_path: str,
        progress_callback: Callable[[ExportProgress], None] = None,
        cancel_check: Callable[[], bool] = None
    ) -> bool:
        """
        Merge invoice items into a single PDF

        Args:
            items: List of invoice items to merge
            output_path: Output PDF path
            progress_callback: Optional callback for progress updates
            cancel_check: Optional callback to check for cancellation

        Returns:
            True if successful, False otherwise
        """
        if not items:
            return False

        try:
            output_doc = self.engine.create_output_document()
            items_per_page = self.layout.items_per_page()
            page_width, page_height = self.layout_config.page_size

            current_page = None
            opened_docs = {}

            for idx, item in enumerate(items):
                # Check for cancellation
                if cancel_check and cancel_check():
                    return False

                # Report progress
                if progress_callback:
                    progress = ExportProgress(
                        current=idx + 1,
                        total=len(items),
                        current_file=Path(item.path).name
                    )
                    progress_callback(progress)

                # Create new page if needed
                if idx % items_per_page == 0:
                    current_page = self.engine.add_page(output_doc, page_width, page_height)

                # Open source document (cache it)
                if item.path not in opened_docs:
                    try:
                        opened_docs[item.path] = self.engine.open_document(item.path)
                    except Exception:
                        continue

                src_doc = opened_docs[item.path]

                # Compute crop rectangle
                try:
                    crop_rect = self.cropper.compute_crop_rect(src_doc, item.page_index, item)
                except Exception:
                    continue

                # Calculate destination rectangle
                cell_index = idx % items_per_page
                dest_rect = self.layout.calculate_dest_rect(crop_rect, cell_index)

                # Place content on page
                try:
                    self.engine.show_pdf_page(
                        current_page,
                        src_doc,
                        item.page_index,
                        dest_rect,
                        clip=crop_rect
                    )
                except Exception:
                    continue

            # Save output document
            output_doc.save(output_path)
            output_doc.close()

            # Close all opened documents
            for doc in opened_docs.values():
                doc.close()

            return True

        except Exception:
            return False

    def generate_preview_page(self, items: List[InvoiceItem], max_items: int = None) -> fitz.Document:
        """
        Generate a preview of the first merged page

        Args:
            items: List of invoice items to merge
            max_items: Maximum number of items to preview (default: one page worth)

        Returns:
            fitz.Document with preview page, or None if failed
        """
        if not items:
            return None

        try:
            items_per_page = self.layout.items_per_page()
            if max_items is None:
                max_items = items_per_page

            preview_items = items[:min(max_items, len(items))]

            output_doc = self.engine.create_output_document()
            page_width, page_height = self.layout_config.page_size
            current_page = self.engine.add_page(output_doc, page_width, page_height)

            opened_docs = {}

            for idx, item in enumerate(preview_items):
                # Open source document
                if item.path not in opened_docs:
                    try:
                        opened_docs[item.path] = self.engine.open_document(item.path)
                    except Exception:
                        continue

                src_doc = opened_docs[item.path]

                # Compute crop rectangle
                try:
                    crop_rect = self.cropper.compute_crop_rect(src_doc, item.page_index, item)
                except Exception:
                    continue

                # Calculate destination rectangle
                dest_rect = self.layout.calculate_dest_rect(crop_rect, idx)

                # Place content on page
                try:
                    self.engine.show_pdf_page(
                        current_page,
                        src_doc,
                        item.page_index,
                        dest_rect,
                        clip=crop_rect
                    )
                except Exception:
                    continue

            # Close all opened documents
            for doc in opened_docs.values():
                doc.close()

            return output_doc

        except Exception:
            return None
