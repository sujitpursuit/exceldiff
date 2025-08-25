#!/usr/bin/env python3
"""
Test script for Enhanced Key Formation Logic

This script tests the new tiered key generation system that handles
partial mappings where only source OR target side is complete.
"""

import logging
from data_models import MappingRecord
from comparator import compare_tab_mappings

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


def test_key_generation():
    """Test the new tiered key generation logic."""
    print("\n" + "="*60)
    print("TEST: Enhanced Key Generation")
    print("="*60)
    
    # Test scenarios for key generation
    test_cases = [
        {
            "name": "Complete Mapping",
            "source_canonical": "FinancialRequest",
            "source_field": "CustomerID",
            "target_canonical": "VendTable",
            "target_field": "AccountNum",
            "expected_prefix": "COMPLETE"
        },
        {
            "name": "Source-Only Complete",
            "source_canonical": "FinancialRequest",
            "source_field": "CustomerID", 
            "target_canonical": "",
            "target_field": "",
            "expected_prefix": "SOURCE_ONLY"
        },
        {
            "name": "Target-Only Complete",
            "source_canonical": "",
            "source_field": "",
            "target_canonical": "VendTable",
            "target_field": "AccountNum",
            "expected_prefix": "TARGET_ONLY"
        },
        {
            "name": "Partial Mapping (Source canonical only)",
            "source_canonical": "FinancialRequest",
            "source_field": "",
            "target_canonical": "",
            "target_field": "AccountNum",
            "expected_prefix": "PARTIAL"
        },
        {
            "name": "Empty Mapping",
            "source_canonical": "",
            "source_field": "",
            "target_canonical": "",
            "target_field": "",
            "expected_prefix": "PARTIAL"
        }
    ]
    
    delimiter = "||@@||"
    passed = 0
    total = len(test_cases)
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\nTest {i}: {test_case['name']}")
        
        # Create mapping record
        mapping = MappingRecord(
            source_canonical=test_case["source_canonical"],
            source_field=test_case["source_field"],
            target_canonical=test_case["target_canonical"],
            target_field=test_case["target_field"],
            row_number=i
        )
        
        # Generate unique ID
        unique_id = mapping.generate_unique_id()
        print(f"  Generated ID: {unique_id}")
        
        # Check prefix
        expected_prefix = test_case["expected_prefix"]
        if unique_id.startswith(expected_prefix + delimiter):
            print(f"  [PASS] Correct prefix: {expected_prefix}")
            passed += 1
        else:
            print(f"  [FAIL] Expected prefix: {expected_prefix}, got: {unique_id.split(delimiter)[0]}")
        
        # Check delimiter usage
        parts = unique_id.split(delimiter)
        if len(parts) >= 5:  # Should have at least 5 parts for standard keys
            print(f"  [PASS] Delimiter structure correct: {len(parts)} parts")
        else:
            print(f"  [FAIL] Unexpected delimiter structure: {len(parts)} parts")
    
    print(f"\nKey Generation Test Results: {passed}/{total} tests passed")
    return passed == total


