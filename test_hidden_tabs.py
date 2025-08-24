"""
Test script to test processing hidden tabs

This script temporarily changes the config to process hidden tabs
and shows the difference in results.
"""

import logging
from excel_analyzer import analyze_workbook
import config

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_with_hidden_tabs():
    """Test analyzing with hidden tabs enabled."""
    print("=" * 60)
    print("Testing with PROCESS_HIDDEN_TABS = True")
    print("=" * 60)
    
    # Temporarily change config to process hidden tabs
    original_process_hidden = config.PROCESS_HIDDEN_TABS
    config.PROCESS_HIDDEN_TABS = True
    
    try:
        file_path = "STTM.xlsx"
        results = analyze_workbook(file_path)
        
        print(f"\nAnalysis Results for '{file_path}' (Processing Hidden Tabs):")
        print("-" * 50)
        
        total_mappings = 0
        valid_tabs = []
        hidden_tabs_processed = []
        skipped_tabs = []
        
        for tab_name, analysis in results.items():
            if analysis.errors:
                if any("skipped" in error.lower() for error in analysis.errors):
                    skipped_tabs.append(tab_name)
                    if any("hidden" in error.lower() for error in analysis.errors):
                        print(f"\nTAB: {tab_name} [HIDDEN - SKIPPED]")
                    else:
                        print(f"\nTAB: {tab_name} [SKIPPED]")
                    for error in analysis.errors:
                        print(f"  SKIP REASON: {error}")
                continue
                
            valid_tabs.append(tab_name)
            
            # Check if this tab was hidden but processed
            try:
                import openpyxl
                wb = openpyxl.load_workbook(file_path, data_only=True)
                sheet = wb[tab_name]
                is_hidden = sheet.sheet_state != 'visible'
                if is_hidden:
                    hidden_tabs_processed.append(tab_name)
                    print(f"\nTAB: {tab_name} [HIDDEN - PROCESSED]")
                else:
                    print(f"\nTAB: {tab_name}")
            except:
                print(f"\nTAB: {tab_name}")
                
            print(f"  Source System: {analysis.metadata.source_system}")
            print(f"  Target System: {analysis.metadata.target_system}")
            print(f"  Mappings Found: {analysis.mapping_count}")
            
            total_mappings += analysis.mapping_count
        
        print(f"\n" + "=" * 60)
        print(f"SUMMARY (With Hidden Tab Processing):")
        print(f"  Total Tabs in File: {len(results)}")
        print(f"  Valid Tabs Analyzed: {len(valid_tabs)}")
        print(f"  Hidden Tabs Processed: {len(hidden_tabs_processed)}")
        print(f"  Tabs Skipped: {len(skipped_tabs)}")
        print(f"  Total Mappings Found: {total_mappings}")
        
        if hidden_tabs_processed:
            print(f"\nHidden tabs that were processed:")
            for tab in hidden_tabs_processed:
                print(f"  - {tab}")
        
    finally:
        # Restore original config
        config.PROCESS_HIDDEN_TABS = original_process_hidden

def test_without_hidden_tabs():
    """Test analyzing with hidden tabs disabled (default behavior)."""
    print("\n" + "=" * 60)
    print("Testing with PROCESS_HIDDEN_TABS = False (Default)")
    print("=" * 60)
    
    file_path = "STTM.xlsx"
    results = analyze_workbook(file_path)
    
    valid_tabs = []
    hidden_skipped = []
    other_skipped = []
    
    for tab_name, analysis in results.items():
        if analysis.errors:
            if any("hidden" in error.lower() for error in analysis.errors):
                hidden_skipped.append(tab_name)
            elif any("skipped" in error.lower() for error in analysis.errors):
                other_skipped.append(tab_name)
        else:
            valid_tabs.append(tab_name)
    
    total_mappings = sum(analysis.mapping_count for analysis in results.values() if not analysis.errors)
    
    print(f"\nSUMMARY (Default - Skip Hidden Tabs):")
    print(f"  Total Tabs in File: {len(results)}")
    print(f"  Valid Tabs Analyzed: {len(valid_tabs)}")
    print(f"  Hidden Tabs Skipped: {len(hidden_skipped)}")
    print(f"  Other Tabs Skipped: {len(other_skipped)}")
    print(f"  Total Mappings Found: {total_mappings}")

if __name__ == "__main__":
    test_without_hidden_tabs()
    test_with_hidden_tabs()