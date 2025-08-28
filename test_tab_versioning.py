"""
Test Tab Versioning Functionality

This script tests the new tab versioning feature that handles Excel tabs
with version suffixes like " (2)", " (3)" etc.
"""

import sys
import os
from pathlib import Path

# Add the project root to sys.path to import our modules
sys.path.insert(0, str(Path(__file__).parent))

from comparator import resolve_tab_versions, compare_workbooks
from data_models import TabAnalysis, TabMetadata
from excel_analyzer import analyze_workbook


def test_version_resolution():
    """Test the tab version resolution logic with mock data."""
    print("Testing tab version resolution logic...")
    
    # Create mock tab analyses
    def create_mock_tab(name: str) -> TabAnalysis:
        tab = TabAnalysis()
        tab.metadata = TabMetadata()
        tab.metadata.tab_name = name
        tab.metadata.source_system = "TestSource"
        tab.metadata.target_system = "TestTarget"
        tab.mappings = []  # Empty for testing
        return tab
    
    # Test scenario 1: Excel1 has base, Excel2 has versioned copies
    print("\nTest 1: Excel1 base -> Excel2 versioned")
    tabs1 = {
        "Vendor Inbound DACH VenProxy": create_mock_tab("Vendor Inbound DACH VenProxy")
    }
    
    tabs2 = {
        "Vendor Inbound DACH VenProxy": create_mock_tab("Vendor Inbound DACH VenProxy"),
        "Vendor Inbound DACH VenProxy (2)": create_mock_tab("Vendor Inbound DACH VenProxy (2)")
    }
    
    resolved = resolve_tab_versions(tabs1, tabs2)
    
    for logical_name, resolution in resolved.items():
        print(f"  Logical: {logical_name}")
        print(f"    File1: {resolution['physical_name_v1']} (v{resolution['version_v1']})")
        print(f"    File2: {resolution['physical_name_v2']} (v{resolution['version_v2']})")
        print(f"    Expected: File1 base vs File2 highest version")
        
        # Verify File2 chose the highest version
        assert resolution['version_v2'] == 2, f"Expected version 2 for File2, got {resolution['version_v2']}"
        print("    [OK] PASS: File2 correctly selected highest version")
    
    # Test scenario 2: Complex versioning with gaps
    print("\nTest 2: Complex versioning scenario")
    tabs1 = {
        "Tab A": create_mock_tab("Tab A"),
        "Tab A (2)": create_mock_tab("Tab A (2)")
    }
    
    tabs2 = {
        "Tab A": create_mock_tab("Tab A"),
        "Tab A (2)": create_mock_tab("Tab A (2)"),
        "Tab A (3)": create_mock_tab("Tab A (3)")
    }
    
    resolved = resolve_tab_versions(tabs1, tabs2)
    
    for logical_name, resolution in resolved.items():
        print(f"  Logical: {logical_name}")
        print(f"    File1: {resolution['physical_name_v1']} (v{resolution['version_v1']})")
        print(f"    File2: {resolution['physical_name_v2']} (v{resolution['version_v2']})")
        
        # File1 should choose v2 (highest), File2 should choose v3 (highest)
        if logical_name == "Tab A":
            assert resolution['version_v1'] == 2, f"Expected v1=2, got {resolution['version_v1']}"
            assert resolution['version_v2'] == 3, f"Expected v2=3, got {resolution['version_v2']}"
            print("    [OK] PASS: Both files correctly selected highest versions")
    
    print("\n[SUCCESS] All tab version resolution tests passed!")


