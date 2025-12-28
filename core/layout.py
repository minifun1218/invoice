"""
Grid layout calculator for invoice merging
"""
import fitz
from typing import Tuple, List
from .models import LayoutConfig


class LayoutCalculator:
    """Calculates grid layout for merging invoices"""

    def __init__(self, config: LayoutConfig):
        """Initialize with layout configuration"""
        self.config = config

    def get_cell_size(self) -> Tuple[float, float]:
        """
        Calculate cell size based on grid configuration

        Returns:
            (cell_width, cell_height) in points
        """
        page_w, page_h = self.config.page_size
        margin = self.config.margin
        gap = self.config.gap
        rows = self.config.rows
        cols = self.config.cols

        cell_w = (page_w - 2 * margin - (cols - 1) * gap) / cols
        cell_h = (page_h - 2 * margin - (rows - 1) * gap) / rows

        return (cell_w, cell_h)

    def calculate_scale(self, src_rect: fitz.Rect) -> float:
        """
        Calculate scale factor to fit source rect into cell

        Args:
            src_rect: Source rectangle to fit

        Returns:
            Scale factor
        """
        cell_w, cell_h = self.get_cell_size()
        src_w = src_rect.width
        src_h = src_rect.height

        if src_w <= 0 or src_h <= 0:
            return 1.0

        scale = min(cell_w / src_w, cell_h / src_h)
        return scale

    def get_cell_position(self, index: int) -> Tuple[int, int]:
        """
        Get row and column for a given index

        Args:
            index: Item index (0-based)

        Returns:
            (row, col) tuple
        """
        row = (index // self.config.cols) % self.config.rows
        col = index % self.config.cols
        return (row, col)

    def calculate_dest_rect(self, src_rect: fitz.Rect, index: int) -> fitz.Rect:
        """
        Calculate destination rectangle for placing source content

        Args:
            src_rect: Source rectangle
            index: Item index in grid

        Returns:
            Destination rectangle on output page
        """
        row, col = self.get_cell_position(index)
        cell_w, cell_h = self.get_cell_size()
        scale = self.calculate_scale(src_rect)

        # Calculate scaled dimensions
        scaled_w = src_rect.width * scale
        scaled_h = src_rect.height * scale

        # Calculate cell top-left position
        page_w, page_h = self.config.page_size
        margin = self.config.margin
        gap = self.config.gap

        cell_x = margin + col * (cell_w + gap)
        cell_y = margin + row * (cell_h + gap)

        # Center content in cell
        x0 = cell_x + (cell_w - scaled_w) / 2
        y0 = cell_y + (cell_h - scaled_h) / 2
        x1 = x0 + scaled_w
        y1 = y0 + scaled_h

        return fitz.Rect(x0, y0, x1, y1)

    def items_per_page(self) -> int:
        """Get number of items that fit on one page"""
        return self.config.rows * self.config.cols
