#!/usr/bin/env python3
"""
Debug script for Row 13 Comment Change Issue

This script traces exactly what happens to row 13 in NetSuiteVendorRequestResponsOTV
to understand why the comment change isn't being detected.
"""

import logging
from pathlib import Path
from data_models import MappingRecord
from excel_analyzer import analyze_workbook
from comparator import compare_workbooks

# Set up detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


def debug_specific_row():
    """Debug the specific row 13 case."""
    print("\n" + "="*60)
    print("DEBUG: Row 13 Comment Change Detection")
    print("="*60)
    
    file1 = "STTM.xlsx"
    file2 = "STTM2.xlsx"
    target_tab = "NetSuiteVendorRequestResponsOTV"
    target_canonical = "NetSuite Vendor Work Item"
    target_field = "SourceSystem"
    
    print(f"Looking for mappings with:")
    print(f"  Target Canonical: '{target_canonical}'")
    print(f"  Target Field: '{target_field}'")
    print(f"  Expected change: Comments field")
    
    # Analyze both files
    print(f"\nAnalyzing {file1}...")
    workbook1_analysis = analyze_workbook(file1)
    
    print(f"Analyzing {file2}...")
    workbook2_analysis = analyze_workbook(file2)
    
    if target_tab not in workbook1_analysis or target_tab not in workbook2_analysis:
        print(f"ERROR: Tab '{target_tab}' not found in one or both files")
        return False
    
    tab1 = workbook1_analysis[target_tab]
    tab2 = workbook2_analysis[target_tab]
    
    print(f"\nTab '{target_tab}' analysis:")
    print(f"  File 1 mappings: {len(tab1.mappings)}")
    print(f"  File 2 mappings: {len(tab2.mappings)}")
    
    # Find target mappings in both files
    target_mappings_1 = []
    target_mappings_2 = []
    
    for mapping in tab1.mappings:
        if (mapping.target_canonical == target_canonical and 
            mapping.target_field == target_field):
            target_mappings_1.append(mapping)
    
    for mapping in tab2.mappings:
        if (mapping.target_canonical == target_canonical and 
            mapping.target_field == target_field):
            target_mappings_2.append(mapping)
    
    print(f"\nFound target mappings:")
    print(f"  File 1: {len(target_mappings_1)} matches")
    print(f"  File 2: {len(target_mappings_2)} matches")
    
    if not target_mappings_1 or not target_mappings_2:
        print("ERROR: Target mapping not found in one or both files!")
        
        # Show all mappings for debugging
        print(f"\nAll mappings in {target_tab} (File 1):")
        for i, mapping in enumerate(tab1.mappings):
            print(f"  {i+1}: '{mapping.target_canonical}' | '{mapping.target_field}' (Row: {mapping.row_number})")
        
        print(f"\nAll mappings in {target_tab} (File 2):")
        for i, mapping in enumerate(tab2.mappings):
            print(f"  {i+1}: '{mapping.target_canonical}' | '{mapping.target_field}' (Row: {mapping.row_number})")
        
        return False
    
    # Analyze each matching mapping
    for i, (mapping1, mapping2) in enumerate(zip(target_mappings_1, target_mappings_2)):
        print(f"\n--- Target Mapping {i+1} Analysis ---")
        
        print(f"File 1 Mapping:")
        print(f"  Row: {mapping1.row_number}")
        print(f"  Source: '{mapping1.source_canonical}' | '{mapping1.source_field}'")
        print(f"  Target: '{mapping1.target_canonical}' | '{mapping1.target_field}'")
        print(f"  Unique ID: {mapping1.unique_id}")
        print(f"  All fields count: {len(mapping1.all_fields)}")
        
        # Look for comment fields
        comment_fields_1 = {k: v for k, v in mapping1.all_fields.items() 
                           if 'comment' in k.lower() and v}
        if comment_fields_1:
            print(f"  Comment fields: {comment_fields_1}")
        else:
            print(f"  Comment fields: None found")
            # Show all fields for debugging
            print(f"  All fields: {list(mapping1.all_fields.keys())}")
        
        print(f"\nFile 2 Mapping:")
        print(f"  Row: {mapping2.row_number}")
        print(f"  Source: '{mapping2.source_canonical}' | '{mapping2.source_field}'")
        print(f"  Target: '{mapping2.target_canonical}' | '{mapping2.target_field}'")
        print(f"  Unique ID: {mapping2.unique_id}")
        print(f"  All fields count: {len(mapping2.all_fields)}")
        
        # Look for comment fields
        comment_fields_2 = {k: v for k, v in mapping2.all_fields.items() 
                           if 'comment' in k.lower() and v}
        if comment_fields_2:
            print(f"  Comment fields: {comment_fields_2}")
        else:
            print(f"  Comment fields: None found")
            # Show all fields for debugging
            print(f"  All fields: {list(mapping2.all_fields.keys())}")
        
        # Check if unique IDs match
        if mapping1.unique_id == mapping2.unique_id:
            print(f"  [PASS] Unique IDs match - will be compared")
            
            # Check for differences in ALL fields
            all_fields_1 = mapping1.all_fields or {}
            all_fields_2 = mapping2.all_fields or {}
            all_field_names = set(all_fields_1.keys()) | set(all_fields_2.keys())
            
            # Look for expected change values in any field
            expected_old = "SourceSystem = D365"
            expected_new = "SourceSystem = D365_changed"
            
            print(f"\n  Searching for expected change:")
            print(f"    Old: '{expected_old}'")
            print(f"    New: '{expected_new}'")
            
            fields_with_expected = []
            all_changes = {}
            
            for field_name in all_field_names:
                value1 = str(all_fields_1.get(field_name, "")).strip()
                value2 = str(all_fields_2.get(field_name, "")).strip()
                
                # Check if this field has the expected values
                if expected_old in value1 or expected_new in value2:
                    fields_with_expected.append(field_name)
                    print(f"    [FOUND] Field '{field_name}':")
                    print(f"      File 1: '{value1}'")
                    print(f"      File 2: '{value2}'")
                
                # Track all changes
                if value1 != value2:
                    all_changes[field_name] = (value1, value2)
            
            if fields_with_expected:
                print(f"  [SUCCESS] Found expected change in {len(fields_with_expected)} field(s)")
            else:
                print(f"  [ERROR] Expected change not found in any field!")
                
                # Show all non-empty fields for debugging
                print(f"\n  All non-empty fields in File 1:")
                for field_name, value in all_fields_1.items():
                    if str(value).strip():
                        print(f"    {field_name}: '{value}'")
                
                print(f"\n  All non-empty fields in File 2:")
                for field_name, value in all_fields_2.items():
                    if str(value).strip():
                        print(f"    {field_name}: '{value}'")
            
            if all_changes:
                print(f"\n  All field changes detected ({len(all_changes)}):")
                for field_name, (old_val, new_val) in all_changes.items():
                    print(f"    {field_name}: '{old_val}' -> '{new_val}'")
            else:
                print(f"  [ERROR] No field changes detected at all!")
                print(f"  This means the comparison logic has a bug.")
        else:
            print(f"  ❌ Unique IDs don't match - won't be compared!")
            print(f"    File 1 ID: {mapping1.unique_id}")
            print(f"    File 2 ID: {mapping2.unique_id}")
    
    return True


