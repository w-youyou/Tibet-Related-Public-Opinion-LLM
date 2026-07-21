import sys
import os

# Ensure backend/ is on the Python path so tests can import from chunker_api
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
