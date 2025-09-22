"""
Train a RoBERTa model for web traffic anomaly detection using Masked Language Modeling.

This script trains a Transformer model on JSON/JSONL web request logs to learn
the patterns of benign traffic. The trained model can then be used for anomaly scoring.
"""
import argparse
import os
import json
import logging
from pathlib import Path
from typing import Optional

import torch
from torch.utils.data import Dataset
from transformers import (
    RobertaConfig,
    RobertaForMaskedLM,
    RobertaTokenizer,
    DataCollatorForLanguageModeling,
    TrainingArguments,
    Trainer,
    set_seed
)
from datasets import Dataset as HFDataset, load_dataset
from tokenizers import ByteLevelBPETokenizer

# Import canonicalization function
import sys
sys.path.append(os.path.dirname(__file__))
from canonicalize import canonicalize_request


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class WebTrafficDataset:
    """Dataset class for loading and processing web traffic logs."""
    
    def __init__(self, file_path: str, tokenizer, max_length: int = 256):
        """
        Initialize the dataset.
        
        Args:
            file_path: Path to the text file containing canonicalized logs
            tokenizer: Trained tokenizer instance
            max_length: Maximum sequence length
        """
        self.file_path = file_path
        self.tokenizer = tokenizer
        self.max_length = max_length
        
        # Load and validate data
        self.texts = self._load_texts()
        logger.info(f"Loaded {len(self.texts)} samples from {file_path}")
    
    def _load_texts(self):
        """Load texts from file and filter empty lines."""
        texts = []
        with open(self.file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:  # Skip empty lines
                    texts.append(line)
        return texts
    
    def tokenize_function(self, examples):
        """Tokenize examples for the dataset."""
        return self.tokenizer(
            examples['text'],
            truncation=True,
            padding=False,  # Dynamic padding handled by data collator
            max_length=self.max_length,
            return_special_tokens_mask=True
        )
    
    def get_dataset(self):
        """Convert to HuggingFace Dataset format."""
        # Create HuggingFace dataset
        dataset = HFDataset.from_dict({'text': self.texts})
        
        # Tokenize
        tokenized_dataset = dataset.map(
            self.tokenize_function,
            batched=True,
            remove_columns=['text'],
            desc="Tokenizing dataset"
        )
        
        return tokenized_dataset


class WebTrafficJSONDataset:
    """Dataset class for loading and processing JSON/JSONL web traffic logs."""
    
    def __init__(self, file_path: str, tokenizer, max_length: int = 256, max_samples: int = None):
        """
        Initialize the dataset for JSON/JSONL input.
        
        Args:
            file_path: Path to the JSON/JSONL file containing web request logs
            tokenizer: Trained tokenizer instance
            max_length: Maximum sequence length
            max_samples: Maximum number of samples to load (None for all)
        """
        self.file_path = file_path
        self.tokenizer = tokenizer
        self.max_length = max_length
        self.max_samples = max_samples
        
        # Load and canonicalize data
        self.texts = self._load_and_canonicalize()
        logger.info(f"Loaded and canonicalized {len(self.texts)} samples from {file_path}")
    
    def _load_and_canonicalize(self):
        """Load JSON data and canonicalize on-the-fly."""
        texts = []
        processed_count = 0
        error_count = 0
        
        with open(self.file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                if self.max_samples and processed_count >= self.max_samples:
                    break
                    
                line = line.strip()
                if not line:
                    continue
                
                try:
                    # Parse JSON line
                    log_entry = json.loads(line)
                    
                    # Canonicalize the log entry
                    canonical_text = canonicalize_request(log_entry)
                    
                    if canonical_text.strip():  # Only add non-empty canonicalized text
                        texts.append(canonical_text)
                        processed_count += 1
                        
                        if processed_count % 10000 == 0:
                            logger.info(f"  Processed {processed_count} entries...")
                            
                except (json.JSONDecodeError, KeyError, Exception) as e:
                    error_count += 1
                    if error_count <= 5:  # Show first 5 errors
                        logger.warning(f"Error processing line {line_num}: {e}")
                    continue
        
        logger.info(f"Canonicalization complete - Processed: {processed_count}, Errors: {error_count}")
        return texts
    
    def tokenize_function(self, examples):
        """Tokenize examples for the dataset."""
        return self.tokenizer(
            examples['text'],
            truncation=True,
            padding=False,  # Dynamic padding handled by data collator
            max_length=self.max_length,
            return_special_tokens_mask=True
        )
    
    def get_dataset(self):
        """Convert to HuggingFace Dataset format."""
        # Create HuggingFace dataset
        dataset = HFDataset.from_dict({'text': self.texts})
        
        # Tokenize
        tokenized_dataset = dataset.map(
            self.tokenize_function,
            batched=True,
            remove_columns=['text'],
            desc="Tokenizing dataset"
        )
        
        return tokenized_dataset


def create_model_config(vocab_size: int = 8000) -> RobertaConfig:
    """
    Create RoBERTa configuration for web traffic anomaly detection.
    
    Args:
        vocab_size: Size of the vocabulary
    
    Returns:
        RobertaConfig instance
    """
    config = RobertaConfig(
        vocab_size=vocab_size,
        max_position_embeddings=256,
        hidden_size=384,
        num_attention_heads=6,
        num_hidden_layers=6,
        intermediate_size=1536,  # 4 * hidden_size
        hidden_act="gelu",
        hidden_dropout_prob=0.1,
        attention_probs_dropout_prob=0.1,
        type_vocab_size=1,
        initializer_range=0.02,
        layer_norm_eps=1e-12,
        pad_token_id=0,
        bos_token_id=1,
        eos_token_id=2,
        position_embedding_type="absolute",
        use_cache=True,
        classifier_dropout=None
    )
    
    logger.info(f"Created model config: {config}")
    return config


def load_tokenizer(tokenizer_dir: str):
    """
    Load the trained tokenizer.
    
    Args:
        tokenizer_dir: Directory containing tokenizer files
    
    Returns:
        Loaded tokenizer
    """
    vocab_file = os.path.join(tokenizer_dir, "vocab.json")
    merges_file = os.path.join(tokenizer_dir, "merges.txt")
    
    if not os.path.exists(vocab_file) or not os.path.exists(merges_file):
        raise FileNotFoundError(f"Tokenizer files not found in {tokenizer_dir}")
    
    # Load ByteLevelBPE tokenizer
    tokenizer = ByteLevelBPETokenizer(vocab_file, merges_file)
    
    # Convert to RobertaTokenizer for compatibility with transformers
    # Create a temporary config
    temp_config = {
        "vocab_file": vocab_file,
        "merges_file": merges_file,
        "tokenizer_class": "RobertaTokenizer",
        "bos_token": "<s>",
        "eos_token": "</s>",
        "unk_token": "<unk>",
        "pad_token": "<pad>",
        "mask_token": "<mask>"
    }
    
    # Save temporary tokenizer config
    temp_dir = "temp_tokenizer"
    Path(temp_dir).mkdir(exist_ok=True)
    
    with open(os.path.join(temp_dir, "tokenizer_config.json"), 'w') as f:
        json.dump(temp_config, f)
    
    # Copy files to temp directory
    import shutil
    shutil.copy(vocab_file, os.path.join(temp_dir, "vocab.json"))
    shutil.copy(merges_file, os.path.join(temp_dir, "merges.txt"))
    
    # Load as RobertaTokenizer
    tokenizer = RobertaTokenizer.from_pretrained(temp_dir)
    
    # Cleanup
    shutil.rmtree(temp_dir)
    
    logger.info(f"Loaded tokenizer with vocab size: {tokenizer.vocab_size}")
    return tokenizer


def prepare_datasets(train_file: str, val_file: Optional[str], tokenizer, max_length: int = 256, max_samples: int = None):
    """
    Prepare training and validation datasets from text or JSON files.
    
    Args:
        train_file: Path to training data file (text or JSON/JSONL)
        val_file: Path to validation data file (optional)
        tokenizer: Tokenizer instance
        max_length: Maximum sequence length
        max_samples: Maximum number of samples to load (None for all)
    
    Returns:
        Tuple of (train_dataset, val_dataset)
    """
    # Detect file type and load accordingly
    if train_file.endswith(('.json', '.jsonl')):
        logger.info("Detected JSON/JSONL training file")
        train_dataset = WebTrafficJSONDataset(train_file, tokenizer, max_length, max_samples)
    else:
        logger.info("Detected text training file")
        train_dataset = WebTrafficDataset(train_file, tokenizer, max_length)
    
    train_hf_dataset = train_dataset.get_dataset()
    
    # Load validation dataset
    val_hf_dataset = None
    if val_file and os.path.exists(val_file):
        if val_file.endswith(('.json', '.jsonl')):
            logger.info("Detected JSON/JSONL validation file")
            val_dataset = WebTrafficJSONDataset(val_file, tokenizer, max_length, max_samples)
        else:
            logger.info("Detected text validation file")
            val_dataset = WebTrafficDataset(val_file, tokenizer, max_length)
        
        val_hf_dataset = val_dataset.get_dataset()
        logger.info(f"Loaded validation dataset with {len(val_hf_dataset)} samples")
    else:
        # Split training data for validation
        logger.info("No validation file provided, splitting training data")
        split_datasets = train_hf_dataset.train_test_split(test_size=0.1, seed=42)
        train_hf_dataset = split_datasets['train']
        val_hf_dataset = split_datasets['test']
        logger.info(f"Split into {len(train_hf_dataset)} train and {len(val_hf_dataset)} validation samples")
    
    return train_hf_dataset, val_hf_dataset


def train_model(
    train_file: str,
    tokenizer_dir: str,
    output_dir: str = "model",
    val_file: Optional[str] = None,
    max_length: int = 256,
    batch_size: int = 32,
    num_epochs: int = 3,
    learning_rate: float = 5e-4,
    warmup_steps: int = 500,
    save_steps: int = 1000,
    eval_steps: int = 1000,
    seed: int = 42,
    max_samples: int = None
):
    """
    Train the RoBERTa model for masked language modeling.
    
    Args:
        train_file: Path to training data file
        tokenizer_dir: Directory containing trained tokenizer
        output_dir: Directory to save model checkpoints
        val_file: Path to validation data file
        max_length: Maximum sequence length
        batch_size: Training batch size
        num_epochs: Number of training epochs
        learning_rate: Learning rate
        warmup_steps: Number of warmup steps
        save_steps: Save checkpoint every N steps
        eval_steps: Evaluate every N steps
        seed: Random seed
    """
    # Set seed for reproducibility
    set_seed(seed)
    
    # Create output directory
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    logger.info("Starting model training...")
    logger.info(f"Training file: {train_file}")
    logger.info(f"Tokenizer directory: {tokenizer_dir}")
    logger.info(f"Output directory: {output_dir}")
    
    # Load tokenizer
    tokenizer = load_tokenizer(tokenizer_dir)
    
    # Create model config and model
    config = create_model_config(vocab_size=tokenizer.vocab_size)
    model = RobertaForMaskedLM(config)
    
    logger.info(f"Model created with {model.num_parameters():,} parameters")
    
    # Prepare datasets
    train_dataset, val_dataset = prepare_datasets(train_file, val_file, tokenizer, max_length, max_samples)
    
    # Data collator for MLM
    data_collator = DataCollatorForLanguageModeling(
        tokenizer=tokenizer,
        mlm=True,
        mlm_probability=0.15,
        return_tensors="pt"
    )
    
    # Training arguments
    training_args = TrainingArguments(
        output_dir=os.path.join(output_dir, "checkpoints"),
        overwrite_output_dir=True,
        per_device_train_batch_size=batch_size,
        per_device_eval_batch_size=batch_size,
        num_train_epochs=num_epochs,
        learning_rate=learning_rate,
        warmup_steps=warmup_steps,
        logging_steps=100,
        save_steps=save_steps,
        eval_steps=eval_steps,
        eval_strategy="steps" if val_dataset else "no",
        save_strategy="steps",
        load_best_model_at_end=True if val_dataset else False,
        metric_for_best_model="eval_loss" if val_dataset else None,
        greater_is_better=False,
        fp16=torch.cuda.is_available(),  # Use mixed precision if CUDA available
        dataloader_pin_memory=True,
        dataloader_num_workers=4,
        remove_unused_columns=False,
        report_to=None,  # Disable wandb/tensorboard
        seed=seed,
        data_seed=seed,
    )
    
    # Initialize trainer
    trainer = Trainer(
        model=model,
        args=training_args,
        data_collator=data_collator,
        train_dataset=train_dataset,
        eval_dataset=val_dataset,
        tokenizer=tokenizer
    )
    
    # Train the model
    logger.info("Starting training...")
    trainer.train()
    
    # Save the final model
    logger.info(f"Saving final model to {output_dir}")
    trainer.save_model(output_dir)
    tokenizer.save_pretrained(output_dir)
    
    # Save training configuration
    training_config = {
        "model_config": config.to_dict(),
        "training_args": training_args.to_dict(),
        "tokenizer_dir": tokenizer_dir,
        "max_length": max_length,
        "vocab_size": tokenizer.vocab_size,
        "training_samples": len(train_dataset),
        "validation_samples": len(val_dataset) if val_dataset else 0
    }
    
    with open(os.path.join(output_dir, "training_config.json"), 'w') as f:
        json.dump(training_config, f, indent=2)
    
    logger.info("Training completed successfully!")
    
    # Print model info
    logger.info(f"Final model saved to: {output_dir}")
    logger.info(f"Model parameters: {model.num_parameters():,}")
    logger.info(f"Vocabulary size: {tokenizer.vocab_size}")


def main():
    """Main function to handle command line arguments and run training."""
    parser = argparse.ArgumentParser(
        description="Train RoBERTa model for web traffic anomaly detection",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    parser.add_argument(
        "train_file",
        help="Path to training data file (text or JSON/JSONL)"
    )
    
    parser.add_argument(
        "--tokenizer_dir",
        default="tokenizer",
        help="Directory containing trained tokenizer"
    )
    
    parser.add_argument(
        "--output_dir",
        default="model",
        help="Directory to save trained model"
    )
    
    parser.add_argument(
        "--val_file",
        help="Path to validation data file"
    )
    
    parser.add_argument(
        "--max_length",
        type=int,
        default=256,
        help="Maximum sequence length"
    )
    
    parser.add_argument(
        "--batch_size",
        type=int,
        default=32,
        help="Training batch size"
    )
    
    parser.add_argument(
        "--num_epochs",
        type=int,
        default=3,
        help="Number of training epochs"
    )
    
    parser.add_argument(
        "--learning_rate",
        type=float,
        default=5e-4,
        help="Learning rate"
    )
    
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed"
    )
    
    parser.add_argument(
        "--max_samples",
        type=int,
        help="Maximum number of samples to use for training (default: all)"
    )
    
    args = parser.parse_args()
    
    try:
        train_model(
            train_file=args.train_file,
            tokenizer_dir=args.tokenizer_dir,
            output_dir=args.output_dir,
            val_file=args.val_file,
            max_length=args.max_length,
            batch_size=args.batch_size,
            num_epochs=args.num_epochs,
            learning_rate=args.learning_rate,
            seed=args.seed,
            max_samples=args.max_samples
        )
        
    except Exception as e:
        logger.error(f"Training failed: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())