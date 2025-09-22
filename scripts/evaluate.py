"""
Evaluation script for web traffic anomaly detection model.

This script evaluates model performance on labeled test data and provides
recommendations for production thresholds based on various metrics.
"""
import argparse
import os
import sys
import time
import logging
from pathlib import Path
from typing import List, Tuple, Dict

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import roc_auc_score, roc_curve, precision_recall_curve
from sklearn.metrics import classification_report, confusion_matrix
import torch
from transformers import RobertaForMaskedLM, RobertaTokenizer

# Add scripts directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '.'))
from scoring import PseudoLogLikelihoodScorer
from canonicalize import canonicalize_request


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ModelEvaluator:
    """
    Comprehensive evaluation of anomaly detection model performance.
    """
    
    def __init__(self, model_dir: str, device: str = "auto"):
        """
        Initialize the evaluator.
        
        Args:
            model_dir: Directory containing trained model
            device: Device to run evaluation on
        """
        self.model_dir = model_dir
        
        # Load model and tokenizer
        logger.info(f"Loading model from: {model_dir}")
        self.model = RobertaForMaskedLM.from_pretrained(model_dir)
        self.tokenizer = RobertaTokenizer.from_pretrained(model_dir)
        
        # Initialize scorer
        self.scorer = PseudoLogLikelihoodScorer(self.model, self.tokenizer, device)
        
        logger.info("Model evaluator initialized")
    
    def load_test_data(self, test_file: str) -> Tuple[List[str], List[int]]:
        """
        Load test data from CSV file.
        
        Expected format: CSV with columns 'text' and 'label'
        where label is 1 for attack, 0 for benign.
        
        Args:
            test_file: Path to test data CSV file
        
        Returns:
            Tuple of (texts, labels)
        """
        logger.info(f"Loading test data from: {test_file}")
        
        # Read CSV file
        df = pd.read_csv(test_file)
        
        # Validate required columns
        required_columns = ['text', 'label']
        for col in required_columns:
            if col not in df.columns:
                raise ValueError(f"Required column '{col}' not found in {test_file}")
        
        # Extract texts and labels
        texts = df['text'].tolist()
        labels = df['label'].tolist()
        
        # Validate labels
        unique_labels = set(labels)
        if not unique_labels.issubset({0, 1}):
            raise ValueError(f"Labels must be 0 (benign) or 1 (attack), found: {unique_labels}")
        
        logger.info(f"Loaded {len(texts)} samples")
        logger.info(f"Label distribution: {pd.Series(labels).value_counts().to_dict()}")
        
        return texts, labels
    
    def score_samples(self, texts: List[str]) -> List[float]:
        """
        Score a list of text samples.
        
        Args:
            texts: List of text samples to score
        
        Returns:
            List of anomaly scores
        """
        scores = []
        latencies = []
        
        logger.info(f"Scoring {len(texts)} samples...")
        
        for i, text in enumerate(texts):
            if i % 100 == 0:
                logger.info(f"Processed {i}/{len(texts)} samples")
            
            start_time = time.time()
            
            try:
                # Tokenize
                inputs = self.tokenizer(
                    text,
                    return_tensors="pt",
                    truncation=True,
                    max_length=256,
                    padding=False
                )
                
                input_ids = inputs['input_ids'].squeeze()
                
                # Score
                score = self.scorer.pseudo_loglikelihood(input_ids)
                scores.append(score)
                
                # Track latency
                latency = (time.time() - start_time) * 1000  # ms
                latencies.append(latency)
                
            except Exception as e:
                logger.warning(f"Error scoring sample {i}: {e}")
                scores.append(0.0)
                latencies.append(0.0)
        
        logger.info("Scoring completed")
        
        # Log latency statistics
        if latencies:
            self.latencies = latencies
            logger.info(f"Latency statistics (ms):")
            logger.info(f"  P50: {np.percentile(latencies, 50):.2f}")
            logger.info(f"  P95: {np.percentile(latencies, 95):.2f}")
            logger.info(f"  P99: {np.percentile(latencies, 99):.2f}")
            logger.info(f"  Mean: {np.mean(latencies):.2f}")
            logger.info(f"  Std: {np.std(latencies):.2f}")
        
        return scores
    
    def calculate_metrics(self, scores: List[float], labels: List[int]) -> Dict:
        """
        Calculate comprehensive evaluation metrics.
        
        Args:
            scores: Anomaly scores
            labels: True labels (0=benign, 1=attack)
        
        Returns:
            Dictionary of metrics
        """
        scores = np.array(scores)
        labels = np.array(labels)
        
        # ROC AUC
        roc_auc = roc_auc_score(labels, scores)
        
        # ROC curve
        fpr, tpr, thresholds = roc_curve(labels, scores)
        
        # Precision-Recall curve
        precision, recall, pr_thresholds = precision_recall_curve(labels, scores)
        
        # Find optimal threshold (Youden's J statistic)
        j_scores = tpr - fpr
        optimal_idx = np.argmax(j_scores)
        optimal_threshold = thresholds[optimal_idx]
        
        # Precision at specific FPR (0.1%)
        target_fpr = 0.001
        fpr_idx = np.where(fpr <= target_fpr)[0]
        if len(fpr_idx) > 0:
            precision_at_001_fpr = tpr[fpr_idx[-1]]
        else:
            precision_at_001_fpr = 0.0
        
        # Calculate metrics at optimal threshold
        predictions = (scores > optimal_threshold).astype(int)
        
        metrics = {
            'roc_auc': roc_auc,
            'optimal_threshold': optimal_threshold,
            'precision_at_001_fpr': precision_at_001_fpr,
            'fpr': fpr,
            'tpr': tpr,
            'roc_thresholds': thresholds,
            'precision': precision,
            'recall': recall,
            'pr_thresholds': pr_thresholds,
            'predictions': predictions,
            'scores': scores,
            'labels': labels
        }
        
        logger.info(f"Evaluation Metrics:")
        logger.info(f"  ROC AUC: {roc_auc:.4f}")
        logger.info(f"  Optimal Threshold: {optimal_threshold:.4f}")
        logger.info(f"  Precision at 0.1% FPR: {precision_at_001_fpr:.4f}")
        
        return metrics
    
    def calculate_production_threshold(self, benign_scores: List[float], percentile: float = 99.9) -> float:
        """
        Calculate recommended production threshold based on benign data.
        
        Args:
            benign_scores: Scores from benign validation set
            percentile: Percentile to use for threshold
        
        Returns:
            Recommended threshold
        """
        threshold = np.percentile(benign_scores, percentile)
        logger.info(f"Recommended Production Threshold: {threshold:.4f} (at {percentile}th percentile)")
        return threshold
    
    def generate_roc_plot(self, metrics: Dict, output_file: str = "roc_curve.png"):
        """
        Generate and save ROC curve plot.
        
        Args:
            metrics: Metrics dictionary from calculate_metrics
            output_file: Output file path
        """
        plt.figure(figsize=(10, 8))
        
        # Main ROC curve
        plt.subplot(2, 2, 1)
        plt.plot(metrics['fpr'], metrics['tpr'], 'b-', lw=2, 
                label=f'ROC (AUC = {metrics["roc_auc"]:.4f})')
        plt.plot([0, 1], [0, 1], 'r--', lw=1, label='Random')
        plt.xlim([0.0, 1.0])
        plt.ylim([0.0, 1.05])
        plt.xlabel('False Positive Rate')
        plt.ylabel('True Positive Rate')
        plt.title('ROC Curve')
        plt.legend(loc="lower right")
        plt.grid(True, alpha=0.3)
        
        # Zoomed ROC curve (low FPR region)
        plt.subplot(2, 2, 2)
        mask = metrics['fpr'] <= 0.1
        plt.plot(metrics['fpr'][mask], metrics['tpr'][mask], 'b-', lw=2)
        plt.xlim([0.0, 0.1])
        plt.ylim([0.0, 1.05])
        plt.xlabel('False Positive Rate')
        plt.ylabel('True Positive Rate')
        plt.title('ROC Curve (Zoomed: FPR ≤ 0.1)')
        plt.grid(True, alpha=0.3)
        
        # Precision-Recall curve
        plt.subplot(2, 2, 3)
        plt.plot(metrics['recall'], metrics['precision'], 'g-', lw=2)
        plt.xlim([0.0, 1.0])
        plt.ylim([0.0, 1.05])
        plt.xlabel('Recall')
        plt.ylabel('Precision')
        plt.title('Precision-Recall Curve')
        plt.grid(True, alpha=0.3)
        
        # Score distribution
        plt.subplot(2, 2, 4)
        benign_scores = metrics['scores'][metrics['labels'] == 0]
        attack_scores = metrics['scores'][metrics['labels'] == 1]
        
        plt.hist(benign_scores, bins=50, alpha=0.7, label='Benign', density=True)
        plt.hist(attack_scores, bins=50, alpha=0.7, label='Attack', density=True)
        plt.axvline(metrics['optimal_threshold'], color='red', linestyle='--', 
                   label=f'Optimal Threshold: {metrics["optimal_threshold"]:.2f}')
        plt.xlabel('Anomaly Score')
        plt.ylabel('Density')
        plt.title('Score Distribution')
        plt.legend()
        plt.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        logger.info(f"ROC curve plot saved to: {output_file}")
        plt.close()
    
    def print_classification_report(self, metrics: Dict):
        """Print detailed classification report."""
        report = classification_report(
            metrics['labels'], 
            metrics['predictions'],
            target_names=['Benign', 'Attack'],
            digits=4
        )
        
        logger.info(f"Classification Report:\n{report}")
        
        # Confusion matrix
        cm = confusion_matrix(metrics['labels'], metrics['predictions'])
        logger.info(f"Confusion Matrix:")
        logger.info(f"                Predicted")
        logger.info(f"Actual    Benign  Attack")
        logger.info(f"Benign    {cm[0,0]:6d}  {cm[0,1]:6d}")
        logger.info(f"Attack    {cm[1,0]:6d}  {cm[1,1]:6d}")


