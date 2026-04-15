import sys, json
from pathlib import Path
repo_root = Path('/Users/lucas/repos/review/008-review-control-plane')
sys.path.insert(0, str(repo_root / 'apps' / 'api'))
from src.main_dependencies import get_store
store = get_store()
tasks = store.list_tasks()
task = tasks[-1]
# Print hermesController output dict
hc = task.result.get('hermesController')
if hc:
    print("Enabled:", hc.get('enabled'))
    print("Degraded:", hc.get('degraded'))
    print("Error:", hc.get('error'))
    print("Agent Results count:", len(hc.get('agentResults', [])))
    print("Main Review Outcomes count:", len(hc.get('mainReviewOutcomes', [])))
else:
    print("No hermesController block!")
