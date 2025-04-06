#!/usr/bin/env python3
"""
Main entry point for testing the background guide processor.

This module provides a command-line interface for testing the background guide
processor functionality without running the full Flask application.
"""

import os
import sys
import argparse
import json
from pathlib import Path

from processor import BackgroundGuideProcessor

def main():
    """Main entry point for the command-line interface."""
    parser = argparse.ArgumentParser(description="Background Guide Processor CLI")
    
    # Required arguments
    parser.add_argument(
        "file", 
        help="Path to the background guide file (PDF or text)"
    )
    
    # Optional arguments
    parser.add_argument(
        "--output-dir", "-o",
        help="Directory to write output files (default: output)",
        default="output"
    )
    parser.add_argument(
        "--use-openai", "-u",
        help="Use OpenAI API for summarization",
        action="store_true",
        default=True
    )
    parser.add_argument(
        "--no-openai",
        help="Don't use OpenAI API for summarization",
        dest="use_openai",
        action="store_false"
    )
    parser.add_argument(
        "--use-aws", "-a",
        help="Use AWS hosted model for refinement",
        action="store_true",
        default=True
    )
    parser.add_argument(
        "--no-aws",
        help="Don't use AWS hosted model for refinement",
        dest="use_aws",
        action="store_false"
    )
    parser.add_argument(
        "--query", "-q",
        help="Query to search in the processed guide",
        default=None
    )
    
    args = parser.parse_args()
    
    # Check if file exists
    file_path = Path(args.file)
    if not file_path.exists():
        print(f"Error: File not found: {file_path}")
        return 1
    
    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        # Initialize processor
        processor = BackgroundGuideProcessor(
            use_openai_for_summary=args.use_openai,
            use_aws_model=args.use_aws,
            output_dir=str(output_dir)
        )
        
        # Process the file
        print(f"Processing file: {file_path}")
        results = processor.process_file(str(file_path))
        
        # Print some results
        print("\nProcessing complete!")
        print(f"Segments: {len(results.get('segments', []))}")
        print(f"JSON files: {len(results.get('json_files', {}))}")
        
        # If a query was provided, search for it
        if args.query:
            print(f"\nSearching for query: {args.query}")
            context = processor.retrieve_context_for_query(args.query)
            
            print(f"Found {len(context)} relevant segments:")
            for i, ctx in enumerate(context, 1):
                print(f"Segment {i}:")
                print(f"  Section: {ctx.get('section', 'N/A')}")
                if ctx.get('subsection'):
                    print(f"  Subsection: {ctx.get('subsection')}")
                print(f"  Score: {ctx.get('score', 0):.4f}")
                
                # Print excerpt
                text = ctx.get('text', '')
                if len(text) > 100:
                    print(f"  Excerpt: {text[:100]}...")
                else:
                    print(f"  Excerpt: {text}")
                    
                print()
        
        return 0
        
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main()) 