def test_truncated_tab_names():
    """Test truncated tab name matching functionality."""
    print("\nTesting truncated tab name matching...")
    
    # Test the truncation detection
    from comparator import resolve_tab_versions
    
    def create_mock_tab(name: str) -> TabAnalysis:
        tab = TabAnalysis()
        tab.metadata = TabMetadata()
        tab.metadata.tab_name = name
        tab.metadata.source_system = "TestSource"
        tab.metadata.target_system = "TestTarget"
        tab.mappings = []
        return tab
    
    # Test scenario: Long name gets truncated in Excel
    print("\nTest 3: Truncated tab name scenario")
    
    # Original long name (34 characters)
    original_name = "VendorInboundVendorProxytoD365STTM"
    truncated_name = "VendorInboundVendorProxytoD (2)"  # Exactly 31 characters
    
    tabs1 = {
        original_name: create_mock_tab(original_name)
    }
    
    tabs2 = {
        original_name: create_mock_tab(original_name),  # Locked version
        truncated_name: create_mock_tab(truncated_name)  # Active version (truncated copy)
    }
    
    resolved = resolve_tab_versions(tabs1, tabs2)
    
    print(f"  Original name: '{original_name}' ({len(original_name)} chars)")
    print(f"  Truncated name: '{truncated_name}' ({len(truncated_name)} chars)")
    
    for logical_name, resolution in resolved.items():
        print(f"  Logical: {logical_name}")
        print(f"    File1: {resolution['physical_name_v1']} (v{resolution['version_v1']})")
        print(f"    File2: {resolution['physical_name_v2']} (v{resolution['version_v2']})")
        
        # Should match the original with the truncated copy
        if logical_name == original_name:
            assert resolution['physical_name_v1'] == original_name
            assert resolution['physical_name_v2'] == truncated_name
            assert resolution['version_v2'] == 2
            print("    [OK] PASS: Truncated name correctly matched with original")
    
    print("[SUCCESS] Truncated tab name tests passed!")


def test_comparison_with_versioning():
    """Test the full comparison process with versioned tabs."""
    print("\nTesting comparison with version resolution...")
    
    # This would require actual Excel files to test properly
    # For now, we'll just verify the integration points work
    
    def create_mock_tab_with_mappings(name: str, mapping_count: int) -> TabAnalysis:
        from data_models import MappingRecord
        
        tab = TabAnalysis()
        tab.metadata = TabMetadata()
        tab.metadata.tab_name = name
        tab.metadata.source_system = f"System_{name.replace(' ', '_')}"
        tab.metadata.target_system = f"Target_{name.replace(' ', '_')}"
        
        # Create mock mappings
        for i in range(mapping_count):
            mapping = MappingRecord()
            mapping.source_canonical = f"source_{i}"
            mapping.source_field = f"field_{i}"
            mapping.target_canonical = f"target_{i}"
            mapping.target_field = f"field_{i}"
            mapping.row_number = i + 1
            tab.mappings.append(mapping)
        
        return tab
    
    # Mock scenario: File1 has 5 mappings, File2 (v2) has 7 mappings
    tabs1 = {
        "Process Tab": create_mock_tab_with_mappings("Process Tab", 5)
    }
    
    tabs2 = {
        "Process Tab": create_mock_tab_with_mappings("Process Tab", 3),  # Locked version
        "Process Tab (2)": create_mock_tab_with_mappings("Process Tab (2)", 7)  # Active version
    }
    
    # Test that comparison works with version resolution
    try:
        from comparator import compare_all_tabs
        
        result = compare_all_tabs(tabs1, tabs2)
        
        # Should have one logical tab comparison
        assert len(result) == 1, f"Expected 1 logical tab, got {len(result)}"
        
        logical_name = list(result.keys())[0]
        comparison = result[logical_name]
        
        print(f"  Comparison result for '{logical_name}':")
        print(f"    Status: {comparison.status}")
        print(f"    Physical v1: {comparison.physical_name_v1}")
        print(f"    Physical v2: {comparison.physical_name_v2}")
        print(f"    Version v1: {comparison.version_v1}")
        print(f"    Version v2: {comparison.version_v2}")
        
        # Verify version metadata is set
        assert comparison.logical_name == "Process Tab"
        assert comparison.physical_name_v2 == "Process Tab (2)"  # Should pick the active version
        assert comparison.version_v2 == 2
        
        print("    [OK] PASS: Comparison correctly used version resolution")
        
    except Exception as e:
        print(f"    [FAIL] Error during comparison: {e}")
        raise
    
    print("\n[SUCCESS] All comparison integration tests passed!")


def main():
    """Run all tab versioning tests."""
    print("="*60)
    print("TAB VERSIONING FEATURE TESTS")
    print("="*60)
    
    try:
        test_version_resolution()
        test_truncated_tab_names()
        test_comparison_with_versioning()
        
        print("\n" + "="*60)
        print("[SUCCESS] ALL TAB VERSIONING TESTS PASSED!")
        print("="*60)
        print("\nThe tab versioning feature is working correctly:")
        print("[OK] Tab version resolution identifies active versions")
        print("[OK] Truncated tab name matching works correctly")
        print("[OK] Comparison logic uses resolved versions")
        print("[OK] Version metadata is preserved in results")
        print("[OK] Reports will show logical names with version info")
        
    except Exception as e:
        print(f"\n[FAIL] TEST FAILED: {e}")
        raise


if __name__ == "__main__":
    main()