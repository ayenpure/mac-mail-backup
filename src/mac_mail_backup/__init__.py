"""
Mac Mail Backup - Export Apple Mail accounts to portable formats.

A command-line tool for backing up email accounts from Apple Mail on macOS.
Automatically discovers accounts and exports to both native and mbox formats.

Created with assistance from Claude (Anthropic).
"""

__version__ = "1.0.0"
__author__ = "Abhishek Yenpure"

from .backup import MacMailBackup
from .converter import MboxConverter

__all__ = ["MacMailBackup", "MboxConverter", "__version__"]
