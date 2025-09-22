"""
Safe fine-tuning script for continuous learning in web traffic anomaly detection.

This script implements a safe fine-tuning approach using a replay buffer to
prevent catastrophic forgetting while adapting to new benign traffic patterns.
"""
import argparse
import os
import sys
import time
import logging
import json
import shutil
from pathlib import Path
from typing import List, Optional, Tuple
import random

import torch
from torch.utils.data import Dataset, DataLoader
from transformers import (
    RobertaForMaskedLM,
    RobertaTokenizer,
    DataCollatorForLanguageModeling,
    TrainingArguments,
    Trainer,
    set_seed
)
from datasets import Dataset as HFDataset
import numpy as np

# Add scripts directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '.'))
from scoring import PseudoLogLikelihoodScorer


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ReplayBuffer:
    """
    Replay buffer for storing and sampling previous training data.
    """
    
    def __init__(self, buffer_file: str, max_size: int = 10000):
        """
        Initialize replay buffer.
        
        Args:
            buffer_file: Path to file storing buffer data
            max_size: Maximum number of samples to store
        """
        self.buffer_file = buffer_file
        self.max_size = max_size
        self.samples = []
        
        # Load existing buffer if it exists
        if os.path.exists(buffer_file):
            self.load_buffer()
        
        logger.info(f"Replay buffer initialized with {len(self.samples)} samples")
    
    def load_buffer(self):
        """Load buffer from file."""
        try:
            with open(self.buffer_file, 'r', encoding='utf-8') as f:
                self.samples = [line.strip() for line in f if line.strip()]
            logger.info(f"Loaded {len(self.samples)} samples from buffer file")
        except Exception as e:
            logger.warning(f"Could not load buffer file: {e}")
            self.samples = []
    
    def save_buffer(self):
        """Save buffer to file."""
        try:
            with open(self.buffer_file, 'w', encoding='utf-8') as f:
                for sample in self.samples:
                    f.write(f"{sample}\n")
            logger.info(f"Saved {len(self.samples)} samples to buffer file")
        except Exception as e:
            logger.error(f"Could not save buffer file: {e}")
    
    def add_samples(self, new_samples: List[str]):
        """
        Add new samples to buffer with reservoir sampling.
        
        Args:
            new_samples: List of new samples to add
        """
        for sample in new_samples:
            if len(self.samples) < self.max_size:
                self.samples.append(sample)
            else:
                # Reservoir sampling: replace random sample
                idx = random.randint(0, len(self.samples) - 1)
                self.samples[idx] = sample
        
        logger.info(f"Added {len(new_samples)} samples to buffer (total: {len(self.samples)})")
    
    def sample_batch(self, batch_size: int) -> List[str]:
        """
        Sample a batch from the buffer.
        
        Args:
            batch_size: Number of samples to return
        
        Returns:
            List of sampled texts
        """
        if len(self.samples) == 0:
            return []
        
        if batch_size >= len(self.samples):
            return self.samples.copy()
        
        return random.sample(self.samples, batch_size)


class ContinualLearningDataset(Dataset):
    """
    Dataset that mixes new data with replay buffer samples.
    """
    
    def __init__(
        self,
        new_samples: List[str],
        replay_buffer: ReplayBuffer,
        tokenizer,
        replay_ratio: float = 0.9,
        max_length: int = 256
    ):
        """
        Initialize dataset.
        
        Args:
            new_samples: New training samples
            replay_buffer: Replay buffer instance
            tokenizer: Tokenizer for encoding
            replay_ratio: Fraction of batch that should come from replay buffer
            max_length: Maximum sequence length
        """
        self.new_samples = new_samples
        self.replay_buffer = replay_buffer
        self.tokenizer = tokenizer
        self.replay_ratio = replay_ratio
        self.max_length = max_length
        
        # Calculate sizes
        total_samples = len(new_samples)
        self.replay_size = int(total_samples * replay_ratio)
        self.new_size = total_samples - self.replay_size
        
        logger.info(f"Dataset created: {self.new_size} new + {self.replay_size} replay = {total_samples} total")
    
    def __len__(self):
        return len(self.new_samples)
    
    def __getitem__(self, idx):
        # Determine if this should be a new sample or replay sample
        if idx < self.new_size:
            # Use new sample
            text = self.new_samples[idx]
        else:
            # Sample from replay buffer
            replay_samples = self.replay_buffer.sample_batch(1)
            text = replay_samples[0] if replay_samples else self.new_samples[idx % self.new_size]
        
        # Tokenize
        encoding = self.tokenizer(
            text,
            truncation=True,
            max_length=self.max_length,
            padding=False,
            return_tensors="pt"
        )
        
        return {
            'input_ids': encoding['input_ids'].squeeze(),
            'attention_mask': encoding['attention_mask'].squeeze()
        }


