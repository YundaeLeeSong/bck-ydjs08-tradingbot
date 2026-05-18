"""
uvx pipreqs . --force
uv add -r requirements.txt
rm requirements.txt

uv build
uv run main.py
"""

import sys
from alphavi.__main__ import main
if __name__ == "__main__":
    main()
    # sys.exit(main())