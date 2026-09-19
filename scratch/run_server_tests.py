import os
import sys
import tempfile
from pathlib import Path

backend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend")
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from tests.test_long_running_server import (
    test_1_synchronous_command_execution,
    test_2_web_server_command_auto_classification,
    test_3_html_preview_start_server,
    test_4_stop_server,
    test_5_repeated_preview_server_reuse,
    test_6_bounded_startup_failure_test,
    test_7_sse_lifecycle_and_server_persistence
)

def run_all():
    print("=" * 60)
    print("RUNNING LONG-RUNNING SERVER REGRESSION TESTS")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)

        print("[RUNNING] Test 1: Synchronous Command Execution...")
        test_1_synchronous_command_execution(tmp_path)
        print("[PASS] Test 1: Synchronous Command Execution Passed.")

        print("[RUNNING] Test 2: Web Server Auto-Classification & Non-Blocking Launch...")
        test_2_web_server_command_auto_classification(tmp_path)
        print("[PASS] Test 2: Web Server Auto-Classification Passed.")

        print("[RUNNING] Test 3: START_SERVER Action & HTML Preview...")
        test_3_html_preview_start_server(tmp_path)
        print("[PASS] Test 3: START_SERVER Action Passed.")

        print("[RUNNING] Test 4: STOP_SERVER Action...")
        test_4_stop_server(tmp_path)
        print("[PASS] Test 4: STOP_SERVER Action Passed.")

        print("[RUNNING] Test 5: Server Reuse & Idempotency...")
        test_5_repeated_preview_server_reuse(tmp_path)
        print("[PASS] Test 5: Server Reuse Passed.")

        print("[RUNNING] Test 6: Bounded Startup Failure Timeout Check...")
        test_6_bounded_startup_failure_test()
        print("[PASS] Test 6: Bounded Startup Failure Check Passed.")

        print("[RUNNING] Test 7: SSE Stream Lifecycle & Web Server Persistence...")
        test_7_sse_lifecycle_and_server_persistence()
        print("[PASS] Test 7: SSE Stream Lifecycle & Server Persistence Passed.")

    print("=" * 60)
    print("ALL 7 LONG-RUNNING SERVER REGRESSION TESTS PASSED SUCCESSFULLY!")
    print("=" * 60)

if __name__ == "__main__":
    run_all()
