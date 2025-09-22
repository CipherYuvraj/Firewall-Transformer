"""
Train a ByteLevelBPE tokenizer for web traffic anomaly detection.

This script trains a tokenizer on canonicalized web request logs and saves
the tokenizer artifacts for use in model training and inference.
"""
import argparse
import os
from pathlib import Path
from tokenizers import ByteLevelBPETokenizer
from tokenizers.processors import BertProcessing


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
        help="Path to text file containing canonicalized logs (one per line)"
    )
    
    parser.add_argument(
        "--output_dir",
        default="tokenizer",
        help="Directory to save tokenizer artifacts"
    )
    
    parser.add_argument(
        "--test_file",
        help="Optional test file to validate tokenizer performance"
    )
    
    args = parser.parse_args()
    
    try:
        # Train the tokenizer
        tokenizer = train_tokenizer(args.input_file, args.output_dir)
        
        # If test file provided, run additional validation
        if args.test_file and os.path.exists(args.test_file):
            print(f"\nRunning validation on test file: {args.test_file}")
            
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