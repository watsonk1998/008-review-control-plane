import sys, json
from pathlib import Path
repo_root = Path('/Users/lucas/repos/review/008-review-control-plane')
sys.path.insert(0, str(repo_root / 'apps' / 'api'))
from src.main_dependencies import get_store
store = get_store()
tasks = store.list_tasks()
task = tasks[-1]
# Print out ALL keys exactly.
print("Result keys:", list(task.result.keys()))
if 'hermesController' in task.result:
    hc = task.result['hermesController']
    print("-- hermesController details --")
    print(hc)
else:
    print("-- NO hermesController KEY EXISTS IN task.result --")
