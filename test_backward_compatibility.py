"""
Test backward compatibility - ensure original functionality still works
"""

import sys
import os
from pathlib import Path

# Add the project root to sys.path to import our modules
sys.path.insert(0, str(Path(__file__).parent))

from comparator import resolve_tab_versions
from data_models import TabAnalysis, TabMetadata


def create_mock_tab(name: str) -> TabAnalysis:
    """Create a mock tab analysis."""
    tab = TabAnalysis()
    tab.metadata = TabMetadata()
    tab.metadata.tab_name = name
    tab.metadata.source_system = "TestSource"
    tab.metadata.target_system = "TestTarget"
    tab.mappings = []
    return tab


def test_normal_tabs_no_versions():
    """Test normal tabs without any versioning (original behavior)."""
    print("Testing normal tabs without versions...")
    
    tabs1 = {
        'NormalTab1': create_mock_tab('NormalTab1'),
        'NormalTab2': create_mock_tab('NormalTab2'),
        'AnotherTab': create_mock_tab('AnotherTab'),
    }
    
    tabs2 = {
        'NormalTab1': create_mock_tab('NormalTab1'),
        'NormalTab2': create_mock_tab('NormalTab2'), 
        'NewTab': create_mock_tab('NewTab'),
    }
    
    resolved = resolve_tab_versions(tabs1, tabs2)
    
    print(f"  Resolved {len(resolved)} logical tabs")
    
    # Should have 4 logical tabs: NormalTab1, NormalTab2, AnotherTab, NewTab
    expected_tabs = {'NormalTab1', 'NormalTab2', 'AnotherTab', 'NewTab'}
    actual_tabs = set(resolved.keys())
    
    assert actual_tabs == expected_tabs, f"Expected {expected_tabs}, got {actual_tabs}"
    
    # Check mappings
    assert resolved['NormalTab1']['physical_name_v1'] == 'NormalTab1'
    assert resolved['NormalTab1']['physical_name_v2'] == 'NormalTab1'
    assert resolved['AnotherTab']['physical_name_v2'] is None  # Only in file1
    assert resolved['NewTab']['physical_name_v1'] is None  # Only in file2
    
    print("  [OK] Normal tabs work correctly")


def test_regular_versioned_tabs():
    """Test regular versioned tabs (existing functionality)."""
    print("Testing regular versioned tabs...")
    
    tabs1 = {
        'DataTab': create_mock_tab('DataTab'),
        'ProcessTab (2)': create_mock_tab('ProcessTab (2)'),
    }
    
    tabs2 = {
        'DataTab': create_mock_tab('DataTab'),
        'ProcessTab': create_mock_tab('ProcessTab'),
        'ProcessTab (2)': create_mock_tab('ProcessTab (2)'),
        'ProcessTab (3)': create_mock_tab('ProcessTab (3)'),
    }
    
    resolved = resolve_tab_versions(tabs1, tabs2)
    
    print(f"  Resolved {len(resolved)} logical tabs")
    
    # Should have 2 logical tabs: DataTab, ProcessTab
    expected_tabs = {'DataTab', 'ProcessTab'}
    actual_tabs = set(resolved.keys())
    
    assert actual_tabs == expected_tabs, f"Expected {expected_tabs}, got {actual_tabs}"
    
    # Check version resolution
    assert resolved['ProcessTab']['physical_name_v1'] == 'ProcessTab (2)'  # Highest in file1
    assert resolved['ProcessTab']['physical_name_v2'] == 'ProcessTab (3)'  # Highest in file2
    assert resolved['ProcessTab']['version_v1'] == 2
    assert resolved['ProcessTab']['version_v2'] == 3
    
    print("  [OK] Versioned tabs work correctly")


def test_edge_cases():
    """Test edge cases that could be affected by changes."""
    print("Testing edge cases...")
    
    # Case 1: Tab names with similar prefixes but different purposes
    tabs1 = {
        'Vendor': create_mock_tab('Vendor'),
        'VendorData': create_mock_tab('VendorData'),
        'VendorProcessing': create_mock_tab('VendorProcessing'),
    }
    
    tabs2 = {
        'Vendor': create_mock_tab('Vendor'),
        'VendorData': create_mock_tab('VendorData'),
        'VendorProcessing': create_mock_tab('VendorProcessing'),
    }
    
    resolved = resolve_tab_versions(tabs1, tabs2)
    
    # Should maintain all 3 separate tabs
    expected_tabs = {'Vendor', 'VendorData', 'VendorProcessing'}
    actual_tabs = set(resolved.keys())
    
    assert actual_tabs == expected_tabs, f"Expected {expected_tabs}, got {actual_tabs}"
    print("  [OK] Similar prefix tabs handled correctly")
    
    # Case 2: Very short tab names
    tabs1 = {'A': create_mock_tab('A'), 'B': create_mock_tab('B')}
    tabs2 = {'A': create_mock_tab('A'), 'C': create_mock_tab('C')}
    
    resolved = resolve_tab_versions(tabs1, tabs2)
    expected_tabs = {'A', 'B', 'C'}
    actual_tabs = set(resolved.keys())
    
    assert actual_tabs == expected_tabs, f"Expected {expected_tabs}, got {actual_tabs}"
    print("  [OK] Short tab names handled correctly")


def test_feature_disabled():
    """Test behavior when truncated matching is disabled."""
    print("Testing with truncated matching disabled...")
    
    import config
    original_setting = config.ENABLE_TRUNCATED_TAB_MATCHING
    
    try:
        # Disable the feature
        config.ENABLE_TRUNCATED_TAB_MATCHING = False
        
        tabs1 = {'VeryLongTabNameThatWouldBeTruncated': create_mock_tab('VeryLongTabNameThatWouldBeTruncated')}
        tabs2 = {'VeryLongTabNameThatWouldBe (2)': create_mock_tab('VeryLongTabNameThatWouldBe (2)')}
        
        resolved = resolve_tab_versions(tabs1, tabs2)
        
        # Should treat as separate tabs when feature is disabled
        expected_tabs = {'VeryLongTabNameThatWouldBeTruncated', 'VeryLongTabNameThatWouldBe'}
        actual_tabs = set(resolved.keys())
        
        assert actual_tabs == expected_tabs, f"Expected {expected_tabs}, got {actual_tabs}"
        print("  [OK] Feature can be disabled correctly")
        
    finally:
        # Restore original setting
        config.ENABLE_TRUNCATED_TAB_MATCHING = original_setting


def main():
    """Run all backward compatibility tests."""
    print("="*60)
    print("BACKWARD COMPATIBILITY TESTS")
    print("="*60)
    
    try:
        test_normal_tabs_no_versions()
        test_regular_versioned_tabs()
        test_edge_cases()
        test_feature_disabled()
        
        print("\n" + "="*60)
        print("[SUCCESS] ALL BACKWARD COMPATIBILITY TESTS PASSED!")
        print("="*60)
        print("\nExisting functionality is preserved:")
        print("[OK] Normal tabs without versions work as before")
        print("[OK] Regular versioned tabs work as before")
        print("[OK] Edge cases are handled correctly")
        print("[OK] New feature can be disabled")
        
    except Exception as e:
        print(f"\n[FAIL] BACKWARD COMPATIBILITY TEST FAILED: {e}")
        raise


if __name__ == "__main__":
    main()