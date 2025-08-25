#!/usr/bin/env python3
"""
Test script to verify that original column names are preserved
"""

from excel_analyzer import analyze_workbook

def test_preserved_column_names():
    print("Testing Preserved Column Names")
    print("="*40)
    
    try:
        # Analyze the workbook
        workbook_analysis = analyze_workbook("STTM.xlsx")
        
        # Get NetSuiteVendorRequestResponsOTV tab
        target_tab = "NetSuiteVendorRequestResponsOTV"
        if target_tab not in workbook_analysis:
            print(f"ERROR: Tab '{target_tab}' not found")
            return
        
        tab_analysis = workbook_analysis[target_tab]
        
        # Find our specific mapping (row 13, target: NetSuite Vendor Work Item | SourceSystem)
        target_mapping = None
        for mapping in tab_analysis.mappings:
            if (mapping.target_canonical == "NetSuite Vendor Work Item" and 
                mapping.target_field == "SourceSystem" and
                mapping.row_number == 13):
                target_mapping = mapping
                break
        
        if target_mapping:
            print(f"Found target mapping (Row {target_mapping.row_number}):")
            print(f"  Target: {target_mapping.target_canonical} | {target_mapping.target_field}")
            print(f"  All fields count: {len(target_mapping.all_fields)}")
            
            print(f"\nAll field keys (showing preserved column names):")
            for key in sorted(target_mapping.all_fields.keys()):
                value = target_mapping.all_fields[key]
                if value:  # Only show non-empty fields
                    print(f"  {key}: '{value}'")
            
            # Check specifically for Comments field
            comments_fields = [key for key in target_mapping.all_fields.keys() if 'comment' in key.lower()]
            if comments_fields:
                print(f"\nComments fields found:")
                for key in comments_fields:
                    value = target_mapping.all_fields[key]
                    print(f"  {key}: '{value}'")
            else:
                print(f"\nNo Comments fields found!")
                print("Available target fields:")
                target_fields = [key for key in target_mapping.all_fields.keys() if key.startswith('target_')]
                for key in target_fields:
                    print(f"  {key}")
                    
        else:
            print("Target mapping not found!")
            print("Available mappings:")
            for i, mapping in enumerate(tab_analysis.mappings[:5]):  # Show first 5
                print(f"  {i+1}: Row {mapping.row_number} - {mapping.target_canonical} | {mapping.target_field}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_preserved_column_names()