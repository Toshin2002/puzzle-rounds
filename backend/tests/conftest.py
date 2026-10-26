import sys
from pathlib import Path

# Let tests `import app` when run from the backend folder.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
