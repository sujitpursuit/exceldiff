#!/usr/bin/env python3
"""
Excel Comparison Tool - Standalone Version

Compare two Excel workbooks and show differences in Source-Target mappings.

Usage: python compare_excel.py file1.xlsx file2.xlsx
"""

import sys
import os
import logging
from pathlib import Path
from datetime import datetime
from comparator import compare_workbooks
from utils import validate_file_path
from report_generator import generate_html_report
import config

def main():
    """Main entry point for the comparison tool."""
    
    # Check command line arguments
    if len(sys.argv) != 3:
        print("Excel Source-Target Mapping Comparison Tool")
        print("=" * 50)
        print("Usage: python compare_excel.py file1.xlsx file2.xlsx")
        print("\nCompares two Excel workbooks and shows differences in")
        print("Source-Target mapping data between the files.")
        print("\nExamples:")
        print("  python compare_excel.py original.xlsx modified.xlsx")
        print("  python compare_excel.py old_version.xlsx new_version.xlsx")
        sys.exit(1)
    
    file1, file2 = sys.argv[1], sys.argv[2]
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("Excel Source-Target Mapping Comparison Tool")
    print("=" * 50)
    print(f"Comparing: {file1}")
    print(f"     vs:   {file2}")
    print("=" * 50)
    
    # Validate files
    print("Validating input files...")
    for i, file_path in enumerate([file1, file2], 1):
        is_valid, error = validate_file_path(file_path)
        if not is_valid:
            print(f"ERROR: File {i} validation failed: {error}")
            sys.exit(1)
        else:
            print(f"  File {i}: {Path(file_path).name} - OK")
    
    print("\nStarting comparison...")
    
    # Run comparison
    result = compare_workbooks(file1, file2)
    
    if result.has_errors:
        print("\nCOMPARISON ERRORS:")
        for error in result.errors:
            print(f"  - {error}")
        sys.exit(1)
    
    print("\nComparison completed successfully!")
    
    # Display results
    print("\n" + "=" * 50)
    print("COMPARISON RESULTS")
    print("=" * 50)
    
    print(f"Files compared: 2")
    print(f"Tabs in file 1: {result.summary.total_tabs_v1}")
    print(f"Tabs in file 2: {result.summary.total_tabs_v2}")
    print(f"Total mappings in file 1: {result.summary.total_mappings_v1}")
    print(f"Total mappings in file 2: {result.summary.total_mappings_v2}")
    
    # Show change summary
    print("\nTAB CHANGES:")
    print(f"  Added: {result.summary.tabs_added}")
    print(f"  Deleted: {result.summary.tabs_deleted}")
    print(f"  Modified: {result.summary.tabs_modified}")
    print(f"  Unchanged: {result.summary.tabs_unchanged}")
    
    print("\nMAPPING CHANGES:")
    print(f"  Added: {result.summary.total_mappings_added}")
    print(f"  Deleted: {result.summary.total_mappings_deleted}")
    print(f"  Modified: {result.summary.total_mappings_modified}")
    
    # Calculate total changes
    total_changes = (result.summary.tabs_added + result.summary.tabs_deleted + 
                    result.summary.tabs_modified + result.summary.total_mappings_added +
                    result.summary.total_mappings_deleted + result.summary.total_mappings_modified)
    
    if total_changes > 0:
        print(f"\nCHANGED TABS DETAIL:")
        changed_tabs = [name for name, comp in result.tab_comparisons.items() if comp.has_changes]
        if changed_tabs:
            for tab_name in changed_tabs:
                comparison = result.tab_comparisons[tab_name]
                changes = comparison.change_summary
                status_desc = []
                if changes['added'] > 0:
                    status_desc.append(f"+{changes['added']} added")
                if changes['deleted'] > 0:
                    status_desc.append(f"-{changes['deleted']} deleted")
                if changes['modified'] > 0:
                    status_desc.append(f"~{changes['modified']} modified")
                
                print(f"  {tab_name}: {', '.join(status_desc)}")
        else:
            print("  None")
            
        print(f"\nSUMMARY: {total_changes} total changes detected")
    else:
        print(f"\nSUMMARY: No changes detected - files are identical")
    
    print("=" * 50)
    
    # Generate HTML report
    print("\nGenerating HTML report...")
    
    # Create report filename with timestamp using config settings
    timestamp = datetime.now().strftime(config.REPORT_TIMESTAMP_FORMAT)
    file1_name = Path(file1).stem
    file2_name = Path(file2).stem
    
    # Use config template for filename
    if config.INCLUDE_TIMESTAMP_IN_FILENAME:
        report_filename = config.REPORT_FILENAME_TEMPLATE.format(
            file1=file1_name, 
            file2=file2_name, 
            timestamp=timestamp
        )
    else:
        report_filename = f"comparison_{file1_name}_vs_{file2_name}.html"
    
    # Use config directories - sample reports for standalone usage
    report_path = os.path.join(config.REPORTS_BASE_DIR, config.SAMPLE_REPORTS_DIR, report_filename)
    
    # Generate report title using config template
    report_title = config.REPORT_TITLE_TEMPLATE.format(
        file1=Path(file1).name,
        file2=Path(file2).name
    )
    
    # Generate the HTML report
    success = generate_html_report(result, report_path, report_title)
    
    if success:
        print(f"HTML report generated successfully: {report_path}")
        print(f"Open the file in your browser to view the detailed comparison report.")
    else:
        print("ERROR: Failed to generate HTML report")
        return 1
    
    print("\nComparison completed successfully!")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())