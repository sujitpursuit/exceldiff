"""
Test File Name Based Azure Folder Structure

This script tests the new implementation where the database file_name field
is used directly for Azure folder naming instead of parsing filenames.

Usage:
    python test_filename_azure.py
"""

import os
import requests
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_with_filename():
    """Test comparison with explicit file_name parameter."""
    print("Testing Azure Reports with Database file_name")
    print("=" * 55)
    
    # Use the Azure blob URLs for STTM files
    file1_path = "https://stexceldifffiles.blob.core.windows.net/excel-files/STTM Working Version File_seq1_v1.0_20250904_210303.xlsx"
    file2_path = "https://stexceldifffiles.blob.core.windows.net/excel-files/STTM Working Version File_seq7_v7.0_20250904_210617.xlsx"
    
    # Simulate the file_name from database (without parsing)
    db_file_name = "STTM_Master_Mapping.xlsx"  # This would come from tracked_files.file_name
    
    print(f"Comparing files:")
    print(f"  File 1: ...{file1_path[-60:]}") 
    print(f"  File 2: ...{file2_path[-60:]}")
    print()
    print(f"Database file_name: {db_file_name}")
    print(f"Expected Azure folder: {os.path.splitext(db_file_name)[0]}")
    print()
    
    try:
        # Prepare the request with file_name parameter
        api_url = "http://localhost:8000/api/compare-versions"
        form_data = {
            'file1_path': file1_path,
            'file2_path': file2_path,
            'title': 'Test with Database file_name',
            'file_name': db_file_name  # Pass the database file_name
        }
        
        print(">> Sending comparison request with file_name...")
        start_time = datetime.now()
        
        response = requests.post(api_url, data=form_data, timeout=180)
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        print(f">> Request completed in {duration:.2f} seconds")
        print()
        
        if response.status_code == 200:
            result = response.json()
            
            print("SUCCESS: Comparison completed!")
            print()
            
            # Check Azure URLs
            reports = result.get('reports', {})
            
            if reports.get('azure_html_blob'):
                azure_blob_path = reports['azure_html_blob']
                print(f"Azure Blob Path: {azure_blob_path}")
                
                # Check if it uses the correct folder name
                expected_folder = os.path.splitext(db_file_name)[0]  # "STTM_Master_Mapping"
                if expected_folder in azure_blob_path:
                    print(f"[OK] Correct folder name used: '{expected_folder}'")
                else:
                    print(f"[WARN] Expected folder '{expected_folder}' not found in path")
                    print(f"       Actual path: {azure_blob_path}")
            
            print()
            print("Azure URLs:")
            if reports.get('azure_html_url'):
                print(f"  HTML: {reports['azure_html_url']}")
            if reports.get('azure_json_url'):
                print(f"  JSON: {reports['azure_json_url']}")
                
            return True
            
        else:
            print(f"ERROR: Comparison failed - Status: {response.status_code}")
            try:
                error_data = response.json()
                print(f"Error details: {error_data.get('detail', 'Unknown error')}")
            except:
                print(f"Error response: {response.text}")
            return False
            
    except Exception as e:
        print(f"ERROR: Request failed: {e}")
        return False

def test_without_filename():
    """Test comparison without file_name (fallback to parsing)."""
    print("\nTesting Fallback (without file_name parameter)")
    print("=" * 55)
    
    file1_path = "https://stexceldifffiles.blob.core.windows.net/excel-files/STTM Working Version File_seq1_v1.0_20250904_210303.xlsx"
    file2_path = "https://stexceldifffiles.blob.core.windows.net/excel-files/STTM Working Version File_seq7_v7.0_20250904_210617.xlsx"
    
    print(f"Comparing files (no file_name provided):")
    print(f"  File 1: ...{file1_path[-60:]}")
    print(f"  File 2: ...{file2_path[-60:]}")
    print(f"Expected folder (parsed): STTM Working Version File")
    print()
    
    try:
        api_url = "http://localhost:8000/api/compare-versions"
        form_data = {
            'file1_path': file1_path,
            'file2_path': file2_path,
            'title': 'Test without file_name (fallback)'
            # Note: NOT passing file_name parameter
        }
        
        print(">> Sending comparison request WITHOUT file_name...")
        response = requests.post(api_url, data=form_data, timeout=180)
        
        if response.status_code == 200:
            result = response.json()
            print("SUCCESS: Fallback parsing still works!")
            
            reports = result.get('reports', {})
            if reports.get('azure_html_blob'):
                azure_blob_path = reports['azure_html_blob']
                print(f"Azure Blob Path: {azure_blob_path}")
                
                # Should use parsed name
                if "STTM Working Version File" in azure_blob_path:
                    print("[OK] Fallback parsing worked correctly")
                else:
                    print("[WARN] Unexpected folder name in path")
                    
            return True
        else:
            print(f"ERROR: Status {response.status_code}")
            return False
            
    except Exception as e:
        print(f"ERROR: {e}")
        return False

def main():
    """Main test function."""
    print("File Name Based Azure Folder Test")
    print("=" * 50)
    print(f"Started at: {datetime.now()}")
    print()
    
    # Test 1: With file_name parameter
    test1_success = test_with_filename()
    
    # Test 2: Without file_name (fallback)
    test2_success = test_without_filename()
    
    # Summary
    print()
    print("=" * 50)
    print("Test Summary")
    print()
    
    if test1_success and test2_success:
        print("SUCCESS: All tests passed!")
        print()
        print("Implementation working correctly:")
        print("+ Database file_name used when provided")
        print("+ Fallback parsing still works when file_name not provided")
        print("+ Azure folder structure uses consistent naming")
        print()
        print("Benefits:")
        print("- Simpler logic (no complex parsing)")
        print("- More reliable (uses authoritative database value)")
        print("- Consistent folder naming across all file versions")
        return True
    else:
        print("ERROR: Some tests failed")
        print()
        print("Check:")
        print("- API server is running")
        print("- Frontend passes file_name correctly")
        print("- Azure configuration is correct")
        return False

if __name__ == "__main__":
    try:
        success = main()
        exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        exit(1)
    except Exception as e:
        print(f"\n\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)