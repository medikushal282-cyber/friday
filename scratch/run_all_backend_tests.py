import os
import sys
import unittest

backend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend")
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

def run_all_tests():
    loader = unittest.TestLoader()
    suite = loader.discover(start_dir=os.path.join(backend_dir, "tests"), pattern="test_*.py")

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("=" * 60)
    print(f"Tests run: {result.testsRun}")
    print(f"Errors: {len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print("=" * 60)

    if not result.wasSuccessful():
        sys.exit(1)

if __name__ == "__main__":
    run_all_tests()
