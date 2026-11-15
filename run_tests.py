#!/usr/bin/env python3
import sys
import unittest


def run_all_tests() -> bool:
    test_loader = unittest.defaultTestLoader
    test_suite = test_loader.discover(start_dir="tests", pattern="test_*.py")
    test_runner = unittest.TextTestRunner(verbosity=2)
    test_result = test_runner.run(test_suite)
    return test_result.wasSuccessful()


if __name__ == "__main__":
    tests_succeeded = run_all_tests()
    sys.exit(0 if tests_succeeded else 1)
