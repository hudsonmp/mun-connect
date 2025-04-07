#!/usr/bin/env python3
"""
Test runner script for the MUN Connect backend.

This script runs the test suite and generates reports.
"""

import argparse
import os
import sys
import subprocess
import time
import json
from pathlib import Path

# Get the directory of this script
TESTS_DIR = Path(__file__).parent.absolute()
PROJECT_ROOT = TESTS_DIR.parent.absolute()

def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Run tests for the MUN Connect backend")
    
    parser.add_argument("--unit", action="store_true", help="Run unit tests only")
    parser.add_argument("--integration", action="store_true", help="Run integration tests only")
    parser.add_argument("--api", action="store_true", help="Run API tests only")
    parser.add_argument("--aws", action="store_true", help="Run AWS integration tests only")
    parser.add_argument("--auth", action="store_true", help="Run authentication tests only")
    parser.add_argument("--all", action="store_true", help="Run all tests")
    parser.add_argument("--report", action="store_true", help="Generate HTML test report")
    parser.add_argument("--coverage", action="store_true", help="Generate coverage report")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--file", type=str, help="Run a specific test file")
    parser.add_argument("--keyword", "-k", type=str, help="Only run tests matching the given keyword expression")
    
    return parser.parse_args()

def run_tests(args):
    """Run the tests based on command-line arguments."""
    # Build the pytest command
    cmd = ["pytest"]
    
    # Add verbosity
    if args.verbose:
        cmd.append("-v")
    
    # Add coverage
    if args.coverage:
        cmd.extend(["--cov=backend", "--cov-report=term", "--cov-report=html:tests/coverage"])
    
    # Add report generation
    if args.report:
        cmd.append("--html=tests/report/report.html")
    
    # Add test selection
    if args.unit:
        cmd.append("-m unit")
    elif args.integration:
        cmd.append("-m integration")
    elif args.api:
        cmd.append("-m api")
    elif args.aws:
        cmd.append("-m aws")
    elif args.auth:
        cmd.append("-m auth")
    
    # Add specific file if provided
    if args.file:
        file_path = args.file
        if not file_path.startswith("/"):
            file_path = str(TESTS_DIR / file_path)
        cmd.append(file_path)
    
    # Add keyword filter if provided
    if args.keyword:
        cmd.append(f"-k {args.keyword}")
    
    # Convert command to string
    cmd_str = " ".join(cmd)
    
    print(f"Running tests with command: {cmd_str}")
    
    # Create reports directory if needed
    if args.report:
        os.makedirs(TESTS_DIR / "report", exist_ok=True)
    
    if args.coverage:
        os.makedirs(TESTS_DIR / "coverage", exist_ok=True)
    
    # Run the tests
    start_time = time.time()
    result = subprocess.run(cmd_str, shell=True, cwd=PROJECT_ROOT)
    end_time = time.time()
    
    # Print summary
    print("\n" + "=" * 80)
    print(f"Test run completed in {end_time - start_time:.2f} seconds")
    print(f"Exit code: {result.returncode}")
    
    if args.report:
        report_path = TESTS_DIR / "report" / "report.html"
        print(f"HTML report generated: {report_path}")
    
    if args.coverage:
        coverage_path = TESTS_DIR / "coverage" / "index.html"
        print(f"Coverage report generated: {coverage_path}")
    
    return result.returncode

def main():
    """Main entry point."""
    args = parse_args()
    
    # If no specific test type is selected, run all tests
    if not any([args.unit, args.integration, args.api, args.aws, args.auth, args.file, args.keyword, args.all]):
        args.all = True
    
    # Create necessary directories
    os.makedirs(TESTS_DIR / "test_data", exist_ok=True)
    os.makedirs(TESTS_DIR / "test_output", exist_ok=True)
    
    # Run the tests
    exit_code = run_tests(args)
    
    # Return the exit code
    return exit_code

if __name__ == "__main__":
    sys.exit(main()) 