def evaluate_model(
    model_dir: str,
    test_file: str,
    benign_file: Optional[str] = None,
    output_dir: str = ".",
    device: str = "auto"
):
    """
    Run comprehensive model evaluation.
    
    Args:
        model_dir: Directory containing trained model
        test_file: Path to labeled test data CSV
        benign_file: Path to separate benign validation data (optional)
        output_dir: Directory to save outputs
        device: Device for evaluation
    """
    # Create output directory
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    # Initialize evaluator
    evaluator = ModelEvaluator(model_dir, device)
    
    # Load and score test data
    texts, labels = evaluator.load_test_data(test_file)
    scores = evaluator.score_samples(texts)
    
    # Calculate metrics
    metrics = evaluator.calculate_metrics(scores, labels)
    
    # Print results
    evaluator.print_classification_report(metrics)
    
    # Generate ROC plot
    roc_plot_path = os.path.join(output_dir, "roc_curve.png")
    evaluator.generate_roc_plot(metrics, roc_plot_path)
    
    # Calculate production threshold from benign data
    if benign_file and os.path.exists(benign_file):
        logger.info("Loading separate benign validation data for threshold calculation")
        benign_texts, _ = evaluator.load_test_data(benign_file)
        benign_scores = evaluator.score_samples(benign_texts)
    else:
        # Use benign samples from test set
        logger.info("Using benign samples from test set for threshold calculation")
        benign_mask = np.array(labels) == 0
        benign_scores = np.array(scores)[benign_mask].tolist()
    
    prod_threshold = evaluator.calculate_production_threshold(benign_scores, percentile=99.9)
    
    # Save evaluation results
    results = {
        'roc_auc': metrics['roc_auc'],
        'optimal_threshold': metrics['optimal_threshold'],
        'production_threshold': prod_threshold,
        'precision_at_001_fpr': metrics['precision_at_001_fpr'],
        'latency_p50': np.percentile(evaluator.latencies, 50) if hasattr(evaluator, 'latencies') else None,
        'latency_p95': np.percentile(evaluator.latencies, 95) if hasattr(evaluator, 'latencies') else None,
        'latency_p99': np.percentile(evaluator.latencies, 99) if hasattr(evaluator, 'latencies') else None,
        'test_samples': len(texts),
        'benign_samples': len([l for l in labels if l == 0]),
        'attack_samples': len([l for l in labels if l == 1])
    }
    
    results_file = os.path.join(output_dir, "evaluation_results.json")
    import json
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    logger.info(f"Evaluation results saved to: {results_file}")
    logger.info("Evaluation completed successfully!")


