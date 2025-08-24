#!/usr/bin/env python3
"""
Test script for Phase 4: Main Application & Error Handling

This script tests the main application interface, error handling,
logging system, and integration between all components.
"""

import os
import sys
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
import logging

# Add current directory to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import ExcelComparisonApp
from exceptions import (
    ExcelComparisonError, FileValidationError, ComparisonError,
    ReportGenerationError, create_user_friendly_message
)
from logger import get_logger, setup_debug_logging, PerformanceTimer
from utils import validate_file_path


def test_main_application_cli():
    """Test the main application command line interface."""
    print("\n" + "="*60)
    print("TEST 1: Main Application CLI")
    print("="*60)
    
    try:
        # Test basic comparison
        app = ExcelComparisonApp()
        
        # Test with valid files
        args = ['STTM.xlsx', 'STTM2.xlsx', '--progress']
        result = app.run(args)
        
        if result == 0:
            print("[PASS] PASSED: Main application CLI test successful")
            return True
        else:
            print(f"[FAIL] FAILED: Main application returned exit code {result}")
            return False
            
    except Exception as e:
        print(f"[FAIL] ERROR: {e}")
        return False


def test_error_handling():
    """Test custom exception handling."""
    print("\n" + "="*60)
    print("TEST 2: Error Handling System")
    print("="*60)
    
    tests_passed = 0
    total_tests = 0
    
    # Test FileValidationError
    try:
        total_tests += 1
        raise FileValidationError("nonexistent.xlsx", "File not found")
    except FileValidationError as e:
        user_message = create_user_friendly_message(e)
        if "could not be found" in user_message.lower():
            print("[PASS] FileValidationError handling: PASS")
            tests_passed += 1
        else:
            print("[FAIL] FileValidationError handling: FAIL")
    
    # Test ComparisonError
    try:
        total_tests += 1
        raise ComparisonError("Comparison failed", "file1.xlsx", "file2.xlsx")
    except ComparisonError as e:
        user_message = create_user_friendly_message(e)
        if "Comparison failed" in user_message:
            print("[PASS] ComparisonError handling: PASS")
            tests_passed += 1
        else:
            print("[FAIL] ComparisonError handling: FAIL")
    
    # Test ReportGenerationError
    try:
        total_tests += 1
        raise ReportGenerationError("output.html", "Permission denied")
    except ReportGenerationError as e:
        user_message = create_user_friendly_message(e)
        if "report" in user_message.lower():
            print("[PASS] ReportGenerationError handling: PASS")
            tests_passed += 1
        else:
            print("[FAIL] ReportGenerationError handling: FAIL")
    
    print(f"\nError handling tests: {tests_passed}/{total_tests} passed")
    return tests_passed == total_tests


def test_logging_system():
    """Test the logging system functionality."""
    print("\n" + "="*60)
    print("TEST 3: Logging System")
    print("="*60)
    
    try:
        # Test different logger configurations
        logger = get_logger("test_module", level="DEBUG")
        logger.info("Test info message")
        logger.warning("Test warning message")
        logger.error("Test error message")
        logger.debug("Test debug message")
        
        # Test debug logging
        debug_logger = setup_debug_logging()
        debug_logger.debug("Debug mode test message")
        
        # Test performance timer
        with PerformanceTimer(logger, "test operation", "processing test data"):
            import time
            time.sleep(0.1)  # Simulate work
        
        # Check if log files are created
        log_dir = Path("logs")
        if log_dir.exists():
            log_files = list(log_dir.glob("*.log"))
            if log_files:
                print(f"[PASS] Log files created: {len(log_files)} files")
                print("[PASS] PASSED: Logging system test successful")
                return True
            else:
                print("[FAIL] No log files created")
                return False
        else:
            print("[FAIL] Log directory not created")
            return False
            
    except Exception as e:
        print(f"[FAIL] ERROR: {e}")
        return False


def test_file_validation():
    """Test file validation with various scenarios."""
    print("\n" + "="*60)
    print("TEST 4: File Validation")
    print("="*60)
    
    tests_passed = 0
    total_tests = 0
    
    # Test valid file
    total_tests += 1
    is_valid, error = validate_file_path("STTM.xlsx")
    if is_valid:
        print("[PASS] Valid file validation: PASS")
        tests_passed += 1
    else:
        print(f"[FAIL] Valid file validation: FAIL - {error}")
    
    # Test non-existent file
    total_tests += 1
    is_valid, error = validate_file_path("nonexistent.xlsx")
    if not is_valid and "not found" in error.lower():
        print("[PASS] Non-existent file validation: PASS")
        tests_passed += 1
    else:
        print("[FAIL] Non-existent file validation: FAIL")
    
    # Test invalid extension
    total_tests += 1
    is_valid, error = validate_file_path("test.txt")
    if not is_valid:
        print("[PASS] Invalid extension validation: PASS")
        tests_passed += 1
    else:
        print("[FAIL] Invalid extension validation: FAIL")
    
    print(f"\nFile validation tests: {tests_passed}/{total_tests} passed")
    return tests_passed == total_tests


