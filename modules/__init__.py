"""
SPID-Xploit v2.0 - Modules Package (CORRECTED)
Italian SPID Penetration Testing Framework
"""

__version__ = "2.0.0"
__author__ = "Security Research Team"
__license__ = "For authorized security testing only"

import sys
import os

modules_dir = os.path.dirname(os.path.abspath(__file__))
if modules_dir not in sys.path:
    sys.path.insert(0, modules_dir)
