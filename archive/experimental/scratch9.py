import sys, json
from pathlib import Path
repo_root = Path('/Users/lucas/repos/review/008-review-control-plane')
sys.path.insert(0, str(repo_root / 'apps' / 'api'))
from src.main_dependencies import get_store
store = get_store()
tasks = store.list_tasks()
print(f"Total tasks: {len(tasks)}")
for t in tasks[-3:]:
    print(f"Task ID: {t.id}, Type: {t.taskType}")
