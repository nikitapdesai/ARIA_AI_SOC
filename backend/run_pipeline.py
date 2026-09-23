"""
File location in project: run_pipeline.py
    python run_pipeline.py
"""

import subprocess
import sys
import time


STEPS = [
    ("Simulating alert stream from Detection Agent",
     [sys.executable, "utils/alert_simulator.py"]),
    ("Running Correlation Agent (RAG + kill-chain grouping)",
     [sys.executable, "agents/correlation_agent.py"]),
    ("Running Priority-Explainer Agent (scoring + SHAP)",
     [sys.executable, "agents/priority_explainer_agent.py"]),
    ("Running Escalation Agent (incident logging + KB growth)",
     [sys.executable, "agents/escalation_agent.py"]),
    ("Evaluating Correlation Agent against ground truth",
     [sys.executable, "agents/evaluate_correlation_agent.py"]),
]


def run_pipeline():
    print("=" * 70)
    print("ARIA -- Full Agent Pipeline Run")
    print("=" * 70)

    start_time = time.time()

    for step_num, (description, command) in enumerate(STEPS, 1):
        print(f"\n[{step_num}/{len(STEPS)}] {description}")
        print("-" * 70)

        result = subprocess.run(command)

        if result.returncode != 0:
            print(f"\n!! Step {step_num} failed (exit code {result.returncode}). Stopping pipeline.")
            sys.exit(1)

    elapsed = time.time() - start_time
    print("\n" + "=" * 70)
    print(f"Pipeline complete in {elapsed:.1f} seconds.")
    print("=" * 70)
    print("\nNext step: launch the API and frontend to view results:")
    print("    uvicorn api.main:app --reload   (terminal 1)")
    print("    cd ../frontend && npm run dev   (terminal 2)")


if __name__ == "__main__":
    run_pipeline()