def load_new_samples(file_path: str) -> List[str]:
    """
    Load new training samples from file.
    
    Args:
        file_path: Path to file containing new samples
    
    Returns:
        List of text samples
    """
    samples = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                samples.append(line)
    
    logger.info(f"Loaded {len(samples)} new samples from {file_path}")
    return samples


def validate_new_samples(
    model_path: str,
    new_samples: List[str],
    threshold_percentile: float = 95.0
) -> Tuple[List[str], float]:
    """
    Validate that new samples are actually benign by scoring them.
    
    Args:
        model_path: Path to current model
        new_samples: List of new samples to validate
        threshold_percentile: Percentile threshold for filtering
    
    Returns:
        Tuple of (filtered_samples, validation_threshold)
    """
    logger.info("Validating new samples for benign nature...")
    
    # Load model and tokenizer
    model = RobertaForMaskedLM.from_pretrained(model_path)
    tokenizer = RobertaTokenizer.from_pretrained(model_path)
    
    # Create scorer
    scorer = PseudoLogLikelihoodScorer(model, tokenizer)
    
    # Score all samples
    scores = []
    for sample in new_samples:
        try:
            inputs = tokenizer(sample, return_tensors="pt", truncation=True, max_length=256)
            input_ids = inputs['input_ids'].squeeze()
            score = scorer.pseudo_loglikelihood(input_ids)
            scores.append(score)
        except Exception as e:
            logger.warning(f"Error scoring sample: {e}")
            scores.append(float('inf'))  # Mark as suspicious
    
    # Calculate threshold
    threshold = np.percentile(scores, threshold_percentile)
    
    # Filter samples
    filtered_samples = []
    for sample, score in zip(new_samples, scores):
        if score <= threshold:
            filtered_samples.append(sample)
    
    logger.info(f"Validation results:")
    logger.info(f"  Original samples: {len(new_samples)}")
    logger.info(f"  Filtered samples: {len(filtered_samples)}")
    logger.info(f"  Validation threshold: {threshold:.4f}")
    logger.info(f"  Rejection rate: {(1 - len(filtered_samples)/len(new_samples))*100:.1f}%")
    
    return filtered_samples, threshold


