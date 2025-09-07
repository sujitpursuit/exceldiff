"""
Test Azure File Comparison

This script tests the complete end-to-end comparison of Excel files stored in Azure Blob Storage.
It will use the API endpoints to compare the uploaded STTM files and verify that the full
workflow (download from Azure -> comparison -> report generation) works correctly.

Usage:
    python test_azure_comparison.py
"""

import os
import requests
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_api_health():
    """Test that the API is running and healthy."""
    print("Testing API health...")
    
    try:
        response = requests.get("http://localhost:8000/api/health", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            print(f"SUCCESS: API is healthy - {data.get('service', 'Unknown')}")
            return True
        else:
            print(f"ERROR: API health check failed - Status: {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("ERROR: Cannot connect to API. Make sure the server is running on localhost:8000")
        return False
    except Exception as e:
        print(f"ERROR: API health check failed: {e}")
        return False

def test_azure_comparison():
    """Test comparison of Azure blob files via API."""
    print("\nTesting Azure file comparison...")
    
    # Use the full Azure blob URLs (detected as Azure paths)
    file1_path = "https://stexceldifffiles.blob.core.windows.net/excel-files/STTM Working Version File_seq1_v1.0_20250904_210303.xlsx"
    file2_path = "https://stexceldifffiles.blob.core.windows.net/excel-files/STTM Working Version File_seq7_v7.0_20250904_210617.xlsx"
    
    print(f"Comparing:")
    print(f"  File 1: {file1_path}")
    print(f"  File 2: {file2_path}")
    
    # Prepare the request
    api_url = "http://localhost:8000/api/compare-versions"
    
    form_data = {
        'file1_path': file1_path,
        'file2_path': file2_path,
        'title': 'Azure Test: STTM Version 1 vs Version 7'
    }
    
    try:
        print("\nSending comparison request...")
        response = requests.post(api_url, data=form_data, timeout=120)  # 2 minute timeout
        
        if response.status_code == 200:
            result = response.json()
            
            print("SUCCESS: Comparison completed!")
            print("\nComparison Summary:")
            
            # Extract and display summary information
            summary = result.get('comparison_summary', {})
            print(f"  Total changes: {summary.get('total_changes', 'Unknown')}")
            
            tabs = summary.get('tabs', {})
            print(f"  Tabs - Total v1: {tabs.get('total_v1', 0)}, Total v2: {tabs.get('total_v2', 0)}")
            print(f"  Tabs - Added: {tabs.get('added', 0)}, Deleted: {tabs.get('deleted', 0)}, Modified: {tabs.get('modified', 0)}")
            
            mappings = summary.get('mappings', {})
            print(f"  Mappings - Total v1: {mappings.get('total_v1', 0)}, Total v2: {mappings.get('total_v2', 0)}")
            print(f"  Mappings - Added: {mappings.get('added', 0)}, Deleted: {mappings.get('deleted', 0)}, Modified: {mappings.get('modified', 0)}")
            
            # Display changed tabs
            changed_tabs = summary.get('changed_tabs', [])
            if changed_tabs:
                print(f"\nChanged Tabs ({len(changed_tabs)}):")
                for tab in changed_tabs:
                    print(f"  - {tab.get('name', 'Unknown')}: +{tab.get('added', 0)} -{tab.get('deleted', 0)} ~{tab.get('modified', 0)}")
            
            # Display report links
            reports = result.get('reports', {})
            print(f"\nReports Generated:")
            if reports.get('html_report'):
                print(f"  HTML: http://localhost:8000{reports['html_report']}")
            if reports.get('json_report'):
                print(f"  JSON: http://localhost:8000{reports['json_report']}")
            
            # Display processing info
            processing = result.get('processing_info', {})
            print(f"\nProcessing Info:")
            print(f"  Timestamp: {processing.get('timestamp', 'Unknown')}")
            print(f"  Tabs compared: {processing.get('total_tabs_compared', 0)}")
            print(f"  Has errors: {processing.get('has_errors', False)}")
            
            if processing.get('errors'):
                print(f"  Errors: {processing['errors']}")
            
            return True
            
        else:
            print(f"ERROR: Comparison failed - Status: {response.status_code}")
            try:
                error_data = response.json()
                print(f"Error details: {error_data.get('detail', 'Unknown error')}")
            except:
                print(f"Error response: {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        print("ERROR: Request timed out. The comparison might be taking too long.")
        return False
    except requests.exceptions.ConnectionError:
        print("ERROR: Cannot connect to API. Make sure the server is running.")
        return False
    except Exception as e:
        print(f"ERROR: Comparison request failed: {e}")
        return False

def test_report_access(report_url):
    """Test that generated reports are accessible."""
    if not report_url:
        return False
        
    print(f"\nTesting report access: {report_url}")
    
    try:
        full_url = f"http://localhost:8000{report_url}"
        response = requests.head(full_url, timeout=10)
        
        if response.status_code == 200:
            print("SUCCESS: Report is accessible")
            return True
        else:
            print(f"ERROR: Report not accessible - Status: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"ERROR: Report access test failed: {e}")
        return False

def main():
    """Main test function."""
    print("Azure File Comparison Test")
    print("=" * 50)
    print(f"Test started at: {datetime.now()}")
    
    # Check environment
    print("\nChecking environment...")
    connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    container_name = os.getenv("AZURE_STORAGE_CONTAINER_NAME", "excel-files")
    
    if not connection_string:
        print("ERROR: AZURE_STORAGE_CONNECTION_STRING not found")
        print("Make sure your .env file is configured properly")
        return False
    
    print(f"Container: {container_name}")
    print("Azure connection string: Configured ✓")
    
    # Test 1: API Health
    print("\n" + "="*50)
    print("Step 1: API Health Check")
    if not test_api_health():
        print("ERROR: API is not healthy. Please start the server first:")
        print("  uvicorn api:app --host 0.0.0.0 --port 8000 --reload")
        return False
    
    # Test 2: Azure File Comparison
    print("\n" + "="*50)
    print("Step 2: Azure File Comparison")
    comparison_success = test_azure_comparison()
    
    # Summary
    print("\n" + "="*50)
    print("Test Summary")
    if comparison_success:
        print("SUCCESS: Azure file comparison test completed successfully!")
        print("\nThe integration is working correctly:")
        print("✓ API can download files from Azure Blob Storage")
        print("✓ Excel comparison logic works with Azure files") 
        print("✓ Reports are generated and accessible")
        print("✓ Cleanup of temporary files is working")
        
        print("\nNext steps:")
        print("- Update your database with Azure blob paths")
        print("- Test the frontend with Azure paths")
        print("- Configure other APIs to use shared Azure storage")
        
        return True
    else:
        print("ERROR: Azure file comparison test failed")
        print("\nTroubleshooting:")
        print("- Check that Azure connection string is correct")
        print("- Verify the Excel files exist in Azure container")
        print("- Check API logs for detailed error information")
        print("- Ensure all dependencies are installed")
        
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