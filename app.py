"""
Stock Analysis & Regression Tool Wrapper
========================================
A lightweight entry point that serves as the executable wrapper for PyInstaller 
or standard script execution. Delegates execution to the core module.
"""
from core.__main__ import main

if __name__ == "__main__":
    main()