"""
Pseudo Log-Likelihood (PLL) scoring for anomaly detection in web traffic.

This module implements an optimized PLL calculation that uses a single batched
forward pass to compute anomaly scores for web request sequences.
"""
import torch
import torch.nn.functional as F
from typing import Tuple, List, Dict, Optional
import logging
from transformers import RobertaForMaskedLM, RobertaTokenizer
import numpy as np


logger = logging.getLogger(__name__)


class PseudoLogLikelihoodScorer:
    """
    Optimized Pseudo Log-Likelihood scorer for anomaly detection.
    
    This class implements an efficient PLL calculation using a single batched
    forward pass to score sequences for anomaly detection.
    """
    
    def __init__(self, model: RobertaForMaskedLM, tokenizer: RobertaTokenizer, device: str = "auto"):
        """
        Initialize the PLL scorer.
        
        Args:
            model: Trained RoBERTa model for masked language modeling
            tokenizer: Corresponding tokenizer
            device: Device to run inference on ("auto", "cpu", "cuda")
        """
        self.model = model
        self.tokenizer = tokenizer
        
        # Set device
        if device == "auto":
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        else:
            self.device = torch.device(device)
        
        self.model.to(self.device)
        self.model.eval()
        
        # Get special token IDs
        self.mask_token_id = tokenizer.mask_token_id
        self.pad_token_id = tokenizer.pad_token_id
        self.bos_token_id = tokenizer.bos_token_id
        self.eos_token_id = tokenizer.eos_token_id
        
        logger.info(f"PLL Scorer initialized on device: {self.device}")
        logger.info(f"Mask token ID: {self.mask_token_id}")
    
    def pseudo_loglikelihood(self, input_ids: torch.Tensor) -> float:
        """
        Calculate the Pseudo Log-Likelihood score for a sequence.
        
        This implementation uses a single batched forward pass for efficiency:
        1. Create a batch by repeating input_ids L times
        2. Mask one position in each copy
        3. Run single forward pass on entire batch
        4. Extract and sum log probabilities
        
        Args:
            input_ids: Input token IDs tensor of shape (L,)
        
        Returns:
            Negative PLL score (higher = more anomalous)
        """
        with torch.inference_mode():
            # Ensure input is on correct device
            input_ids = input_ids.to(self.device)
            
            # Get sequence length (excluding special tokens)
            seq_length = input_ids.size(0)
            
            # Handle edge cases
            if seq_length == 0:
                return 0.0
            
            # Filter out special tokens for masking
            # We don't want to mask BOS, EOS, or PAD tokens
            maskable_positions = []
            for i, token_id in enumerate(input_ids):
                if token_id not in [self.pad_token_id, self.bos_token_id, self.eos_token_id]:
                    maskable_positions.append(i)
            
            if len(maskable_positions) == 0:
                return 0.0
            
            # Create batch for efficient computation
            # Shape: (num_maskable_positions, seq_length)
            batch_input_ids = input_ids.unsqueeze(0).repeat(len(maskable_positions), 1)
            
            # Mask one position in each row
            original_tokens = []
            for batch_idx, pos in enumerate(maskable_positions):
                original_tokens.append(input_ids[pos].item())
                batch_input_ids[batch_idx, pos] = self.mask_token_id
            
            # Single forward pass for entire batch
            outputs = self.model(batch_input_ids)
            logits = outputs.logits  # Shape: (batch_size, seq_length, vocab_size)
            
            # Extract logits for masked positions only
            # Shape: (batch_size, vocab_size)
            masked_logits = logits[range(len(maskable_positions)), maskable_positions]
            
            # Apply log softmax to get log probabilities
            log_probs = F.log_softmax(masked_logits, dim=-1)
            
            # Gather log probabilities for original tokens
            original_token_ids = torch.tensor(original_tokens, device=self.device)
            token_log_probs = log_probs.gather(1, original_token_ids.unsqueeze(1)).squeeze(1)
            
            # Sum log probabilities to get total PLL
            total_pll = token_log_probs.sum().item()
            
            # Return negative PLL as anomaly score (higher = more anomalous)
            return -total_pll
    
    def score_with_explanation(self, input_ids: torch.Tensor, top_k: int = 5) -> Tuple[float, List[Dict]]:
        """
        Calculate PLL score and provide token-level explanations.
        
        Args:
            input_ids: Input token IDs tensor of shape (L,)
            top_k: Number of most anomalous tokens to return in explanation
        
        Returns:
            Tuple of (anomaly_score, token_explanations)
            where token_explanations is a list of dicts with 'token', 'logprob', 'position'
        """
        with torch.inference_mode():
            input_ids = input_ids.to(self.device)
            seq_length = input_ids.size(0)
            
            if seq_length == 0:
                return 0.0, []
            
            # Filter maskable positions
            maskable_positions = []
            for i, token_id in enumerate(input_ids):
                if token_id not in [self.pad_token_id, self.bos_token_id, self.eos_token_id]:
                    maskable_positions.append(i)
            
            if len(maskable_positions) == 0:
                return 0.0, []
            
            # Create batch
            batch_input_ids = input_ids.unsqueeze(0).repeat(len(maskable_positions), 1)
            original_tokens = []
            
            for batch_idx, pos in enumerate(maskable_positions):
                original_tokens.append(input_ids[pos].item())
                batch_input_ids[batch_idx, pos] = self.mask_token_id
            
            # Forward pass
            outputs = self.model(batch_input_ids)
            logits = outputs.logits
            
            # Extract masked logits and compute log probabilities
            masked_logits = logits[range(len(maskable_positions)), maskable_positions]
            log_probs = F.log_softmax(masked_logits, dim=-1)
            
            # Get log probabilities for original tokens
            original_token_ids = torch.tensor(original_tokens, device=self.device)
            token_log_probs = log_probs.gather(1, original_token_ids.unsqueeze(1)).squeeze(1)
            
            # Total anomaly score
            total_score = -token_log_probs.sum().item()
            
            # Create explanations
            explanations = []
            for i, (pos, token_id, log_prob) in enumerate(
                zip(maskable_positions, original_tokens, token_log_probs.cpu().numpy())
            ):
                token_str = self.tokenizer.decode([token_id])
                explanations.append({
                    'token': token_str,
                    'logprob': float(log_prob),
                    'position': pos,
                    'anomaly_contribution': -float(log_prob)
                })
            
            # Sort by anomaly contribution (most anomalous first)
            explanations.sort(key=lambda x: x['anomaly_contribution'], reverse=True)
            
            return total_score, explanations[:top_k]
    
    def batch_score(self, batch_input_ids: torch.Tensor) -> List[float]:
        """
        Score a batch of sequences efficiently.
        
        Args:
            batch_input_ids: Batch of input sequences, shape (batch_size, seq_length)
        
        Returns:
            List of anomaly scores
        """
        scores = []
        for input_ids in batch_input_ids:
            # Remove padding tokens from each sequence
            non_pad_mask = input_ids != self.pad_token_id
            if non_pad_mask.any():
                cleaned_input_ids = input_ids[non_pad_mask]
                score = self.pseudo_loglikelihood(cleaned_input_ids)
            else:
                score = 0.0
            scores.append(score)
        
        return scores