def debug_full_comparison():
    """Debug the full comparison to see what changes are detected."""
    print(f"\n" + "="*60)
    print("DEBUG: Full Comparison Analysis")
    print("="*60)
    
    result = compare_workbooks("STTM.xlsx", "STTM2.xlsx")
    
    target_tab = "NetSuiteVendorRequestResponsOTV"
    if target_tab in result.tab_comparisons:
        tab_comparison = result.tab_comparisons[target_tab]
        
        print(f"Tab '{target_tab}' comparison results:")
        print(f"  Added mappings: {len(tab_comparison.added_mappings)}")
        print(f"  Deleted mappings: {len(tab_comparison.deleted_mappings)}")
        print(f"  Modified mappings: {len(tab_comparison.modified_mappings)}")
        
        if tab_comparison.modified_mappings:
            print(f"\nModified mappings details:")
            for i, change in enumerate(tab_comparison.modified_mappings):
                print(f"  Change {i+1}:")
                print(f"    Target: '{change.mapping.target_canonical}' | '{change.mapping.target_field}'")
                print(f"    Change type: {change.change_type}")
                print(f"    Field changes: {len(change.field_changes)}")
                for field_name, change_info in change.field_changes.items():
                    print(f"      {field_name}: '{change_info['old']}' -> '{change_info['new']}'")


if __name__ == "__main__":
    print("Row 13 Comment Change Debug Script")
    print("="*60)
    
    # Check files exist
    for filename in ["STTM.xlsx", "STTM2.xlsx"]:
        if not Path(filename).exists():
            print(f"ERROR: {filename} not found!")
            exit(1)
    
    success1 = debug_specific_row()
    if success1:
        debug_full_comparison()
    
    print(f"\nDebug analysis complete!")