import sys, json
from pathlib import Path
repo_root = Path('/Users/lucas/repos/review/008-review-control-plane')
sys.path.insert(0, str(repo_root / 'apps' / 'api'))
from src.main_dependencies import get_store
store = get_store()
with open('/Users/lucas/repos/review/008-review-control-plane/apps/api/.data/tasks.json', 'r') as f:
    data = json.load(f)
    print("Task result issues count:", len(data[-1]['result']['issues']))
    print("Is hermes packet saved?", 'hermes_packet' in data[-1]['result'] or 'hermes' in str(data[-1]))
