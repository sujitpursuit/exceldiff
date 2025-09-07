"""
Simple Azure Blob Files Test

This script lists and tests access to the uploaded Excel files in Azure Blob Storage.
It will verify that the STTM files you uploaded are accessible and ready for comparison.

Usage:
    python test_blob_files.py
"""

import os
from datetime import datetime
from azure.storage.blob import BlobServiceClient
from azure.core.exceptions import AzureError
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def format_file_size(size_bytes):
    """Convert bytes to human readable format."""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.2f} {size_names[i]}"

def test_blob_access():
    """Test access to Azure blob storage and list uploaded files."""
    print("Testing Azure Blob Storage Access")
    print("=" * 50)
    
    # Get connection info
    connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    container_name = os.getenv("AZURE_STORAGE_CONTAINER_NAME", "excel-files")
    
    if not connection_string:
        print("ERROR: AZURE_STORAGE_CONNECTION_STRING not found in environment")
        print("   Make sure your .env file contains the connection string")
        return False
    
    print(f"Container: {container_name}")
    print(f"Test time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    try:
        # Connect to Azure
        blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        container_client = blob_service_client.get_container_client(container_name)
        
        # Check if container exists
        if not container_client.exists():
            print(f"ERROR: Container '{container_name}' does not exist")
            return False
        
        print("SUCCESS: Successfully connected to Azure Blob Storage")
        print()
        
        # List all blobs in container
        print("Files in container:")
        print("-" * 50)
        
        blobs = list(container_client.list_blobs())
        
        if not blobs:
            print("WARNING: No files found in container")
            return False
        
        # Display each blob with details
        sttm_files = []
        for i, blob in enumerate(blobs, 1):
            print(f"{i}. {blob.name}")
            print(f"   Size: {format_file_size(blob.size)}")
            print(f"   Last Modified: {blob.last_modified}")
            print(f"   Content Type: {blob.content_settings.content_type if blob.content_settings else 'Unknown'}")
            
            # Check if it's an STTM file
            if 'STTM' in blob.name and blob.name.endswith('.xlsx'):
                sttm_files.append(blob)
            
            print()
        
        print(f"Summary:")
        print(f"   Total files: {len(blobs)}")
        print(f"   STTM Excel files: {len(sttm_files)}")
        print()
        
        # Test specific STTM files access
        if sttm_files:
            print("Testing STTM Files Access:")
            print("-" * 50)
            
            for sttm_file in sttm_files:
                print(f"Testing: {sttm_file.name}")
                
                try:
                    # Get blob client
                    blob_client = container_client.get_blob_client(sttm_file.name)
                    
                    # Test if we can get properties (lightweight operation)
                    properties = blob_client.get_blob_properties()
                    
                    print(f"SUCCESS: Accessible - Size: {format_file_size(properties.size)}")
                    
                    # Test download capability (just first few bytes)
                    try:
                        # Download just the first 1024 bytes to test download capability
                        stream = blob_client.download_blob(offset=0, length=1024)
                        data = stream.readall()
                        
                        if len(data) > 0:
                            print(f"SUCCESS: Download test successful - Read {len(data)} bytes")
                        else:
                            print("WARNING: File appears to be empty")
                            
                    except Exception as e:
                        print(f"ERROR: Download test failed: {str(e)}")
                        
                except Exception as e:
                    print(f"ERROR: Access test failed: {str(e)}")
                
                print()
        
        # Check for the specific files mentioned
        expected_files = [
            "STTM Working Version File_seq1_v1.0_20250904_210303.xlsx",
            "STTM Working Version File_seq7_v7.0_20250904_210617.xlsx"
        ]
        
        print("Checking for expected files:")
        print("-" * 50)
        
        found_files = [blob.name for blob in blobs]
        
        for expected_file in expected_files:
            if expected_file in found_files:
                print(f"FOUND: {expected_file}")
            else:
                print(f"MISSING: {expected_file}")
                
                # Try to find similar files
                similar = [f for f in found_files if 'STTM' in f and any(part in f for part in expected_file.split('_')[:3])]
                if similar:
                    print(f"   Similar files found: {similar}")
        
        print()
        
        # Final assessment
        if len(sttm_files) >= 2:
            print("SUCCESS: Azure Blob Storage is working correctly!")
            print("Multiple STTM files found and accessible")
            print("Ready to integrate with comparison API")
            return True
        elif len(sttm_files) == 1:
            print("PARTIAL: Only 1 STTM file found")
            print("   You need at least 2 files to test comparison")
            return False
        else:
            print("ISSUE: No STTM Excel files found")
            print("   Please upload STTM Excel files to the container")
            return False
            
    except AzureError as e:
        print(f"AZURE ERROR: {str(e)}")
        return False
    except Exception as e:
        print(f"UNEXPECTED ERROR: {str(e)}")
        return False

if __name__ == "__main__":
    print("Azure Blob Files Test")
    print("=" * 50)
    
    success = test_blob_access()
    
    print("\n" + "=" * 50)
    if success:
        print("SUCCESS: Test completed successfully!")
        print("Next step: Integrate Azure storage into the comparison API")
    else:
        print("WARNING: Test found issues that need to be resolved")
        print("Please check the errors above and try again")