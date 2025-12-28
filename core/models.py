"""
Data models for Invoice Merge Assistant
"""
from dataclasses import dataclass, field
from typing import Literal, Optional, Tuple
from PIL import Image
import fitz


CropMode = Literal["auto", "top", "manual"]


@dataclass
class InvoiceItem:
    """Represents a single invoice PDF file"""
    path: str
    page_index: int = 0
    crop_mode: CropMode = "auto"
    manual_norm: Optional[Tuple[float, float, float, float]] = None
    cached_auto_rect: Optional[fitz.Rect] = None
    cached_thumb: Optional[Image.Image] = None

    def __post_init__(self):
        """Validate the invoice item"""
        if self.page_index < 0:
            raise ValueError("page_index must be non-negative")
        if self.manual_norm is not None:
            x0, y0, x1, y1 = self.manual_norm
            if not (0 <= x0 < x1 <= 1 and 0 <= y0 < y1 <= 1):
                raise ValueError("manual_norm must be normalized coordinates in [0,1]")


@dataclass
class CropConfig:
    """Configuration for cropping behavior"""
    top_half_ratio: float = 0.55
    auto_margin: float = 10.0
    pixel_threshold: int = 245
    pixel_zoom: float = 1.5

    def __post_init__(self):
        """Validate crop configuration"""
        if not 0 < self.top_half_ratio <= 1:
            raise ValueError("top_half_ratio must be in (0, 1]")
        if self.auto_margin < 0:
            raise ValueError("auto_margin must be non-negative")
        if not 0 <= self.pixel_threshold <= 255:
            raise ValueError("pixel_threshold must be in [0, 255]")
        if self.pixel_zoom <= 0:
            raise ValueError("pixel_zoom must be positive")


@dataclass
class LayoutConfig:
    """Configuration for grid layout"""
    rows: int = 2
    cols: int = 2
    a4_orientation: Literal["portrait", "landscape"] = "portrait"
    margin: float = 20.0
    gap: float = 10.0

    def __post_init__(self):
        """Validate layout configuration"""
        if self.rows <= 0 or self.cols <= 0:
            raise ValueError("rows and cols must be positive")
        if self.margin < 0 or self.gap < 0:
            raise ValueError("margin and gap must be non-negative")

    @property
    def page_size(self) -> Tuple[float, float]:
        """Get page size in points (A4: 595.27 x 841.89 pt)"""
        a4_width, a4_height = 595.27, 841.89
        if self.a4_orientation == "portrait":
            return (a4_width, a4_height)
        else:
            return (a4_height, a4_width)


@dataclass
class ExportProgress:
    """Progress information for export task"""
    current: int = 0
    total: int = 0
    current_file: str = ""

    @property
    def percentage(self) -> float:
        """Get progress percentage"""
        if self.total == 0:
            return 0.0
        return (self.current / self.total) * 100.0