def safe_finetune(
    model_path: str,
    new_samples_file: str,
    replay_buffer_file: str,
    output_path: str,
    learning_rate: float = 1e-6,
    num_steps: int = 100,
    batch_size: int = 8,
    replay_ratio: float = 0.9,
    validate_samples: bool = True,
    backup_model: bool = True,
    seed: int = 42
):
    """
    Perform safe fine-tuning with replay buffer.
    
    Args:
        model_path: Path to current model
        new_samples_file: Path to file with new benign samples
        replay_buffer_file: Path to replay buffer file
        output_path: Path to save updated model
        learning_rate: Learning rate for fine-tuning
        num_steps: Number of training steps
        batch_size: Training batch size
        replay_ratio: Fraction of batch from replay buffer
        validate_samples: Whether to validate new samples
        backup_model: Whether to backup original model
        seed: Random seed
    """
    set_seed(seed)
    
    logger.info("Starting safe fine-tuning process...")
    logger.info(f"Model path: {model_path}")
    logger.info(f"New samples file: {new_samples_file}")
    logger.info(f"Replay buffer file: {replay_buffer_file}")
    logger.info(f"Output path: {output_path}")
    logger.info(f"Learning rate: {learning_rate}")
    logger.info(f"Training steps: {num_steps}")
    logger.info(f"Replay ratio: {replay_ratio}")
    
    # Create output directory
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    
    # Backup original model if requested
    if backup_model:
        backup_path = f"{model_path}_backup_{int(time.time())}"
        logger.info(f"Backing up original model to: {backup_path}")
        shutil.copytree(model_path, backup_path)
    
    # Load new samples
    new_samples = load_new_samples(new_samples_file)
    
    if len(new_samples) == 0:
        logger.error("No new samples found")
        return
    
    # Validate new samples if requested
    if validate_samples:
        new_samples, validation_threshold = validate_new_samples(model_path, new_samples)
        
        if len(new_samples) == 0:
            logger.error("No samples passed validation")
            return
    
    # Initialize replay buffer
    replay_buffer = ReplayBuffer(replay_buffer_file)
    
    # Load model and tokenizer
    logger.info("Loading model and tokenizer...")
    model = RobertaForMaskedLM.from_pretrained(model_path)
    tokenizer = RobertaTokenizer.from_pretrained(model_path)
    
    # Create mixed dataset
    dataset = ContinualLearningDataset(
        new_samples=new_samples,
        replay_buffer=replay_buffer,
        tokenizer=tokenizer,
        replay_ratio=replay_ratio
    )
    
    # Convert to HuggingFace dataset
    def tokenize_function(examples):
        return examples
    
    # Create simple dataset from our custom dataset
    all_samples = []
    for i in range(len(dataset)):
        item = dataset[i]
        all_samples.append({
            'input_ids': item['input_ids'].tolist(),
            'attention_mask': item['attention_mask'].tolist()
        })
    
    hf_dataset = HFDataset.from_list(all_samples)
    
    # Data collator
    data_collator = DataCollatorForLanguageModeling(
        tokenizer=tokenizer,
        mlm=True,
        mlm_probability=0.15,
        return_tensors="pt"
    )
    
    # Training arguments for fine-tuning
    training_args = TrainingArguments(
        output_dir=f"{output_path}_temp",
        overwrite_output_dir=True,
        per_device_train_batch_size=batch_size,
        max_steps=num_steps,
        learning_rate=learning_rate,
        warmup_steps=10,
        logging_steps=10,
        save_steps=num_steps,  # Save only at the end
        save_strategy="steps",
        fp16=torch.cuda.is_available(),
        dataloader_pin_memory=True,
        remove_unused_columns=False,
        report_to=None,
        seed=seed,
        data_seed=seed,
        lr_scheduler_type="constant"  # Keep learning rate constant
    )
    
    # Initialize trainer
    trainer = Trainer(
        model=model,
        args=training_args,
        data_collator=data_collator,
        train_dataset=hf_dataset,
        tokenizer=tokenizer
    )
    
    # Fine-tune the model
    logger.info("Starting fine-tuning...")
    trainer.train()
    
    # Save the updated model
    logger.info(f"Saving updated model to: {output_path}")
    trainer.save_model(output_path)
    tokenizer.save_pretrained(output_path)
    
    # Update replay buffer with new samples
    replay_buffer.add_samples(new_samples)
    replay_buffer.save_buffer()
    
    # Save fine-tuning metadata
    metadata = {
        "timestamp": time.time(),
        "original_model": model_path,
        "new_samples_count": len(new_samples),
        "replay_buffer_size": len(replay_buffer.samples),
        "learning_rate": learning_rate,
        "num_steps": num_steps,
        "batch_size": batch_size,
        "replay_ratio": replay_ratio,
        "validation_enabled": validate_samples,
        "validation_threshold": validation_threshold if validate_samples else None
    }
    
    metadata_file = os.path.join(output_path, "finetune_metadata.json")
    with open(metadata_file, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    # Cleanup temporary directory
    temp_dir = f"{output_path}_temp"
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
    
    logger.info("Safe fine-tuning completed successfully!")
    logger.info(f"Updated model saved to: {output_path}")
    logger.info(f"Replay buffer updated with {len(new_samples)} new samples")


def main():
    """Main function to handle command line arguments and run fine-tuning."""
    parser = argparse.ArgumentParser(
        description="Safe fine-tuning for continual learning",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    parser.add_argument(
        "model_path",
        help="Path to current model directory"
    )
    
    parser.add_argument(
        "new_samples_file",
        help="Path to file containing new benign samples"
    )
    
    parser.add_argument(
        "replay_buffer_file",
        help="Path to replay buffer file"
    )
    
    parser.add_argument(
        "--output_path",
        help="Path to save updated model (default: model_path + '_updated')"
    )
    
    parser.add_argument(
        "--learning_rate",
        type=float,
        default=1e-6,
        help="Learning rate for fine-tuning"
    )
    
    parser.add_argument(
        "--num_steps",
        type=int,
        default=100,
        help="Number of training steps"
    )
    
    parser.add_argument(
        "--batch_size",
        type=int,
        default=8,
        help="Training batch size"
    )
    
    parser.add_argument(
        "--replay_ratio",
        type=float,
        default=0.9,
        help="Fraction of batch from replay buffer"
    )
    
    parser.add_argument(
        "--no_validation",
        action="store_true",
        help="Skip validation of new samples"
    )
    
    parser.add_argument(
        "--no_backup",
        action="store_true",
        help="Skip backing up original model"
    )
    
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed"
    )
    
    args = parser.parse_args()
    
    # Set output path if not provided
    if not args.output_path:
        args.output_path = f"{args.model_path}_updated"
    
    # Validate inputs
    if not os.path.exists(args.model_path):
        logger.error(f"Model path not found: {args.model_path}")
        return 1
    
    if not os.path.exists(args.new_samples_file):
        logger.error(f"New samples file not found: {args.new_samples_file}")
        return 1
    
    try:
        safe_finetune(
            model_path=args.model_path,
            new_samples_file=args.new_samples_file,
            replay_buffer_file=args.replay_buffer_file,
            output_path=args.output_path,
            learning_rate=args.learning_rate,
            num_steps=args.num_steps,
            batch_size=args.batch_size,
            replay_ratio=args.replay_ratio,
            validate_samples=not args.no_validation,
            backup_model=not args.no_backup,
            seed=args.seed
        )
        
    except Exception as e:
        logger.error(f"Fine-tuning failed: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())