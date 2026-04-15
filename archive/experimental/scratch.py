import sys
from pathlib import Path
repo_root = Path('/Users/lucas/repos/review/008-review-control-plane')
sys.path.insert(0, str(repo_root / 'apps' / 'api'))
from src.services.document_loader import DocumentLoader
print([m for m in dir(DocumentLoader) if not m.startswith('_')])
