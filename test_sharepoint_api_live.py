"""
Live test of SharePoint API endpoints with real data
"""

import requests
import json
import time
import subprocess
import sys
from api import db_manager

def test_live_sharepoint_api():
    """Test SharePoint API endpoints with real migrated data."""
    
    print("SharePoint API Live Testing")
    print("=" * 50)
    
    # Get some real version data
    try:
        result = db_manager.get_file_versions(
            'https://pursuitsoftwarebiz-my.sharepoint.com/:x:/g/personal/sujit_s_pursuitsoftware_biz/EQ-MT6NYQZxBuFUGvrpU5VABE4G5Gbmsvvci9J45TLCywQ?e=FlEJry', 
            'url'
        )
        
        print(f"Found file: {result['file_info']['friendly_name']}")
        print(f"Total versions: {result['file_info']['total_versions']}")
        
        # Find a version that needs downloading
        version_to_test = None
        for version in result['versions']:
            if not version['downloaded']:
                version_to_test = version
                break
        
        if not version_to_test:
            version_to_test = result['versions'][0]  # Use first version anyway
        
        print(f"Testing with version {version_to_test['sequence_number']} (ID: {version_to_test['version_id']})")
        
        # Start API server
        print("\\nStarting API server...")
        server = subprocess.Popen([
            sys.executable, '-m', 'uvicorn', 'api:app',
            '--host', '127.0.0.1', '--port', '8001'
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        # Wait for server to start
        time.sleep(5)
        
        try:
            # Test 1: Health check
            print("1. Testing health endpoint...")
            response = requests.get('http://127.0.0.1:8001/api/health', timeout=10)
            print(f"   Health check: {response.status_code} - {response.json().get('status', 'unknown')}")
            
            # Test 2: Get version status
            print("2. Testing get-version-status endpoint...")
            response = requests.get(f'http://127.0.0.1:8001/api/get-version-status?version_id={version_to_test["version_id"]}', timeout=10)
            if response.status_code == 200:
                status_data = response.json()
                print(f"   Version status: Downloaded={status_data['download_status']['downloaded']}, Local exists={status_data['download_status']['local_file_exists']}")
                needs_download = status_data['download_status']['needs_download']
                print(f"   Needs download: {needs_download}")
            else:
                print(f"   Status check failed: {response.status_code} - {response.text}")
                
            # Test 3: Download SharePoint version
            print("3. Testing download-sharepoint-version endpoint...")
            download_data = {
                'version_id': version_to_test['version_id'],
                'force_download': False
            }
            response = requests.post('http://127.0.0.1:8001/api/download-sharepoint-version', data=download_data, timeout=30)
            
            if response.status_code == 200:
                download_result = response.json()
                print(f"   Download status: {download_result.get('download_status')}")
                if download_result.get('download_status') == 'success':
                    print(f"   File size: {download_result.get('local_storage', {}).get('file_size', 0)} bytes")
                    print(f"   Local path: {download_result.get('local_storage', {}).get('local_path', 'N/A')}")
                    print(f"   From cache: {download_result.get('local_storage', {}).get('from_cache', False)}")
                else:
                    print(f"   Download error: {download_result.get('error', 'Unknown error')}")
            else:
                print(f"   Download failed: {response.status_code} - {response.text}")
            
            # Test 4: Test version comparison if we have multiple versions
            if len(result['versions']) >= 2:
                print("4. Testing compare-sharepoint-versions endpoint...")
                version1 = result['versions'][0]
                version2 = result['versions'][1]
                
                compare_data = {
                    'version1_id': version1['version_id'],
                    'version2_id': version2['version_id'],
                    'title': f'Test Comparison: v{version1["sequence_number"]} vs v{version2["sequence_number"]}'
                }
                
                # This might take longer, so increase timeout
                response = requests.post('http://127.0.0.1:8001/api/compare-sharepoint-versions', data=compare_data, timeout=60)
                
                if response.status_code == 200:
                    compare_result = response.json()
                    print(f"   Comparison status: {compare_result.get('status')}")
                    if compare_result.get('status') == 'success':
                        summary = compare_result.get('comparison_summary', {})
                        print(f"   Total changes: {summary.get('total_changes', 0)}")
                        print(f"   Report HTML: {compare_result.get('reports', {}).get('html_url', 'N/A')}")
                else:
                    print(f"   Comparison failed: {response.status_code} - {response.text}")
            else:
                print("4. Skipping comparison test (need at least 2 versions)")
            
            print("\\n" + "=" * 50)
            print("Live API testing completed!")
            
        finally:
            # Cleanup
            print("Stopping server...")
            server.terminate()
            server.wait(timeout=5)
            
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    success = test_live_sharepoint_api()
    sys.exit(0 if success else 1)