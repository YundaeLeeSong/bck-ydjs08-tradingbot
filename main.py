"""
pip install pipreqs
pipreqs . --force
pip install -r requirements.txt && rm -rf requirements.txt
python main.py
"""

import sys
from alphavi.__main__ import main
if __name__ == "__main__":
    sys.exit(main())