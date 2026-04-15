import sys, json, asyncio
from pathlib import Path
repo_root = Path('/Users/lucas/repos/review/008-review-control-plane')
sys.path.insert(0, str(repo_root / 'apps' / 'api'))
from src.main_dependencies import get_runtime, get_store
store = get_store()
task = store.list_tasks()[-1]
print("Running task", task.id)
runtime = get_runtime()
print("Is hermes_controller initialized?", hasattr(runtime, 'hermes_controller'))
print("Is structured_review initialized?", hasattr(runtime, 'structured_review'))
