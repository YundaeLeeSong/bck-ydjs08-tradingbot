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


def get_env_arr(env_var: str) -> list[str]:
    """
    Retrieves an environment variable and parses it into a list of strings,
    splitting by common delimiters (e.g., ';', ':', ',').

    Args:
        env_var (str): The name of the environment variable to retrieve.

    Returns:
        list[str]: A list of parsed string values, or an empty list if not found.
    """
    import re
    val = get_env_var(env_var)
    if not val:
        return []
    
    # Split by ;, :, or , and filter out empty strings
    parts = re.split(r'[;:,]+', val)
    return [p.strip() for p in parts if p.strip()]


def get_resource(file_name: str) -> Optional[Path]:
    """
    Locates a resource file (e.g., .html template) considering standard execution
    and PyInstaller temporary directories. Default assumes files are in 'resource' 
    or 'resources' folders unless the user passed a path with directories.

    Args:
        file_name (str): The name or relative path of the file to locate.

    Returns:
        Optional[Path]: The absolute path to the resource, or None if not found.
    """
    if not file_name or not isinstance(file_name, str):
        return None

    file_path = Path(file_name)
    if len(file_path.parts) > 1:
        candidates = [file_path]
    else:
        candidates = [
            Path("resource") / file_name,
            Path("resources") / file_name,
            Path(file_name)
        ]

    for candidate in candidates:
        # 1. PyInstaller _MEIPASS
        try:
            meipass_path = Path(sys._MEIPASS) / candidate
            if meipass_path.exists():
                return meipass_path.resolve()
        except AttributeError:
            pass

        # 2. Execution directory
        cwd_path = Path.cwd() / candidate
        if cwd_path.exists():
            return cwd_path.resolve()

        # 3. Fallback to trying relative to the calling script's location
        # (Assuming the caller is a few frames up)
        try:
            import inspect
            caller_frame = inspect.stack()[1]
            caller_path = Path(caller_frame.filename).parent / candidate
            if caller_path.exists():
                return caller_path.resolve()
        except Exception:
            pass

    return None

