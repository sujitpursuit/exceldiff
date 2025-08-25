#!/usr/bin/env python3
"""
Excel Source-Target Mapping Comparison Tool - Main Application

This is the primary entry point for the Excel comparison tool with a comprehensive
command-line interface, error handling, and user-friendly interactions.

Usage: python main.py [options] file1.xlsx file2.xlsx
"""

import argparse
import sys
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

# Local imports
from comparator import compare_workbooks
from report_generator import generate_html_report
from json_report_generator import generate_json_report
from utils import validate_file_path
from exceptions import (
    ExcelComparisonError, FileValidationError, ComparisonError,
    ReportGenerationError, create_user_friendly_message
)
from logger import get_logger, PerformanceTimer, log_exception, log_user_action
import config


class ExcelComparisonApp:
    """Main application class for the Excel comparison tool."""
    
    def __init__(self):
        self.logger = None
        self.start_time = None
        self.args = None
        
    def setup_logging(self, debug_mode: bool = False, quiet_mode: bool = False):
        """Initialize logging based on user preferences."""
        if quiet_mode:
            self.logger = get_logger("main", level="ERROR", console_output=False, file_output=True)
        elif debug_mode:
            self.logger = get_logger("main", level="DEBUG", debug_mode=True)
        else:
            self.logger = get_logger("main", level="INFO")
        
        log_user_action(self.logger, "Application started", f"Debug: {debug_mode}, Quiet: {quiet_mode}")
    
    def create_argument_parser(self) -> argparse.ArgumentParser:
        """Create and configure command-line argument parser."""
        parser = argparse.ArgumentParser(
            description="Excel Source-Target Mapping Comparison Tool",
            epilog="""
Examples:
  python main.py file1.xlsx file2.xlsx
  python main.py -o custom_report.html file1.xlsx file2.xlsx
  python main.py --debug --verbose file1.xlsx file2.xlsx
  python main.py --quiet --no-report file1.xlsx file2.xlsx
            """,
            formatter_class=argparse.RawDescriptionHelpFormatter
        )
        
        # Positional arguments
        parser.add_argument(
            'file1',
            help='First Excel file (original/baseline version)'
        )
        
        parser.add_argument(
            'file2',
            help='Second Excel file (modified/new version)'
        )
        
        # Output options
        output_group = parser.add_argument_group('Output Options')
        output_group.add_argument(
            '-o', '--output',
            help='Output HTML report file path (default: auto-generated in reports/)',
            metavar='FILE'
        )
        
        output_group.add_argument(
            '--no-report',
            action='store_true',
            help='Skip HTML report generation (console output only)'
        )
        
        output_group.add_argument(
            '--report-title',
            help='Custom title for the HTML report',
            metavar='TITLE'
        )
        
        # Logging options
        logging_group = parser.add_argument_group('Logging Options')
        logging_group.add_argument(
            '--debug',
            action='store_true',
            help='Enable debug mode with verbose output'
        )
        
        logging_group.add_argument(
            '--quiet',
            action='store_true',
            help='Suppress console output (errors only)'
        )
        
        logging_group.add_argument(
            '--log-level',
            choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
            default='INFO',
            help='Set logging level (default: INFO)'
        )
        
        # Processing options
        processing_group = parser.add_argument_group('Processing Options')
        processing_group.add_argument(
            '--include-hidden',
            action='store_true',
            help='Include hidden tabs in comparison'
        )
        
        processing_group.add_argument(
            '--validate-only',
            action='store_true',
            help='Only validate files without performing comparison'
        )
        
        # Progress and timing
        misc_group = parser.add_argument_group('Miscellaneous')
        misc_group.add_argument(
            '--progress',
            action='store_true',
            help='Show progress indicators during processing'
        )
        
        misc_group.add_argument(
            '--version',
            action='version',
            version='Excel Comparison Tool v2.0'
        )
        
        return parser
    
    def validate_arguments(self, args) -> bool:
        """Validate command-line arguments."""
        try:
            # Check if files exist and are accessible
            for file_path in [args.file1, args.file2]:
                is_valid, error = validate_file_path(file_path)
                if not is_valid:
                    raise FileValidationError(file_path, error)
            
            # Check output directory if custom output specified
            if args.output:
                output_path = Path(args.output)
                output_dir = output_path.parent
                
                if not output_dir.exists():
                    try:
                        output_dir.mkdir(parents=True, exist_ok=True)
                        self.logger.info(f"Created output directory: {output_dir}")
                    except Exception as e:
                        raise ReportGenerationError(str(output_path), f"Cannot create output directory: {e}")
            
            return True
            
        except ExcelComparisonError as e:
            self.print_error(create_user_friendly_message(e))
            return False
        except Exception as e:
            self.print_error(f"Unexpected validation error: {e}")
            log_exception(self.logger, "argument validation", e)
            return False
    
    def print_header(self):
        """Print application header."""
        if not self.args.quiet:
            print("\n" + "="*70)
            print("   Excel Source-Target Mapping Comparison Tool v2.0")
            print("="*70)
            print(f"Comparing: {self.args.file1}")
            print(f"     vs:   {self.args.file2}")
            print("="*70)
    
    def print_progress(self, message: str):
        """Print progress message if progress mode is enabled."""
        if self.args.progress and not self.args.quiet:
            timestamp = datetime.now().strftime("%H:%M:%S")
            print(f"[{timestamp}] {message}")
    
    def print_error(self, message: str):
        """Print error message to stderr."""
        print(f"ERROR: {message}", file=sys.stderr)
    
    def print_success(self, message: str):
        """Print success message."""
        if not self.args.quiet:
            print(f"[OK] {message}")
    
    def validate_files(self) -> bool:
        """Validate input files."""
        self.print_progress("Validating input files...")
        
        try:
            for i, file_path in enumerate([self.args.file1, self.args.file2], 1):
                is_valid, error = validate_file_path(file_path)
                if not is_valid:
                    raise FileValidationError(file_path, error)
                
                if not self.args.quiet:
                    file_size = Path(file_path).stat().st_size
                    print(f"  File {i}: {Path(file_path).name} ({file_size:,} bytes) [OK]")
            
            return True
            
        except FileValidationError as e:
            self.print_error(create_user_friendly_message(e))
            log_exception(self.logger, "file validation", e)
            return False
    
    def perform_comparison(self):
        """Perform the Excel comparison operation."""
        self.print_progress("Starting Excel comparison...")
        
        try:
            with PerformanceTimer(self.logger, "Excel comparison", f"{self.args.file1} vs {self.args.file2}"):
                result = compare_workbooks(self.args.file1, self.args.file2)
            
            if result.has_errors:
                self.logger.warning(f"Comparison completed with {len(result.errors)} errors")
                if not self.args.quiet:
                    print("\nComparison Warnings:")
                    for error in result.errors:
                        print(f"  - {error}")
            
            return result
            
        except Exception as e:
            raise ComparisonError(str(e), self.args.file1, self.args.file2)
    
    def display_results(self, result):
        """Display comparison results to console."""
        if self.args.quiet:
            return
        
        print("\n" + "="*70)
        print("COMPARISON RESULTS")
        print("="*70)
        
        # File information
        print(f"Files analyzed: 2")
        print(f"Total tabs in file 1: {result.summary.total_tabs_v1}")
        print(f"Total tabs in file 2: {result.summary.total_tabs_v2}")
        print(f"Valid tabs compared: {len(result.tab_comparisons)}")
        
        # Mapping counts
        print(f"\nMapping counts:")
        print(f"  File 1 total mappings: {result.summary.total_mappings_v1}")
        print(f"  File 2 total mappings: {result.summary.total_mappings_v2}")
        
        # Changes summary
        print(f"\nTAB CHANGES:")
        print(f"  Added:     {result.summary.tabs_added}")
        print(f"  Deleted:   {result.summary.tabs_deleted}")
        print(f"  Modified:  {result.summary.tabs_modified}")
        print(f"  Unchanged: {result.summary.tabs_unchanged}")
        
        print(f"\nMAPPING CHANGES:")
        print(f"  Added:     {result.summary.total_mappings_added}")
        print(f"  Deleted:   {result.summary.total_mappings_deleted}")
        print(f"  Modified:  {result.summary.total_mappings_modified}")
        
        # Calculate total changes
        total_changes = (result.summary.tabs_added + result.summary.tabs_deleted + 
                        result.summary.tabs_modified + result.summary.total_mappings_added +
                        result.summary.total_mappings_deleted + result.summary.total_mappings_modified)
        
        if total_changes > 0:
            print(f"\nCHANGED TABS:")
            changed_tabs = [name for name, comp in result.tab_comparisons.items() if comp.has_changes]
            for tab_name in changed_tabs:
                comparison = result.tab_comparisons[tab_name]
                changes = comparison.change_summary
                status_parts = []
                
                if changes['added'] > 0:
                    status_parts.append(f"+{changes['added']} added")
                if changes['deleted'] > 0:
                    status_parts.append(f"-{changes['deleted']} deleted")
                if changes['modified'] > 0:
                    status_parts.append(f"~{changes['modified']} modified")
                
                print(f"  {tab_name}: {', '.join(status_parts)}")
            
            print(f"\nSUMMARY: SUMMARY: {total_changes} total changes detected")
        else:
            print(f"\nSUMMARY: SUMMARY: No changes detected - files are identical")
        
        # Log summary for audit purposes
        if hasattr(result, 'summary'):
            summary_dict = {
                'tabs_added': result.summary.tabs_added,
                'tabs_deleted': result.summary.tabs_deleted,
                'tabs_modified': result.summary.tabs_modified,
                'total_mappings_added': result.summary.total_mappings_added,
                'total_mappings_deleted': result.summary.total_mappings_deleted,
                'total_mappings_modified': result.summary.total_mappings_modified
            }
            # Log summary for audit purposes
            self.logger.info(f"Comparison Summary: {self.args.file1} vs {self.args.file2}")
            self.logger.info(f"  Tabs: +{summary_dict['tabs_added']} -{summary_dict['tabs_deleted']} ~{summary_dict['tabs_modified']}")
            self.logger.info(f"  Mappings: +{summary_dict['total_mappings_added']} -{summary_dict['total_mappings_deleted']} ~{summary_dict['total_mappings_modified']}")
    
    def generate_report(self, result) -> Optional[str]:
        """Generate HTML report."""
        if self.args.no_report:
            return None
        
        self.print_progress("Generating HTML report...")
        
        try:
            # Determine output path
            if self.args.output:
                output_path = self.args.output
            else:
                # Auto-generate filename using config settings
                timestamp = datetime.now().strftime(config.REPORT_TIMESTAMP_FORMAT)
                file1_name = Path(self.args.file1).stem
                file2_name = Path(self.args.file2).stem
                
                # Use the template from config
                if config.INCLUDE_TIMESTAMP_IN_FILENAME:
                    filename = config.REPORT_FILENAME_TEMPLATE.format(
                        file1=file1_name, 
                        file2=file2_name, 
                        timestamp=timestamp
                    )
                else:
                    filename = f"comparison_{file1_name}_vs_{file2_name}.html"
                
                # Construct the full path using config directories
                output_path = os.path.join(config.REPORTS_BASE_DIR, config.DIFF_REPORTS_DIR, filename)
            
            # Generate report title using config template
            if self.args.report_title:
                report_title = self.args.report_title
            else:
                report_title = config.REPORT_TITLE_TEMPLATE.format(
                    file1=Path(self.args.file1).name,
                    file2=Path(self.args.file2).name
                )
            
            # Generate the HTML report
            with PerformanceTimer(self.logger, "HTML report generation", output_path):
                success = generate_html_report(result, output_path, report_title)
            
            if success:
                self.print_success(f"HTML report generated: {output_path}")
                self.logger.info(f"Report generation successful: {output_path}")
                
                # Generate the JSON report (same path but with .json extension)
                json_output_path = output_path.replace('.html', '.json')
                try:
                    with PerformanceTimer(self.logger, "JSON report generation", json_output_path):
                        json_success = generate_json_report(result, json_output_path, report_title)
                    
                    if json_success:
                        self.print_success(f"JSON report generated: {json_output_path}")
                        self.logger.info(f"JSON report generation successful: {json_output_path}")
                    else:
                        self.logger.warning("JSON report generation failed")
                        
                except Exception as e:
                    self.logger.warning(f"JSON report generation failed: {e}")
                
                return output_path
            else:
                raise ReportGenerationError(output_path, "Report generation returned False")
                
        except Exception as e:
            raise ReportGenerationError(output_path, str(e))
    
    def run(self, args=None) -> int:
        """Main application execution."""
        try:
            # Parse arguments
            parser = self.create_argument_parser()
            self.args = parser.parse_args(args)
            
            # Setup logging
            self.setup_logging(self.args.debug, self.args.quiet)
            self.start_time = time.time()
            
            # Validate arguments
            if not self.validate_arguments(self.args):
                return 1
            
            # Print header
            self.print_header()
            
            # Validate files only mode
            if self.args.validate_only:
                if self.validate_files():
                    self.print_success("File validation completed successfully")
                    return 0
                else:
                    return 1
            
            # Validate files
            if not self.validate_files():
                return 1
            
            # Perform comparison
            result = self.perform_comparison()
            
            # Display results
            self.display_results(result)
            
            # Generate report
            report_path = self.generate_report(result)
            
            # Final summary
            elapsed_time = time.time() - self.start_time
            if not self.args.quiet:
                print("\n" + "="*70)
                print(f"SUCCESS: Comparison completed successfully in {elapsed_time:.2f} seconds")
                if report_path:
                    print(f"Report: Report saved to: {report_path}")
                    print("   Open this file in your web browser to view the detailed comparison")
                print("="*70)
            
            # Log completion
            self.logger.info(f"Application completed successfully in {elapsed_time:.2f}s")
            log_user_action(self.logger, "Application completed", 
                          f"Files: {self.args.file1} vs {self.args.file2}, Report: {report_path}")
            
            return 0
            
        except KeyboardInterrupt:
            self.print_error("Operation cancelled by user")
            if self.logger:
                log_user_action(self.logger, "Operation cancelled", "KeyboardInterrupt")
            return 130  # Standard exit code for Ctrl+C
            
        except ExcelComparisonError as e:
            self.print_error(create_user_friendly_message(e))
            if self.logger:
                log_exception(self.logger, "application execution", e)
            return 1
            
        except Exception as e:
            self.print_error(f"Unexpected error: {e}")
            if self.logger:
                log_exception(self.logger, "application execution", e)
            return 1


def main():
    """Entry point for the application."""
    app = ExcelComparisonApp()
    exit_code = app.run()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()