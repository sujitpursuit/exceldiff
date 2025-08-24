#!/usr/bin/env python3
"""
Custom Exception Classes for Excel Source-Target Mapping Comparison Tool

This module defines custom exceptions for better error handling and user experience.
"""

from typing import List, Optional


class ExcelComparisonError(Exception):
    """Base exception class for all Excel comparison tool errors."""
    
    def __init__(self, message: str, details: Optional[str] = None):
        self.message = message
        self.details = details
        super().__init__(self.message)
    
    def __str__(self):
        if self.details:
            return f"{self.message}\nDetails: {self.details}"
        return self.message


class FileValidationError(ExcelComparisonError):
    """Raised when file validation fails."""
    
    def __init__(self, file_path: str, reason: str):
        self.file_path = file_path
        self.reason = reason
        message = f"File validation failed: {file_path}"
        super().__init__(message, reason)


class FileNotFoundError(FileValidationError):
    """Raised when a required file is not found."""
    
    def __init__(self, file_path: str):
        reason = "File does not exist or is not accessible"
        super().__init__(file_path, reason)


class InvalidFileFormatError(FileValidationError):
    """Raised when file format is not supported."""
    
    def __init__(self, file_path: str, expected_format: str = "Excel (.xlsx)"):
        reason = f"Invalid file format. Expected: {expected_format}"
        super().__init__(file_path, reason)


class FilePermissionError(FileValidationError):
    """Raised when file permissions prevent access."""
    
    def __init__(self, file_path: str, operation: str = "read"):
        reason = f"Permission denied for {operation} operation"
        super().__init__(file_path, reason)


class ExcelAnalysisError(ExcelComparisonError):
    """Raised when Excel file analysis fails."""
    
    def __init__(self, file_path: str, tab_name: Optional[str] = None, reason: str = "Unknown error"):
        self.file_path = file_path
        self.tab_name = tab_name
        
        if tab_name:
            message = f"Excel analysis failed for tab '{tab_name}' in file: {file_path}"
        else:
            message = f"Excel analysis failed for file: {file_path}"
            
        super().__init__(message, reason)


class InvalidExcelStructureError(ExcelAnalysisError):
    """Raised when Excel file doesn't have the expected structure."""
    
    def __init__(self, file_path: str, tab_name: str, expected_structure: str):
        reason = f"Expected structure: {expected_structure}"
        super().__init__(file_path, tab_name, reason)


class MissingRequiredColumnsError(ExcelAnalysisError):
    """Raised when required columns are missing from Excel tab."""
    
    def __init__(self, file_path: str, tab_name: str, missing_columns: List[str]):
        columns_str = ", ".join(missing_columns)
        reason = f"Missing required columns: {columns_str}"
        super().__init__(file_path, tab_name, reason)


class ComparisonError(ExcelComparisonError):
    """Raised when comparison operation fails."""
    
    def __init__(self, reason: str, file1: Optional[str] = None, file2: Optional[str] = None):
        self.file1 = file1
        self.file2 = file2
        
        if file1 and file2:
            message = f"Comparison failed between '{file1}' and '{file2}'"
        else:
            message = "Comparison operation failed"
            
        super().__init__(message, reason)


class IncompatibleFilesError(ComparisonError):
    """Raised when files cannot be compared due to incompatibility."""
    
    def __init__(self, file1: str, file2: str, reason: str):
        super().__init__(reason, file1, file2)


class ReportGenerationError(ExcelComparisonError):
    """Raised when HTML report generation fails."""
    
    def __init__(self, output_path: str, reason: str):
        self.output_path = output_path
        message = f"Report generation failed: {output_path}"
        super().__init__(message, reason)


class ConfigurationError(ExcelComparisonError):
    """Raised when configuration is invalid or missing."""
    
    def __init__(self, config_item: str, reason: str):
        self.config_item = config_item
        message = f"Configuration error for '{config_item}'"
        super().__init__(message, reason)


class ValidationError(ExcelComparisonError):
    """Raised when data validation fails."""
    
    def __init__(self, data_type: str, validation_rule: str, actual_value: str = ""):
        self.data_type = data_type
        self.validation_rule = validation_rule
        self.actual_value = actual_value
        
        message = f"Validation failed for {data_type}"
        details = f"Rule: {validation_rule}"
        if actual_value:
            details += f", Actual value: {actual_value}"
            
        super().__init__(message, details)


class ProcessingError(ExcelComparisonError):
    """Raised when data processing fails."""
    
    def __init__(self, operation: str, reason: str, context: Optional[str] = None):
        self.operation = operation
        self.context = context
        
        message = f"Processing failed during {operation}"
        if context:
            message += f" (Context: {context})"
            
        super().__init__(message, reason)


class UserInteractionError(ExcelComparisonError):
    """Raised when user interaction or input is invalid."""
    
    def __init__(self, user_input: str, expected_format: str):
        self.user_input = user_input
        self.expected_format = expected_format
        
        message = f"Invalid user input: '{user_input}'"
        details = f"Expected format: {expected_format}"
        
        super().__init__(message, details)


# Utility functions for error handling
def handle_file_error(file_path: str, error: Exception) -> FileValidationError:
    """Convert generic file errors to specific FileValidationError instances."""
    
    if isinstance(error, FileNotFoundError):
        return FileNotFoundError(file_path)
    elif isinstance(error, PermissionError):
        return FilePermissionError(file_path)
    elif "format" in str(error).lower() or "xlsx" in str(error).lower():
        return InvalidFileFormatError(file_path)
    else:
        return FileValidationError(file_path, str(error))


def handle_excel_error(file_path: str, tab_name: Optional[str], error: Exception) -> ExcelAnalysisError:
    """Convert generic Excel errors to specific ExcelAnalysisError instances."""
    
    error_msg = str(error).lower()
    
    if "column" in error_msg and "missing" in error_msg:
        # Try to extract column names from error message
        return MissingRequiredColumnsError(file_path, tab_name or "", ["Unknown column"])
    elif "structure" in error_msg or "format" in error_msg:
        return InvalidExcelStructureError(file_path, tab_name or "", "Source-Target mapping format")
    else:
        return ExcelAnalysisError(file_path, tab_name, str(error))


def create_user_friendly_message(error: Exception) -> str:
    """Create user-friendly error messages from exceptions."""
    
    if isinstance(error, FileNotFoundError):
        return f"The file '{error.file_path}' could not be found. Please check the file path and try again."
    
    elif isinstance(error, FilePermissionError):
        return f"Permission denied accessing '{error.file_path}'. Please check file permissions or close the file if it's open."
    
    elif isinstance(error, InvalidFileFormatError):
        return f"The file '{error.file_path}' is not a valid Excel file. Please ensure you're using a .xlsx file."
    
    elif isinstance(error, InvalidExcelStructureError):
        return f"The Excel file structure in tab '{error.tab_name}' doesn't match the expected Source-Target mapping format."
    
    elif isinstance(error, ReportGenerationError):
        return f"Failed to generate the HTML report at '{error.output_path}'. Please check write permissions and disk space."
    
    elif isinstance(error, ExcelComparisonError):
        return error.message
    
    else:
        return f"An unexpected error occurred: {str(error)}"