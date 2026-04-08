"""
Utility module for environment variable retrieval.

Provides functions to locate and load environment variables safely from
multiple sources, prioritizing the system OS environment and falling back
to `.env` files located relative to execution paths or calling scripts.
"""

import os
import sys
from pathlib import Path
from typing import Optional

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

def get_env_var(env_var: str) -> Optional[str]:
    """
    Looks up an environment variable from multiple locations.

    Priority:
    1. OS environment
    2. .env (relative to PyInstaller _MEIPASS)
    3. .env (relative to execution directory)
    
    Args:
        env_var (str): The name of the environment variable to retrieve.

    Returns:
        Optional[str]: The value of the environment variable, or None if not found.
    """
    # Validate input
    if not env_var or not isinstance(env_var, str):
        return None

    # 1. os environment
    val = os.getenv(env_var)
    if val:
        return val

    if load_dotenv:
        # 2. PyInstaller creates a temp folder and stores path in _MEIPASS
        try:
            meipass_env = Path(sys._MEIPASS) / ".env"
            if meipass_env.exists():
                load_dotenv(dotenv_path=meipass_env)
                val = os.getenv(env_var)
                if val:
                    return val
        except AttributeError:
            pass

        # 3. Standard Python environment (execution directory)
        cwd_env = Path.cwd() / ".env"
        if cwd_env.exists():
            load_dotenv(dotenv_path=cwd_env)
            val = os.getenv(env_var)
            if val:
                return val

    return os.getenv(env_var)
