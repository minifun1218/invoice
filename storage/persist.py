"""
Persistence layer for saving and loading crop configurations
"""
import json
from pathlib import Path
from typing import Dict, Optional
from core.models import InvoiceItem


class ConfigPersistence:
    """Handles saving and loading crop configurations"""

    @staticmethod
    def get_config_path(pdf_path: str) -> Path:
        """Get sidecar JSON path for a PDF file"""
        pdf_file = Path(pdf_path)
        return pdf_file.parent / f"{pdf_file.stem}_crop_config.json"

    @staticmethod
    def save_config(item: InvoiceItem) -> bool:
        """
        Save crop configuration for an invoice item

        Args:
            item: Invoice item to save

        Returns:
            True if saved successfully
        """
        try:
            config_path = ConfigPersistence.get_config_path(item.path)
            config_data = {
                "crop_mode": item.crop_mode,
                "manual_norm": item.manual_norm,
                "page_index": item.page_index
            }
            with open(config_path, 'w') as f:
                json.dump(config_data, f, indent=2)
            return True
        except Exception:
            return False

    @staticmethod
    def load_config(pdf_path: str) -> Optional[Dict]:
        """
        Load crop configuration for a PDF file

        Args:
            pdf_path: Path to PDF file

        Returns:
            Configuration dict or None if not found
        """
        try:
            config_path = ConfigPersistence.get_config_path(pdf_path)
            if not config_path.exists():
                return None
            with open(config_path, 'r') as f:
                return json.load(f)
        except Exception:
            return None