def test_command_line_arguments():
    """Test command line argument parsing."""
    print("\n" + "="*60)
    print("TEST 5: Command Line Arguments")
    print("="*60)
    
    try:
        app = ExcelComparisonApp()
        parser = app.create_argument_parser()
        
        # Test basic arguments
        args = parser.parse_args(['file1.xlsx', 'file2.xlsx'])
        if args.file1 == 'file1.xlsx' and args.file2 == 'file2.xlsx':
            print("[PASS] Basic argument parsing: PASS")
        else:
            print("[FAIL] Basic argument parsing: FAIL")
            return False
        
        # Test optional arguments
        args = parser.parse_args(['--debug', '--output', 'custom.html', 'file1.xlsx', 'file2.xlsx'])
        if args.debug and args.output == 'custom.html':
            print("[PASS] Optional argument parsing: PASS")
        else:
            print("[FAIL] Optional argument parsing: FAIL")
            return False
        
        # Test validation-only mode
        args = parser.parse_args(['--validate-only', 'file1.xlsx', 'file2.xlsx'])
        if args.validate_only:
            print("[PASS] Validate-only mode: PASS")
        else:
            print("[FAIL] Validate-only mode: FAIL")
            return False
        
        print("[PASS] PASSED: Command line arguments test successful")
        return True
        
    except Exception as e:
        print(f"[FAIL] ERROR: {e}")
        return False


def test_integration_with_existing_modules():
    """Test integration between new Phase 4 modules and existing code."""
    print("\n" + "="*60)
    print("TEST 6: Integration with Existing Modules")
    print("="*60)
    
    try:
        # Test integration with comparator
        from comparator import compare_workbooks
        
        logger = get_logger("integration_test")
        logger.info("Testing integration with comparator module")
        
        # This should use the new error handling
        result = compare_workbooks("STTM.xlsx", "STTM2.xlsx")
        
        if result and not result.has_errors:
            print("[PASS] Comparator integration: PASS")
        else:
            print(f"[FAIL] Comparator integration: FAIL - {result.errors if result else 'No result'}")
            return False
        
        # Test integration with report generator
        from report_generator import generate_html_report
        
        report_path = "reports/test_reports/integration_test.html"
        success = generate_html_report(result, report_path, "Integration Test Report")
        
        if success and Path(report_path).exists():
            print("[PASS] Report generator integration: PASS")
        else:
            print("[FAIL] Report generator integration: FAIL")
            return False
        
        print("[PASS] PASSED: Integration test successful")
        return True
        
    except Exception as e:
        print(f"[FAIL] ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_error_recovery():
    """Test error recovery mechanisms."""
    print("\n" + "="*60)
    print("TEST 7: Error Recovery")
    print("="*60)
    
    try:
        app = ExcelComparisonApp()
        
        # Test with invalid first file
        result1 = app.run(['nonexistent1.xlsx', 'STTM2.xlsx', '--quiet'])
        if result1 != 0:  # Should fail gracefully
            print("[PASS] Invalid file error recovery: PASS")
        else:
            print("[FAIL] Invalid file error recovery: FAIL")
            return False
        
        # Test with invalid output directory
        invalid_path = "/invalid/path/report.html" if os.name != 'nt' else "Z:\\invalid\\path\\report.html"
        result2 = app.run(['STTM.xlsx', 'STTM2.xlsx', '--output', invalid_path, '--quiet'])
        if result2 != 0:  # Should fail gracefully
            print("[PASS] Invalid output path error recovery: PASS")
        else:
            print("[FAIL] Invalid output path error recovery: FAIL") 
            return False
        
        print("[PASS] PASSED: Error recovery test successful")
        return True
        
    except Exception as e:
        print(f"[FAIL] ERROR: {e}")
        return False


def run_all_phase4_tests():
    """Run all Phase 4 tests."""
    print("Starting Phase 4: Main Application & Error Handling Tests")
    print("="*60)
    
    tests = [
        ("Command Line Arguments", test_command_line_arguments),
        ("Error Handling System", test_error_handling),
        ("Logging System", test_logging_system),
        ("File Validation", test_file_validation),
        ("Integration with Existing Modules", test_integration_with_existing_modules),
        ("Error Recovery", test_error_recovery),
        ("Main Application CLI", test_main_application_cli),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"[FAIL] ERROR in {test_name}: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "="*60)
    print("PHASE 4 TEST RESULTS SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "PASSED" if result else "FAILED"
        print(f"{status} - {test_name}")
    
    print(f"\nOverall: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("[SUCCESS] All Phase 4 tests passed! Main Application & Error Handling is working correctly.")
        print("\nPhase 4 Features Verified:")
        print("  [PASS] Command Line Interface")
        print("  [PASS] Custom Exception Classes")
        print("  [PASS] Comprehensive Logging System")
        print("  [PASS] Error Recovery Mechanisms")
        print("  [PASS] Integration with Existing Modules")
        print("  [PASS] User-Friendly Error Messages")
        return True
    else:
        print("[ERROR] Some Phase 4 tests failed. Please review the implementation.")
        return False


if __name__ == "__main__":
    # Ensure we're in the correct directory
    script_dir = Path(__file__).parent
    os.chdir(script_dir)
    
    # Run all tests
    success = run_all_phase4_tests()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)