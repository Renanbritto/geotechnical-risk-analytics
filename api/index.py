import sys
import os

# Add the project root to the python path so the `src` module can be imported
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.api.server import app
