"""
JSON Log Processor for Web Traffic Anomaly Detection

This script processes JSON log files and converts them to canonicalized format
required for training the anomaly detection model.
"""
import json
import argparse
import os
import logging
from pathlib import Path
from typing import List, Dict, Any, Iterator
from tqdm import tqdm

# Import canonicalization functions
from canonicalize import canonicalize_request


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def read_json_logs(file_path: str) -> Iterator[Dict[str, Any]]:
    """
    Read JSON logs from file. Supports both JSONL (one JSON per line) 
    and JSON array formats.
    
    Args:
        file_path: Path to JSON log file
    
    Yields:
        Dictionary representing each log entry
    """
    logger.info(f"Reading JSON logs from: {file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        # Try to determine format by reading first line
        first_line = f.readline().strip()
        f.seek(0)  # Reset file pointer
        
        if first_line.startswith('['):
            # JSON array format
            logger.info("Detected JSON array format")
            data = json.load(f)
            if isinstance(data, list):
                for entry in data:
                    yield entry
            else:
                yield data
        else:
            # JSONL format (one JSON per line)
            logger.info("Detected JSONL format")
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if line:
                    try:
                        entry = json.loads(line)
                        yield entry
                    except json.JSONDecodeError as e:
                        logger.warning(f"Invalid JSON on line {line_num}: {e}")
                        continue


def process_json_logs(
    input_file: str,
    output_file: str,
    max_samples: int = None,
    skip_errors: bool = True
) -> int:
    """
    Process JSON logs and convert to canonicalized format.
    
    Args:
        input_file: Path to input JSON file
        output_file: Path to output canonicalized text file
        max_samples: Maximum number of samples to process (None for all)
        skip_errors: Whether to skip entries that cause errors
    
    Returns:
        Number of successfully processed entries
    """
    processed_count = 0
    error_count = 0
    
    # Create output directory if needed
    Path(output_file).parent.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Processing JSON logs from {input_file} to {output_file}")
    if max_samples:
        logger.info(f"Processing maximum {max_samples} samples")
    
    with open(output_file, 'w', encoding='utf-8') as out_f:
        for i, log_entry in enumerate(tqdm(read_json_logs(input_file), desc="Processing logs")):
            if max_samples and processed_count >= max_samples:
                break
            
            try:
                # Canonicalize the log entry
                canonical = canonicalize_request(log_entry)
                
                # Write to output file
                out_f.write(f"{canonical}\n")
                processed_count += 1
                
            except Exception as e:
                error_count += 1
                if skip_errors:
                    logger.debug(f"Error processing entry {i}: {e}")
                    continue
                else:
                    logger.error(f"Error processing entry {i}: {e}")
                    raise
    
    logger.info(f"Processing completed:")
    logger.info(f"  Successfully processed: {processed_count}")
    logger.info(f"  Errors encountered: {error_count}")
    logger.info(f"  Output written to: {output_file}")
    
    return processed_count


def analyze_json_structure(file_path: str, max_samples: int = 100) -> Dict[str, Any]:
    """
    Analyze the structure of JSON logs to understand data format.
    
    Args:
        file_path: Path to JSON file
        max_samples: Maximum samples to analyze
    
    Returns:
        Dictionary with analysis results
    """
    logger.info(f"Analyzing JSON structure of {file_path}")
    
    all_keys = set()
    field_types = {}
    field_examples = {}
    sample_count = 0
    
    for entry in read_json_logs(file_path):
        if sample_count >= max_samples:
            break
        
        sample_count += 1
        
        if isinstance(entry, dict):
            for key, value in entry.items():
                all_keys.add(key)
                
                # Track field types
                value_type = type(value).__name__
                if key not in field_types:
                    field_types[key] = set()
                field_types[key].add(value_type)
                
                # Store examples
                if key not in field_examples:
                    field_examples[key] = []
                if len(field_examples[key]) < 3:  # Keep up to 3 examples
                    field_examples[key].append(str(value)[:100])  # Truncate long values
    
    analysis = {
        'total_samples_analyzed': sample_count,
        'unique_fields': len(all_keys),
        'all_fields': sorted(list(all_keys)),
        'field_types': {k: list(v) for k, v in field_types.items()},
        'field_examples': field_examples
    }
    
    # Print analysis
    logger.info(f"Analysis Results:")
    logger.info(f"  Samples analyzed: {sample_count}")
    logger.info(f"  Unique fields found: {len(all_keys)}")
    logger.info(f"  Common fields: {sorted(list(all_keys))[:10]}")
    
    return analysis


def create_sample_canonical_data(output_file: str = "data/sample_canonical.txt"):
    """
    Create sample canonicalized data for testing.
    
    Args:
        output_file: Path to output sample file
    """
    sample_logs = [
        {
            "method": "GET",
            "path": "/api/users",
            "query_params": {"page": "1", "limit": "10"},
            "headers": {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "application/json",
                "Authorization": "Bearer token123"
            }
        },
        {
            "method": "POST",
            "path": "/api/login",
            "headers": {
                "Content-Type": "application/json",
                "User-Agent": "curl/7.68.0"
            },
            "body": '{"username": "admin", "password": "secret"}'
        },
        {
            "method": "GET",
            "path": "/static/css/style.css",
            "headers": {
                "Accept": "text/css",
                "User-Agent": "Mozilla/5.0"
            }
        },
        {
            "method": "POST",
            "path": "/upload",
            "query_params": {"type": "image"},
            "headers": {
                "Content-Type": "multipart/form-data",
                "Content-Length": "1024"
            }
        },
        {
            "method": "DELETE",
            "path": "/api/users/123",
            "headers": {
                "Authorization": "Bearer token456",
                "Content-Type": "application/json"
            }
        }
    ]
    
    # Create output directory
    Path(output_file).parent.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Creating sample canonical data: {output_file}")
    
    with open(output_file, 'w', encoding='utf-8') as f:
        for log_entry in sample_logs:
            canonical = canonicalize_request(log_entry)
            f.write(f"{canonical}\n")
    
    logger.info(f"Sample data created with {len(sample_logs)} entries")


def main():
    """Main function to handle command line arguments."""
    parser = argparse.ArgumentParser(
        description="Process JSON logs for web traffic anomaly detection",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Process command
    process_parser = subparsers.add_parser('process', help='Process JSON logs to canonical format')
    process_parser.add_argument('input_file', help='Input JSON log file')
    process_parser.add_argument('output_file', help='Output canonicalized text file')
    process_parser.add_argument('--max_samples', type=int, help='Maximum samples to process')
    process_parser.add_argument('--no_skip_errors', action='store_true', help='Fail on first error')
    
    # Analyze command
    analyze_parser = subparsers.add_parser('analyze', help='Analyze JSON log structure')
    analyze_parser.add_argument('input_file', help='Input JSON log file')
    analyze_parser.add_argument('--max_samples', type=int, default=100, help='Maximum samples to analyze')
    analyze_parser.add_argument('--output', help='Save analysis to JSON file')
    
    # Sample command
    sample_parser = subparsers.add_parser('sample', help='Create sample canonical data')
    sample_parser.add_argument('--output', default='data/sample_canonical.txt', help='Output file path')
    
    args = parser.parse_args()
    
    if args.command == 'process':
        if not os.path.exists(args.input_file):
            logger.error(f"Input file not found: {args.input_file}")
            return 1
        
        try:
            count = process_json_logs(
                input_file=args.input_file,
                output_file=args.output_file,
                max_samples=args.max_samples,
                skip_errors=not args.no_skip_errors
            )
            logger.info(f"Successfully processed {count} log entries")
            
        except Exception as e:
            logger.error(f"Processing failed: {e}")
            return 1
    
    elif args.command == 'analyze':
        if not os.path.exists(args.input_file):
            logger.error(f"Input file not found: {args.input_file}")
            return 1
        
        try:
            analysis = analyze_json_structure(args.input_file, args.max_samples)
            
            if args.output:
                with open(args.output, 'w') as f:
                    json.dump(analysis, f, indent=2)
                logger.info(f"Analysis saved to: {args.output}")
            
        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            return 1
    
    elif args.command == 'sample':
        try:
            create_sample_canonical_data(args.output)
            logger.info("Sample data created successfully")
            
        except Exception as e:
            logger.error(f"Sample creation failed: {e}")
            return 1
    
    else:
        parser.print_help()
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())