def pseudo_loglikelihood(model: RobertaForMaskedLM, input_ids: torch.Tensor) -> float:
    """
    Standalone function for calculating Pseudo Log-Likelihood.
    
    This is a convenience function that matches the original specification
    but uses the optimized implementation from PseudoLogLikelihoodScorer.
    
    Args:
        model: Trained RoBERTa model
        input_ids: Input token IDs tensor of shape (L,)
    
    Returns:
        Negative PLL score (higher = more anomalous)
    """
    # Create a temporary scorer (less efficient than reusing scorer instance)
    device = next(model.parameters()).device
    
    with torch.inference_mode():
        input_ids = input_ids.to(device)
        seq_length = input_ids.size(0)
        
        if seq_length == 0:
            return 0.0
        
        # Get mask token ID from model config
        mask_token_id = model.config.mask_token_id
        if mask_token_id is None:
            # Fallback: assume mask token is at a standard position
            mask_token_id = model.config.vocab_size - 1
        
        # Filter positions to mask (avoid special tokens)
        # Note: This is a simplified version without tokenizer access
        maskable_positions = list(range(seq_length))
        
        # Create batch
        batch_input_ids = input_ids.unsqueeze(0).repeat(len(maskable_positions), 1)
        original_tokens = input_ids.clone()
        
        # Mask each position
        for batch_idx, pos in enumerate(maskable_positions):
            batch_input_ids[batch_idx, pos] = mask_token_id
        
        # Forward pass
        outputs = model(batch_input_ids)
        logits = outputs.logits
        
        # Extract logits for masked positions
        masked_logits = logits[range(len(maskable_positions)), maskable_positions]
        log_probs = F.log_softmax(masked_logits, dim=-1)
        
        # Get log probabilities for original tokens
        token_log_probs = log_probs.gather(1, original_tokens.unsqueeze(1)).squeeze(1)
        
        # Return negative sum as anomaly score
        return -token_log_probs.sum().item()


class AnomalyThreshold:
    """Helper class for managing anomaly detection thresholds."""
    
    def __init__(self, threshold: float = 50.0):
        """
        Initialize with a threshold value.
        
        Args:
            threshold: Anomaly threshold (scores above this are considered anomalous)
        """
        self.threshold = threshold
    
    def is_anomalous(self, score: float) -> bool:
        """Check if a score indicates an anomaly."""
        return score > self.threshold
    
    def calibrate_threshold(self, benign_scores: List[float], percentile: float = 99.9) -> float:
        """
        Calibrate threshold based on benign data distribution.
        
        Args:
            benign_scores: List of scores from benign samples
            percentile: Percentile to use as threshold
        
        Returns:
            Calibrated threshold value
        """
        self.threshold = np.percentile(benign_scores, percentile)
        logger.info(f"Threshold calibrated to {self.threshold:.4f} at {percentile}th percentile")
        return self.threshold


# Example usage and testing
if __name__ == "__main__":
    # This would be used for testing the scoring functions
    print("PLL Scoring module loaded successfully")
    print("Note: This module requires a trained model and tokenizer for actual scoring")
    
    # Example of how to use:
    """
    from transformers import RobertaForMaskedLM, RobertaTokenizer
    
    # Load model and tokenizer
    model = RobertaForMaskedLM.from_pretrained("model/")
    tokenizer = RobertaTokenizer.from_pretrained("model/")
    
    # Create scorer
    scorer = PseudoLogLikelihoodScorer(model, tokenizer)
    
    # Score a request
    text = "[METHOD] GET [PATH] /api/test [PARAMS] id=123 [HEADERS] content-type:application/json"
    inputs = tokenizer(text, return_tensors="pt")
    score = scorer.pseudo_loglikelihood(inputs['input_ids'].squeeze())
    
    print(f"Anomaly score: {score}")
    """