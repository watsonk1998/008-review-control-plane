import sys, json
from pathlib import Path
repo_root = Path('/Users/lucas/repos/review/008-review-control-plane')
sys.path.insert(0, str(repo_root / 'apps' / 'api'))
from src.main_dependencies import get_store
store = get_store()
tasks = store.list_tasks()
task = tasks[-1]
# Print out keys of task.result
print("Result keys:", task.result.keys() if task.result else "No result")
if task.result and 'metrics' in task.result:
    print("Metrics:", task.result['metrics'])
if task.result and 'dual_review_enabled' in task.result:
    print("Dual Review Enabled:", task.result['dual_review_enabled'])
