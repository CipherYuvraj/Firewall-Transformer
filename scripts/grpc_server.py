#!/usr/bin/env python3
"""
gRPC server for real-time anomaly detection inference.

This server provides a production-ready gRPC interface for scoring web traffic
using the trained Transformer model.
"""

import grpc
from concurrent import futures
import argparse
import logging
import signal
import sys
import os
import json
from typing import List, Dict, Any

# Add scripts directory to path
sys.path.append(os.path.dirname(__file__))

import anomaly_detection_pb2
import anomaly_detection_pb2_grpc
from transformers import RobertaForMaskedLM, RobertaTokenizer
from scoring import PseudoLogLikelihoodScorer
from canonicalize import canonicalize_request

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AnomalyDetectionServicer(anomaly_detection_pb2_grpc.AnomalyDetectionServicer):
    """
    gRPC servicer for anomaly detection.
    """
    
    def __init__(self, model_path: str, threshold: float = None):
        """
        Initialize the anomaly detection servicer.
        
        Args:
            model_path: Path to the trained model directory
            threshold: Anomaly detection threshold (if None, will be adaptive)
        """
        logger.info(f"Loading model from: {model_path}")
        
        # Load model and tokenizer
        self.model = RobertaForMaskedLM.from_pretrained(model_path)
        self.tokenizer = RobertaTokenizer.from_pretrained(model_path)
        
        # Initialize scorer
        self.scorer = PseudoLogLikelihoodScorer(self.model, self.tokenizer)
        
        # Set threshold
        self.threshold = threshold if threshold is not None else -10.0  # Default threshold
        
        logger.info(f"Model loaded successfully with {self.model.num_parameters():,} parameters")
        logger.info(f"Tokenizer loaded with vocab size: {self.tokenizer.vocab_size}")
        logger.info(f"Anomaly threshold set to: {self.threshold}")
    
    def ScoreRequest(self, request, context):
        """
        Score a single web request for anomaly detection.
        """
        try:
            # Canonicalize the request
            canonical_text = self._canonicalize_web_request(request)
            
            # Tokenize and score
            inputs = self.tokenizer(
                canonical_text, 
                return_tensors="pt", 
                truncation=True, 
                max_length=256
            )
            
            score = float(self.scorer.pseudo_loglikelihood(inputs['input_ids'].squeeze()))
            is_anomaly = score > self.threshold
            
            logger.debug(f"Scored request: {canonical_text[:100]}... -> {score:.4f}")
            
            return anomaly_detection_pb2.ScoreResponse(
                score=score,
                is_anomaly=is_anomaly,
                threshold=self.threshold,
                canonical_text=canonical_text
            )
            
        except Exception as e:
            logger.error(f"Error scoring request: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Scoring error: {str(e)}")
            return anomaly_detection_pb2.ScoreResponse()
    
    def ScoreBatch(self, request, context):
        """
        Score a batch of web requests.
        """
        try:
            results = []
            
            for req in request.requests:
                # Canonicalize the request
                canonical_text = self._canonicalize_web_request(req)
                
                # Tokenize and score
                inputs = self.tokenizer(
                    canonical_text, 
                    return_tensors="pt", 
                    truncation=True, 
                    max_length=256
                )
                
                score = float(self.scorer.pseudo_loglikelihood(inputs['input_ids'].squeeze()))
                is_anomaly = score > self.threshold
                
                results.append(anomaly_detection_pb2.ScoreResponse(
                    score=score,
                    is_anomaly=is_anomaly,
                    threshold=self.threshold,
                    canonical_text=canonical_text
                ))
            
            logger.info(f"Scored batch of {len(results)} requests")
            
            return anomaly_detection_pb2.BatchScoreResponse(responses=results)
            
        except Exception as e:
            logger.error(f"Error scoring batch: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Batch scoring error: {str(e)}")
            return anomaly_detection_pb2.BatchScoreResponse()
    
    def UpdateThreshold(self, request, context):
        """
        Update the anomaly detection threshold.
        """
        try:
            old_threshold = self.threshold
            self.threshold = request.threshold
            
            logger.info(f"Threshold updated from {old_threshold} to {self.threshold}")
            
            return anomaly_detection_pb2.UpdateThresholdResponse(
                success=True,
                old_threshold=old_threshold,
                new_threshold=self.threshold
            )
            
        except Exception as e:
            logger.error(f"Error updating threshold: {e}")
            return anomaly_detection_pb2.UpdateThresholdResponse(
                success=False,
                old_threshold=self.threshold,
                new_threshold=self.threshold
            )
    
    def GetModelInfo(self, request, context):
        """
        Get information about the loaded model.
        """
        try:
            return anomaly_detection_pb2.ModelInfoResponse(
                model_name="transformer-anomaly-detector",
                model_parameters=self.model.num_parameters(),
                vocab_size=self.tokenizer.vocab_size,
                max_sequence_length=256,
                current_threshold=self.threshold
            )
            
        except Exception as e:
            logger.error(f"Error getting model info: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Model info error: {str(e)}")
            return anomaly_detection_pb2.ModelInfoResponse()
    
    def _canonicalize_web_request(self, request) -> str:
        """
        Convert a WebRequest proto to canonical format.
        """
        # Convert headers to dict
        headers = {}
        for header in request.headers:
            headers[header.key.lower()] = header.value
        
        # Convert query parameters to dict
        params = {}
        for param in request.query_params:
            params[param.key] = param.value
        
        # Use the canonicalize function
        return canonicalize_request(
            method=request.method,
            path=request.path,
            query_params=params,
            headers=headers
        )


def create_server(model_path: str, port: int, max_workers: int = 10, threshold: float = None):
    """
    Create and configure the gRPC server.
    """
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=max_workers))
    
    # Add servicer
    servicer = AnomalyDetectionServicer(model_path, threshold)
    anomaly_detection_pb2_grpc.add_AnomalyDetectionServicer_to_server(servicer, server)
    
    # Configure server
    listen_addr = f"[::]:{port}"
    server.add_insecure_port(listen_addr)
    
    return server, servicer


def main():
    parser = argparse.ArgumentParser(description="Anomaly Detection gRPC Server")
    
    parser.add_argument(
        "--model_path", 
        required=True,
        help="Path to the trained model directory"
    )
    
    parser.add_argument(
        "--port", 
        type=int, 
        default=50051,
        help="Port to listen on (default: 50051)"
    )
    
    parser.add_argument(
        "--max_workers", 
        type=int, 
        default=10,
        help="Maximum number of worker threads (default: 10)"
    )
    
    parser.add_argument(
        "--threshold", 
        type=float, 
        default=None,
        help="Anomaly detection threshold (default: adaptive)"
    )
    
    parser.add_argument(
        "--verbose", 
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Create and start server
    logger.info("Starting Anomaly Detection gRPC Server...")
    logger.info(f"Model path: {args.model_path}")
    logger.info(f"Port: {args.port}")
    logger.info(f"Max workers: {args.max_workers}")
    
    server, servicer = create_server(
        model_path=args.model_path,
        port=args.port,
        max_workers=args.max_workers,
        threshold=args.threshold
    )
    
    server.start()
    logger.info(f"Server started on port {args.port}")
    
    # Handle graceful shutdown
    def signal_handler(signum, frame):
        logger.info("Received shutdown signal, stopping server...")
        server.stop(grace=30)
        logger.info("Server stopped")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        logger.info("Server interrupted, shutting down...")
        server.stop(grace=30)


if __name__ == "__main__":
    main()