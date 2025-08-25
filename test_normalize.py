#!/usr/bin/env python3
"""
Test column name normalization
"""

from excel_analyzer import normalize_column_name
from config import COLUMN_NAME_MAPPINGS

def test_comments_normalization():
    print("Column Name Normalization Test")
    print("="*40)
    
    # Test cases
    test_headers = [
        "Comments",
        "comments", 
        "Comment",
        "comment",
        "Description",
        "description",
        "COMMENTS"
    ]
    
    print("COLUMN_NAME_MAPPINGS['description']:")
    print(COLUMN_NAME_MAPPINGS['description'])
    
    print(f"\nTesting normalization:")
    for header in test_headers:
        result = normalize_column_name(header)
        print(f"  '{header}' -> '{result}'")

if __name__ == "__main__":
    test_comments_normalization()