def main():
    """Main function to handle command line arguments and run evaluation."""
    parser = argparse.ArgumentParser(
        description="Evaluate anomaly detection model performance",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    parser.add_argument(
        "test_file",
        help="Path to labeled test data CSV (columns: text, label)"
    )
    
    parser.add_argument(
        "--model_dir",
        default="model",
        help="Directory containing trained model"
    )
    
    parser.add_argument(
        "--benign_file",
        help="Path to separate benign validation data for threshold calculation"
    )
    
    parser.add_argument(
        "--output_dir",
        default=".",
        help="Directory to save evaluation outputs"
    )
    
    parser.add_argument(
        "--device",
        default="auto",
        choices=["auto", "cpu", "cuda"],
        help="Device for evaluation"
    )
    
    args = parser.parse_args()
    
    # Validate inputs
    if not os.path.exists(args.test_file):
        logger.error(f"Test file not found: {args.test_file}")
        return 1
    
    if not os.path.exists(args.model_dir):
        logger.error(f"Model directory not found: {args.model_dir}")
        return 1
    
    try:
        evaluate_model(
            model_dir=args.model_dir,
            test_file=args.test_file,
            benign_file=args.benign_file,
            output_dir=args.output_dir,
            device=args.device
        )
        
    except Exception as e:
        logger.error(f"Evaluation failed: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())