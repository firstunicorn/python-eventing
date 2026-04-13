"""Enforce tiered coverage thresholds on critical code paths.

Validates that critical infrastructure (identified via Serena MCP analysis)
meets 85% coverage minimum while overall project maintains 80%.

Based on 2026 best practices: risk-based thresholds, not blanket percentages.
"""

import json
import sys
from pathlib import Path


# Critical paths identified via Serena MCP analysis
# These require 85% coverage minimum (high risk, business-critical)
CRITICAL_PATHS = {
    # Core business logic & resilience
    "src/messaging/core/contracts/circuit_breaker.py": 85,
    "src/messaging/core/contracts/bus/": 85,
    "src/messaging/core/contracts/dispatcher_setup.py": 85,
    
    # Infrastructure: message processing & idempotency
    "src/messaging/main/_initialization.py": 85,
    "src/messaging/infrastructure/persistence/processed_message_store/": 85,
    "src/messaging/infrastructure/outbox/outbox_repository.py": 85,
    "src/messaging/infrastructure/outbox/outbox_crud/": 85,
    
    # Pub/sub bridge & publishers
    "src/messaging/infrastructure/pubsub/bridge/": 85,
    "src/messaging/infrastructure/pubsub/kafka_publisher.py": 85,
    "src/messaging/infrastructure/pubsub/rabbit/publisher.py": 85,
    
    # Resilience middleware
    "src/messaging/infrastructure/resilience/": 85,
}


def get_coverage_data() -> dict:
    """Load coverage JSON report."""
    coverage_file = Path(".coverage")
    if not coverage_file.exists():
        print("ERROR: .coverage file not found. Run pytest with --cov first.")
        sys.exit(1)
    
    # Use coverage.py API to get data
    from coverage import Coverage
    
    cov = Coverage()
    cov.load()
    cov.json_report(outfile="coverage.json")
    
    with open("coverage.json", encoding="utf-8") as f:
        return json.load(f)


def calculate_path_coverage(data: dict, path_pattern: str) -> tuple[float, list[str]]:
    """Calculate coverage for files matching path pattern."""
    matching_files = []
    total_statements = 0
    covered_statements = 0
    
    for file_path, file_data in data["files"].items():
        normalized = file_path.replace("\\", "/")
        pattern_normalized = path_pattern.replace("\\", "/")
        
        if pattern_normalized.endswith("/"):
            # Directory pattern
            if normalized.startswith(pattern_normalized):
                matching_files.append(file_path)
                summary = file_data["summary"]
                total_statements += summary["num_statements"]
                covered_statements += summary["covered_lines"]
        else:
            # File pattern
            if normalized == pattern_normalized or normalized.endswith(pattern_normalized):
                matching_files.append(file_path)
                summary = file_data["summary"]
                total_statements += summary["num_statements"]
                covered_statements += summary["covered_lines"]
    
    if total_statements == 0:
        return 0.0, matching_files
    
    return (covered_statements / total_statements) * 100, matching_files


def main() -> None:
    """Check coverage thresholds for critical paths."""
    data = get_coverage_data()
    
    print("\n" + "=" * 70)
    print("TIERED COVERAGE VALIDATION")
    print("=" * 70)
    print(f"Overall project coverage: {data['totals']['percent_covered']:.2f}%")
    print(f"Overall threshold: 80% (enforced by pytest)")
    print("\n" + "-" * 70)
    print("CRITICAL PATHS (85% minimum):")
    print("-" * 70)
    
    failures = []
    
    for path, threshold in CRITICAL_PATHS.items():
        coverage_pct, files = calculate_path_coverage(data, path)
        
        if not files:
            print(f"[WARN] {path}: NO FILES FOUND")
            continue
        
        # Use ASCII status indicators instead of Unicode emoji
        status = "[PASS]" if coverage_pct >= threshold else "[FAIL]"
        print(f"{status} {path}")
        print(f"   Coverage: {coverage_pct:.2f}% (threshold: {threshold}%)")
        print(f"   Files: {len(files)}")
        
        if coverage_pct < threshold:
            failures.append((path, coverage_pct, threshold))
            for file in files:
                file_cov = data["files"][file]["summary"]["percent_covered"]
                print(f"      - {file}: {file_cov:.2f}%")
    
    print("=" * 70)
    
    if failures:
        print("\n[FAIL] CRITICAL PATH COVERAGE FAILURES:")
        for path, actual, expected in failures:
            print(f"   {path}: {actual:.2f}% < {expected}%")
        print("\nCritical infrastructure must meet 85% coverage.")
        print("Run: pytest <path> -v --cov=<path> to see missing lines")
        sys.exit(1)
    else:
        print("\n[PASS] All critical paths meet 85% coverage threshold!")
        sys.exit(0)


if __name__ == "__main__":
    main()
