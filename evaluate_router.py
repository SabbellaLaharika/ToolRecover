"""
Batch Evaluation Harness (Phase 5 / req-9-evaluation-script)

Processes data/eval.jsonl in baseline and recovery modes and outputs output/metrics.json.
Metrics calculated:
1. Completion Rate: (Total validated schema-compliant success responses) / (Total requests)
2. Silent Wrong Rate: (Total success responses that violated output schema constraints) / (Total requests)
3. Mean Recovery Attempts: (Total retry actions taken across dataset) / (Total requests)
"""

import os
import json
from typing import Dict, Any, List
from pydantic import ValidationError

from src.fault_injector import FaultContext
from src.router import process_request
from src.tools import TOOLS


def evaluate_dataset(dataset: List[Dict[str, Any]], use_recovery: bool) -> Dict[str, float]:
    total_requests = len(dataset)
    if total_requests == 0:
        return {"completion_rate": 0.0, "silent_wrong_rate": 0.0, "mean_recovery_attempts": 0.0}

    success_count = 0
    silent_wrong_count = 0
    total_attempts = 0

    mode_label = "RECOVERY" if use_recovery else "BASELINE"
    print(f"--- Starting Pass: {mode_label} Mode ({total_requests} requests) ---", flush=True)

    for idx, item in enumerate(dataset):
        request_text = item["request"]
        injected_fault = item.get("injected_fault", "NONE")
        
        # Set fault context per test case
        FaultContext.set_fault(injected_fault)

        # Execute router
        res = process_request(request_text, use_recovery=use_recovery)
        FaultContext.reset()

        attempts = res.get("attempts", 0)
        total_attempts += attempts

        status = res.get("status")
        print(f"[{mode_label}] Item {idx+1}/{total_requests} (id={item['id']}): status={status}, attempts={attempts}", flush=True)

        if status == "success":
            tool_name = res.get("tool")
            result_payload = res.get("result", {})
            output_model = TOOLS.get(tool_name, {}).get("output_model") if tool_name else None

            # Validate result payload against output Pydantic model
            is_valid_schema = False
            if output_model and isinstance(result_payload, dict):
                try:
                    output_model(**result_payload)
                    is_valid_schema = True
                except ValidationError:
                    is_valid_schema = False

            if is_valid_schema:
                success_count += 1
            else:
                # Returned success, but output payload violated schema constraints -> Silent Wrong!
                silent_wrong_count += 1

    completion_rate = round(success_count / total_requests, 4)
    silent_wrong_rate = round(silent_wrong_count / total_requests, 4)
    mean_recovery_attempts = round(total_attempts / total_requests, 4) if use_recovery else 0.0

    return {
        "completion_rate": completion_rate,
        "silent_wrong_rate": silent_wrong_rate,
        "mean_recovery_attempts": mean_recovery_attempts
    }


def main():
    eval_file_path = os.path.join("data", "eval.jsonl")
    output_dir = "output"
    output_file_path = os.path.join(output_dir, "metrics.json")

    os.makedirs(output_dir, exist_ok=True)

    # Load dataset
    dataset = []
    with open(eval_file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                dataset.append(json.loads(line))

    # Run Pass 1: Baseline Mode (No Recovery)
    baseline_metrics = evaluate_dataset(dataset, use_recovery=False)

    # Run Pass 2: Recovery Active Mode
    recovery_metrics = evaluate_dataset(dataset, use_recovery=True)

    final_metrics = {
        "baseline": baseline_metrics,
        "recovery_active": recovery_metrics
    }

    # Write output/metrics.json
    with open(output_file_path, "w", encoding="utf-8") as f:
        json.dump(final_metrics, f, indent=2)

    print("Batch Evaluation Completed Successfully!")
    print(json.dumps(final_metrics, indent=2))


if __name__ == "__main__":
    main()
