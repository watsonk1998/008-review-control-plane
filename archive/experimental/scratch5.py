import sys, json
from pathlib import Path
repo_root = Path('/Users/lucas/repos/review/008-review-control-plane')
sys.path.insert(0, str(repo_root / 'apps' / 'api'))
from src.main_dependencies import get_store
store = get_store()
tasks = store.list_tasks()
task = tasks[-1]
# Print first lines of finalReportMarkdown
final_md = task.result.get('finalReportMarkdown')
if final_md:
    print("Found finalReportMarkdown!")
    print(final_md[:500])
else:
    print("finalReportMarkdown not found!")
