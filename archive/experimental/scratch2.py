import sys, json
from pathlib import Path
repo_root = Path('/Users/lucas/repos/review/008-review-control-plane')
sys.path.insert(0, str(repo_root / 'apps' / 'api'))
from src.main_dependencies import get_store
store = get_store()
tasks = store.list_tasks()
task = tasks[-1]
print("Task ID:", task.id)
if task.result and 'packets' in task.result:
    for engine, pack in task.result['packets'].items():
        print(f"Engine: {engine}")
        if isinstance(pack, dict):
            print("  Degraded:", pack.get('degraded'))
            print("  Error:", pack.get('error'))
            findings = pack.get('findings', [])
            print(f"  Findings count: {len(findings)}")
            if findings:
                print("  Sample Finding:", findings[0].get('title'))
        else:
            print("  Pack is not a dict:", type(pack))
