"""
Test script for Phase 1 modules

This script tests the core data extraction functionality using the sample STTM.xlsx file.
"""

import logging
import json
from excel_analyzer import analyze_workbook

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_analyze_sample_file():
    """Test analyzing the sample STTM.xlsx file."""
    print("=" * 60)
    print("Testing Phase 1: Excel Analysis Module")
    print("=" * 60)
    
    file_path = "STTM.xlsx"
    
    try:
        # Analyze the workbook
        results = analyze_workbook(file_path)
        
        print(f"\nAnalysis Results for '{file_path}':")
        print("-" * 40)
        
        total_mappings = 0
        
        for tab_name, analysis in results.items():
            if analysis.errors:
                # Check if it's a skipped tab vs actual error
                if any("skipped" in error.lower() for error in analysis.errors):
                    # Check specific skip reasons
                    if any("hidden" in error.lower() for error in analysis.errors):
                        print(f"\nTAB: {tab_name} [HIDDEN - SKIPPED]")
                    else:
                        print(f"\nTAB: {tab_name} [SKIPPED]")
                    for error in analysis.errors:
                        print(f"  SKIP REASON: {error}")
                else:
                    print(f"\nTAB: {tab_name} [ERRORS]")
                    for error in analysis.errors:
                        print(f"  ERROR: {error}")
                continue
                
            print(f"\nTAB: {tab_name}")
            print(f"  Source System: {analysis.metadata.source_system}")
            print(f"  Target System: {analysis.metadata.target_system}")
            print(f"  Mappings Found: {analysis.mapping_count}")
            print(f"  Total Rows: {analysis.metadata.max_row}")
            print(f"  Total Columns: {analysis.metadata.max_column}")
            
            # Show column mapping
            if analysis.column_mapping.source_columns or analysis.column_mapping.target_columns:
                print(f"  Source Columns: {list(analysis.column_mapping.source_columns.keys())}")
                print(f"  Target Columns: {list(analysis.column_mapping.target_columns.keys())}")
            
            # Show sample mappings
            if analysis.mappings:
                print(f"  Sample Mappings:")
                for i, mapping in enumerate(analysis.mappings[:3]):  # Show first 3
                    print(f"    {i+1}. {mapping.source_canonical}|{mapping.source_field} -> "
                          f"{mapping.target_canonical}|{mapping.target_field}")
                    print(f"       ID: {mapping.unique_id}")
                
                if len(analysis.mappings) > 3:
                    print(f"    ... and {len(analysis.mappings) - 3} more")
            
            total_mappings += analysis.mapping_count
        
        print(f"\n" + "=" * 60)
        valid_tabs = [r for r in results.values() if not r.errors]
        skipped_tabs = [r for r in results.values() if r.errors and any("skipped" in error.lower() for error in r.errors)]
        error_tabs = [r for r in results.values() if r.errors and not any("skipped" in error.lower() for error in r.errors)]
        
        print(f"SUMMARY:")
        print(f"  Total Tabs in File: {len(results)}")
        print(f"  Valid Tabs Analyzed: {len(valid_tabs)}")
        print(f"  Tabs Skipped (Invalid Structure): {len(skipped_tabs)}")
        print(f"  Tabs with Errors: {len(error_tabs)}")
        print(f"  Total Mappings Found: {total_mappings}")
        
        # Test specific functionality
        test_data_models(results)
        
    except Exception as e:
        print(f"ERROR: Failed to analyze file: {e}")
        import traceback
        traceback.print_exc()


def test_data_models(results):
    """Test data model functionality."""
    print(f"\n" + "-" * 40)
    print("Testing Data Model Functions:")
    print("-" * 40)
    
    for tab_name, analysis in results.items():
        if analysis.errors or not analysis.mappings:
            continue
            
        mapping = analysis.mappings[0]  # Test with first mapping
        
        print(f"\nTesting mapping from tab '{tab_name}':")
        print(f"  Original ID: {mapping.unique_id}")
        print(f"  Is Valid: {mapping.is_valid()}")
        print(f"  All Fields Count: {len(mapping.all_fields)}")
        
        # Test unique ID generation
        new_id = mapping.generate_unique_id()
        print(f"  Regenerated ID: {new_id}")
        print(f"  IDs Match: {mapping.unique_id == new_id}")
        
        # Show some field data
        if mapping.all_fields:
            print(f"  Sample Fields:")
            for key, value in list(mapping.all_fields.items())[:5]:
                display_value = str(value)[:50] + "..." if len(str(value)) > 50 else str(value)
                print(f"    {key}: {display_value}")
        
        break  # Test with just one mapping


if __name__ == "__main__":
    test_analyze_sample_file()