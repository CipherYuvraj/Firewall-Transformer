"""
Train a ByteLevelBPE tokenizer for web traffic anomaly detection.

This script trains a tokenizer directly on JSON/JSONL files and saves
the tokenizer artifacts for use in model training and inference.
"""
import argparse
import os
import json
import tempfile
from pathlib import Path
from tokenizers import ByteLevelBPETokenizer
from tokenizers.processors import BertProcessing
from canonicalize import canonicalize_request


def train_tokenizer_from_json(input_file: str, output_dir: str = "tokenizer", max_samples: int = None):
    """
    Train a ByteLevelBPE tokenizer on JSON/JSONL data.
    
    Args:
        input_file: Path to JSON/JSONL file containing web request logs
        output_dir: Directory to save tokenizer artifacts
        max_samples: Maximum number of samples to use for training (None for all)
    """
    # Validate input file exists
    if not os.path.exists(input_file):
        raise FileNotFoundError(f"Input file not found: {input_file}")
    
    # Create output directory
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    print(f"Training tokenizer on JSON file: {input_file}")
    print(f"Output directory: {output_dir}")
    if max_samples:
        print(f"Max samples: {max_samples}")
    
    # Create temporary file for canonicalized data
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as temp_file:
        temp_filename = temp_file.name
        
        print("Canonicalizing JSON data...")
        processed_count = 0
        error_count = 0
        
        try:
            with open(input_file, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    if max_samples and processed_count >= max_samples:
                        break
                        
                    line = line.strip()
                    if not line:
                        continue
                    
                    try:
                        # Parse JSON line
                        log_entry = json.loads(line)
                        
                        # Canonicalize the log entry
                        canonical_text = canonicalize_request(log_entry)
                        
                        # Write to temporary file
                        temp_file.write(canonical_text + '\n')
                        processed_count += 1
                        
                        if processed_count % 10000 == 0:
                            print(f"  Processed {processed_count} entries...")
                            
                    except (json.JSONDecodeError, KeyError, Exception) as e:
                        error_count += 1
                        if error_count <= 5:  # Show first 5 errors
                            print(f"  Warning: Error processing line {line_num}: {e}")
                        continue
        
        except Exception as e:
            os.unlink(temp_filename)  # Clean up temp file
            raise e
    
    print(f"Canonicalization complete:")
    print(f"  Processed: {processed_count} entries")
    print(f"  Errors: {error_count} entries")
    print(f"  Temporary file: {temp_filename}")
    
    try:
        # Train tokenizer on the temporary file
        tokenizer = train_tokenizer(temp_filename, output_dir)
        return tokenizer
    finally:
        # Clean up temporary file
        try:
            os.unlink(temp_filename)
            print(f"Cleaned up temporary file: {temp_filename}")
        except:
            pass


def train_tokenizer(input_file: str, output_dir: str = "tokenizer"):
    """
    Train a ByteLevelBPE tokenizer on canonicalized log data.
    
    Args:
        input_file: Path to text file containing canonicalized logs
        output_dir: Directory to save tokenizer artifacts
    """
    # Validate input file exists
    if not os.path.exists(input_file):
        raise FileNotFoundError(f"Input file not found: {input_file}")
    
    # Create output directory
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    print(f"Training tokenizer on: {input_file}")
    print(f"Output directory: {output_dir}")
    
    # Initialize tokenizer
    tokenizer = ByteLevelBPETokenizer()
    
    # Special tokens for our domain
    special_tokens = [
        "[METHOD]",  # Marks HTTP method section
        "[PATH]",    # Marks URL path section  
        "[PARAMS]",  # Marks query parameters section
        "[HEADERS]", # Marks headers section
        "<pad>",     # Padding token
        "<s>",       # Start of sequence
        "</s>",      # End of sequence
        "<unk>",     # Unknown token
        "<mask>"     # Mask token for MLM
    ]
    
    print("Training tokenizer with configuration:")
    print(f"  Vocab size: 8000")
    print(f"  Min frequency: 2")
    print(f"  Special tokens: {special_tokens}")
    
    # Train the tokenizer
    tokenizer.train(
        files=[input_file],
        vocab_size=8000,
        min_frequency=2,
        special_tokens=special_tokens,
        show_progress=True
    )
    
    # Configure post-processor for BERT-like behavior
    tokenizer.post_processor = BertProcessing(
        ("<s>", tokenizer.token_to_id("<s>")),
        ("</s>", tokenizer.token_to_id("</s>"))
    )
    
    # Enable truncation and padding
    tokenizer.enable_truncation(max_length=256)
    tokenizer.enable_padding(pad_id=tokenizer.token_to_id("<pad>"), pad_token="<pad>")
    
    # Save tokenizer
    vocab_file = os.path.join(output_dir, "vocab.json")
    merges_file = os.path.join(output_dir, "merges.txt")
    
    tokenizer.save_model(output_dir)
    
    print(f"Tokenizer saved to:")
    print(f"  Vocabulary: {vocab_file}")
    print(f"  Merges: {merges_file}")
    
    # Validate the saved tokenizer by loading it
    print("\nValidating saved tokenizer...")
    test_tokenizer = ByteLevelBPETokenizer(vocab_file, merges_file)
    
    # Test tokenization
    test_text = "[METHOD] GET [PATH] /api/test [PARAMS] id=123 [HEADERS] content-type:application/json"
    encoding = test_tokenizer.encode(test_text)
    
    print(f"Test encoding successful:")
    print(f"  Input: {test_text}")
    print(f"  Tokens: {encoding.tokens[:10]}...")  # Show first 10 tokens
    print(f"  Token IDs: {encoding.ids[:10]}...")  # Show first 10 IDs
    print(f"  Total tokens: {len(encoding.tokens)}")
    
    # Print vocabulary statistics
    print(f"\nTokenizer statistics:")
    print(f"  Vocabulary size: {test_tokenizer.get_vocab_size()}")
    print(f"  Special tokens: {len(special_tokens)}")
    
    # Show some example tokens from vocabulary
    vocab = test_tokenizer.get_vocab()
    print(f"\nExample vocabulary tokens:")
    sorted_vocab = sorted(vocab.items(), key=lambda x: x[1])[:20]
    for token, token_id in sorted_vocab:
        print(f"  {token_id:4d}: '{token}'")
    
    return test_tokenizer


def main():
    """Main function to handle command line arguments and run training."""
    parser = argparse.ArgumentParser(
        description="Train a ByteLevelBPE tokenizer for web traffic anomaly detection",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    parser.add_argument(
        "input_file",
        help="Path to JSON/JSONL file containing web request logs"
    )
    
    parser.add_argument(
        "--output_dir",
        default="tokenizer",
        help="Directory to save tokenizer artifacts"
    )
    
    parser.add_argument(
        "--max_samples",
        type=int,
        help="Maximum number of samples to use for training (default: all)"
    )
    
    parser.add_argument(
        "--test_file",
        help="Optional JSON test file to validate tokenizer performance"
    )
    
    args = parser.parse_args()
    
    try:
        # Detect file type and train accordingly
        if args.input_file.endswith(('.json', '.jsonl')):
            print("Detected JSON/JSONL input file")
            tokenizer = train_tokenizer_from_json(args.input_file, args.output_dir, args.max_samples)
        else:
            print("Detected text input file")
            tokenizer = train_tokenizer(args.input_file, args.output_dir)
        
        # If test file provided, run additional validation
        if args.test_file and os.path.exists(args.test_file):
            print(f"\nRunning validation on test file: {args.test_file}")
            
            if args.test_file.endswith(('.json', '.jsonl')):
                # Test on JSON file
                total_tokens = 0
                test_count = 0
                
                with open(args.test_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        if test_count >= 100:  # Test on first 100 lines
                            break
                        line = line.strip()
                        if not line:
                            continue
                        
                        try:
                            log_entry = json.loads(line)
                            canonical_text = canonicalize_request(log_entry)
                            encoding = tokenizer.encode(canonical_text)
                            total_tokens += len(encoding.tokens)
                            test_count += 1
                        except:
                            continue
                
                if test_count > 0:
                    avg_tokens = total_tokens / test_count
                    print(f"  Processed {test_count} test entries")
                    print(f"  Average tokens per entry: {avg_tokens:.2f}")
                    print(f"  Total tokens: {total_tokens}")
            else:
                # Test on text file
                with open(args.test_file, 'r', encoding='utf-8') as f:
                    test_lines = f.readlines()[:100]  # Test on first 100 lines
                
                total_tokens = 0
                for line in test_lines:
                    encoding = tokenizer.encode(line.strip())
                    total_tokens += len(encoding.tokens)
                
                avg_tokens = total_tokens / len(test_lines)
                print(f"  Processed {len(test_lines)} test lines")
                print(f"  Average tokens per line: {avg_tokens:.2f}")
                print(f"  Total tokens: {total_tokens}")
        
        print("\nTokenizer training completed successfully!")
        
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())