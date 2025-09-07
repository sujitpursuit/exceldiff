"""
Azure Blob Storage Connection Test

This script tests the connection to Azure Blob Storage and verifies that
the Excel file container is accessible. Run this after setting up your
Azure Storage Account and configuring environment variables.

Requirements:
- Azure Storage Account created
- Container named 'excel-files' created  
- AZURE_STORAGE_CONNECTION_STRING set in environment or .env file
- azure-storage-blob package installed

Usage:
    python test_azure_connection.py
"""

import os
import sys
from datetime import datetime
from azure.storage.blob import BlobServiceClient
from azure.core.exceptions import AzureError
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def print_section(title):
    """Print a section header for better readability."""
    print(f"\n{'='*50}")
    print(f" {title}")
    print('='*50)

def test_environment_variables():
    """Test that required environment variables are set."""
    print("🔍 Checking environment variables...")
    
    connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    container_name = os.getenv("AZURE_STORAGE_CONTAINER_NAME", "excel-files")
    
    if not connection_string:
        print("❌ AZURE_STORAGE_CONNECTION_STRING not found")
        print("   Please set this environment variable with your Azure Storage connection string")
        return None, None
    
    # Mask the connection string for security (show only account name)
    if "AccountName=" in connection_string:
        account_name = connection_string.split("AccountName=")[1].split(";")[0]
        print(f"✅ Connection string found for account: {account_name}")
    else:
        print("✅ Connection string found (format not recognized)")
    
    print(f"✅ Container name: {container_name}")
    
    return connection_string, container_name

def test_blob_service_connection(connection_string):
    """Test connection to Azure Blob Service."""
    print("\n🔍 Testing Azure Blob Service connection...")
    
    try:
        # Create BlobServiceClient
        blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        
        # Test connection by getting account info
        account_info = blob_service_client.get_account_information()
        print(f"✅ Connected successfully!")
        print(f"   Account kind: {account_info.get('account_kind', 'Unknown')}")
        print(f"   SKU name: {account_info.get('sku_name', 'Unknown')}")
        
        return blob_service_client
        
    except AzureError as e:
        print(f"❌ Azure connection failed: {str(e)}")
        return None
    except Exception as e:
        print(f"❌ Unexpected error connecting to Azure: {str(e)}")
        return None

def test_container_access(blob_service_client, container_name):
    """Test access to the specific container."""
    print(f"\n🔍 Testing access to container '{container_name}'...")
    
    try:
        # Get container client
        container_client = blob_service_client.get_container_client(container_name)
        
        # Check if container exists
        if container_client.exists():
            print(f"✅ Container '{container_name}' exists and is accessible")
            
            # Get container properties
            properties = container_client.get_container_properties()
            print(f"   Created: {properties.last_modified}")
            print(f"   Public access: {properties.public_access or 'Private'}")
            
            return container_client
        else:
            print(f"❌ Container '{container_name}' does not exist")
            print("   Please create this container in the Azure portal")
            return None
            
    except AzureError as e:
        print(f"❌ Error accessing container: {str(e)}")
        return None
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")
        return None

def list_containers(blob_service_client):
    """List all available containers."""
    print("\n🔍 Listing all containers in storage account...")
    
    try:
        containers = list(blob_service_client.list_containers())
        
        if containers:
            print(f"✅ Found {len(containers)} container(s):")
            for container in containers:
                print(f"   - {container.name} (modified: {container.last_modified})")
        else:
            print("⚠️  No containers found in storage account")
            
        return containers
        
    except Exception as e:
        print(f"❌ Error listing containers: {str(e)}")
        return []

def list_blobs_in_container(container_client, container_name):
    """List blobs in the Excel files container."""
    print(f"\n🔍 Listing blobs in '{container_name}' container...")
    
    try:
        blobs = list(container_client.list_blobs())
        
        if blobs:
            print(f"📁 Found {len(blobs)} file(s):")
            for blob in blobs:
                size_mb = blob.size / (1024 * 1024) if blob.size else 0
                print(f"   - {blob.name}")
                print(f"     Size: {size_mb:.2f} MB, Modified: {blob.last_modified}")
        else:
            print("📁 Container is empty (this is normal for new setup)")
            
        return blobs
        
    except Exception as e:
        print(f"❌ Error listing blobs: {str(e)}")
        return []

def test_upload_download(container_client):
    """Test uploading and downloading a small test file."""
    print("\n🔍 Testing upload/download functionality...")
    
    test_filename = "test-connection.txt"
    test_content = f"Azure Blob Storage test file created at {datetime.now()}"
    
    try:
        # Upload test file
        print("📤 Uploading test file...")
        blob_client = container_client.get_blob_client(test_filename)
        blob_client.upload_blob(test_content, overwrite=True)
        print(f"✅ Test file '{test_filename}' uploaded successfully")
        
        # Download test file
        print("📥 Downloading test file...")
        downloaded_content = blob_client.download_blob().readall().decode('utf-8')
        
        if downloaded_content == test_content:
            print("✅ Test file downloaded and content matches")
        else:
            print("❌ Downloaded content doesn't match uploaded content")
            return False
        
        # Clean up test file
        print("🗑️ Cleaning up test file...")
        blob_client.delete_blob()
        print("✅ Test file deleted successfully")
        
        return True
        
    except Exception as e:
        print(f"❌ Upload/download test failed: {str(e)}")
        return False

def main():
    """Main test function."""
    print_section("Azure Blob Storage Connection Test")
    print(f"Test started at: {datetime.now()}")
    
    # Test 1: Environment variables
    print_section("Step 1: Environment Configuration")
    connection_string, container_name = test_environment_variables()
    
    if not connection_string:
        print("\n❌ Setup incomplete. Please configure environment variables first.")
        return False
    
    # Test 2: Blob service connection
    print_section("Step 2: Azure Blob Service Connection")
    blob_service_client = test_blob_service_connection(connection_string)
    
    if not blob_service_client:
        print("\n❌ Cannot connect to Azure Blob Storage. Please check your connection string.")
        return False
    
    # Test 3: List all containers
    print_section("Step 3: Container Discovery")
    containers = list_containers(blob_service_client)
    
    # Test 4: Specific container access
    print_section("Step 4: Container Access Test")
    container_client = test_container_access(blob_service_client, container_name)
    
    if not container_client:
        print(f"\n❌ Cannot access container '{container_name}'. Please create it in Azure portal.")
        return False
    
    # Test 5: List files in container
    print_section("Step 5: Container Contents")
    blobs = list_blobs_in_container(container_client, container_name)
    
    # Test 6: Upload/Download test
    print_section("Step 6: Upload/Download Test")
    upload_success = test_upload_download(container_client)
    
    # Summary
    print_section("Test Summary")
    if upload_success:
        print("🎉 All tests passed! Azure Blob Storage is ready for use.")
        print("\nNext steps:")
        print("1. Install required dependencies: pip install azure-storage-blob azure-identity")
        print("2. Update your application to use Azure Storage")
        print("3. Start migrating Excel files to the blob container")
        return True
    else:
        print("⚠️  Some tests failed. Please review the errors above.")
        return False

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {str(e)}")
        sys.exit(1)