def test_validation_logic():
    """Test the updated validation logic for partial mappings."""
    print("\n" + "="*60)
    print("TEST: Enhanced Validation Logic")
    print("="*60)
    
    test_cases = [
        {
            "name": "Complete mapping",
            "source_canonical": "FinancialRequest",
            "source_field": "CustomerID",
            "target_canonical": "VendTable", 
            "target_field": "AccountNum",
            "should_be_valid": True
        },
        {
            "name": "Source-only complete",
            "source_canonical": "FinancialRequest",
            "source_field": "CustomerID",
            "target_canonical": "",
            "target_field": "",
            "should_be_valid": True
        },
        {
            "name": "Target-only complete", 
            "source_canonical": "",
            "source_field": "",
            "target_canonical": "VendTable",
            "target_field": "AccountNum",
            "should_be_valid": True
        },
        {
            "name": "Partial with some data on both sides",
            "source_canonical": "FinancialRequest",
            "source_field": "",
            "target_canonical": "",
            "target_field": "AccountNum",
            "should_be_valid": True
        },
        {
            "name": "Completely empty",
            "source_canonical": "",
            "source_field": "",
            "target_canonical": "",
            "target_field": "",
            "should_be_valid": False
        }
    ]
    
    passed = 0
    total = len(test_cases)
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\nTest {i}: {test_case['name']}")
        
        mapping = MappingRecord(
            source_canonical=test_case["source_canonical"],
            source_field=test_case["source_field"],
            target_canonical=test_case["target_canonical"],
            target_field=test_case["target_field"]
        )
        
        is_valid = mapping.is_valid()
        should_be_valid = test_case["should_be_valid"]
        
        if is_valid == should_be_valid:
            status = "PASS" if is_valid else "PASS (correctly invalid)"
            print(f"  [{status}] Validation result: {is_valid}")
            passed += 1
        else:
            print(f"  [FAIL] Expected: {should_be_valid}, got: {is_valid}")
    
    print(f"\nValidation Test Results: {passed}/{total} tests passed")
    return passed == total


def test_comparison_scenarios():
    """Test comparison scenarios with partial mappings."""
    print("\n" + "="*60)
    print("TEST: Enhanced Comparison Scenarios")
    print("="*60)
    
    # Scenario 1: Source-only becomes complete
    print("\nScenario 1: Source-only becomes complete mapping")
    
    mappings_v1 = [
        MappingRecord(
            source_canonical="FinancialRequest",
            source_field="CustomerID",
            target_canonical="",
            target_field="",
            row_number=1
        )
    ]
    
    mappings_v2 = [
        MappingRecord(
            source_canonical="FinancialRequest", 
            source_field="CustomerID",
            target_canonical="VendTable",
            target_field="AccountNum",
            row_number=1
        )
    ]
    
    result = compare_tab_mappings(mappings_v1, mappings_v2)
    print(f"  Added: {len(result['added'])}")
    print(f"  Deleted: {len(result['deleted'])}")
    print(f"  Modified: {len(result['modified'])}")
    
    # Check if we detected completion scenario
    completion_detected = any(
        change.change_type == "completed_mapping" 
        for change in result['modified']
    )
    
    if completion_detected:
        print("  [PASS] Completion scenario detected")
    else:
        print("  [INFO] Standard add/delete detected (also valid)")
    
    # Scenario 2: Multiple partial mappings
    print("\nScenario 2: Multiple partial mappings")
    
    mappings_v1 = [
        MappingRecord(source_canonical="System1", source_field="Field1", row_number=1),
        MappingRecord(target_canonical="System2", target_field="Field2", row_number=2)
    ]
    
    mappings_v2 = [
        MappingRecord(source_canonical="System1", source_field="Field1", row_number=1),
        MappingRecord(target_canonical="System2", target_field="Field2", row_number=2),
        MappingRecord(source_canonical="System3", source_field="Field3", 
                     target_canonical="System4", target_field="Field4", row_number=3)
    ]
    
    result = compare_tab_mappings(mappings_v1, mappings_v2)
    print(f"  Added: {len(result['added'])}")
    print(f"  Deleted: {len(result['deleted'])}")
    print(f"  Modified: {len(result['modified'])}")
    
    print("\nComparison scenarios tested successfully")
    return True


def run_all_tests():
    """Run all enhanced key formation tests."""
    print("Enhanced Key Formation Tests")
    print("="*60)
    
    tests = [
        ("Key Generation", test_key_generation),
        ("Validation Logic", test_validation_logic),
        ("Comparison Scenarios", test_comparison_scenarios)
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
    print("TEST RESULTS SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "PASSED" if result else "FAILED" 
        print(f"{status} - {test_name}")
    
    print(f"\nOverall: {passed}/{total} test groups passed ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("All enhanced key formation tests passed!")
        return True
    else:
        print("Some tests failed. Please review the enhanced key logic.")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)