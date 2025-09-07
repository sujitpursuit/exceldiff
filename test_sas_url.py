"""
Test SAS URL Access

This script tests that the generated SAS URLs are accessible.
"""

import requests

def test_sas_url():
    # Use one of the generated SAS URLs from the test
    sas_url = "https://stexceldifffiles.blob.core.windows.net/diff-reports/STTM_Master_Mapping/comparison_azure_excel_i07avf7f_vs_azure_excel_uc4vpvc4_20250906_221558.html?se=2025-09-14T02%3A15%3A59Z&sp=r&sv=2025-07-05&sr=b&sig=hBvvv3G4LaeSQppkb8f15%2B5exnK6DNqvt983K9JtCZE%3D"
    
    print("Testing SAS URL access...")
    print(f"URL: {sas_url[:100]}...")
    
    try:
        response = requests.head(sas_url, timeout=10)
        
        if response.status_code == 200:
            print(f"SUCCESS: SAS URL is accessible (Status: {response.status_code})")
            print(f"Content-Type: {response.headers.get('Content-Type', 'Not specified')}")
            print(f"Content-Length: {response.headers.get('Content-Length', 'Not specified')} bytes")
            return True
        else:
            print(f"ERROR: Cannot access SAS URL (Status: {response.status_code})")
            return False
            
    except Exception as e:
        print(f"ERROR: Failed to access SAS URL: {e}")
        return False

if __name__ == "__main__":
    test_sas_url()