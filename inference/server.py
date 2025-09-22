"""
gRPC inference server for web traffic anomaly detection.

This server loads a trained RoBERTa model and provides real-time anomaly scoring
for web requests via gRPC interface with optimized inference performance.
"""
import os
import sys
import time
import logging
import argparse
import threading
from concurrent import futures
from pathlib import Path
from typing import Optional, List

import grpc
import torch
from transformers import RobertaForMaskedLM, RobertaTokenizer

# Add scripts directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'scripts'))
from scoring import PseudoLogLikelihoodScorer
from canonicalize import canonicalize_request

# Import generated protobuf classes
import inference_pb2
import inference_pb2_grpc


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class WAFInferenceServicer(inference_pb2_grpc.WAFInferenceServicer):
    """
    gRPC servicer for WAF inference requests.
    
    Handles anomaly scoring requests with optimized inference using
    torch.inference_mode() and torch.compile() for performance.
    """
    
    def __init__(
        self,
        model_dir: str,
        threshold: float = 50.0,
        device: str = "auto",
        compile_model: bool = True
    ):
        """
        Initialize the inference servicer.
        
        Args:
            model_dir: Directory containing the trained model
            threshold: Anomaly threshold for blocking decisions
            device: Device to run inference on
            compile_model: Whether to compile model for optimization
        """
        self.model_dir = model_dir
        self.threshold = threshold
        self.start_time = time.time()
        self.request_count = 0
        self.total_latency = 0.0
        self._lock = threading.Lock()
        
        logger.info(f"Loading model from: {model_dir}")
        logger.info(f"Anomaly threshold: {threshold}")
        
        # Load model and tokenizer
        self.model = RobertaForMaskedLM.from_pretrained(model_dir)
        self.tokenizer = RobertaTokenizer.from_pretrained(model_dir)
        
        # Set device
        if device == "auto":
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        else:
            self.device = torch.device(device)
        
        self.model.to(self.device)
        self.model.eval()
        
        # Optimize model with torch.compile if available and requested
        if compile_model and hasattr(torch, 'compile'):
            try:
                logger.info("Compiling model for optimized inference...")
                self.model = torch.compile(self.model, mode="reduce-overhead")
                logger.info("Model compilation successful")
            except Exception as e:
                logger.warning(f"Model compilation failed: {e}, continuing without compilation")
        
        # Initialize scorer
        self.scorer = PseudoLogLikelihoodScorer(self.model, self.tokenizer, str(self.device))
        
        # Warm up the model with a dummy request
        self._warmup()
        
        logger.info(f"WAF Inference Server initialized on device: {self.device}")
        logger.info(f"Model parameters: {self.model.num_parameters():,}")
    
    def _warmup(self):
        """Warm up the model with a dummy request."""
        try:
            dummy_request = "[METHOD] GET [PATH] /api/test [PARAMS] [HEADERS] "
            inputs = self.tokenizer(dummy_request, return_tensors="pt", truncation=True, max_length=256)
            input_ids = inputs['input_ids'].squeeze()
            
            with torch.inference_mode():
                _ = self.scorer.pseudo_loglikelihood(input_ids)
            
            logger.info("Model warmup completed")
        except Exception as e:
            logger.warning(f"Model warmup failed: {e}")
    
    def Score(self, request: inference_pb2.Request, context) -> inference_pb2.Response:
        """
        Score a single request for anomaly detection.
        
        Args:
            request: gRPC request containing canonical_request string
            context: gRPC context
        
        Returns:
            Response with score, block decision, and explanations
        """
        start_time = time.time()
        
        try:
            # Validate input
            if not request.canonical_request:
                return inference_pb2.Response(
                    score=0.0,
                    block=False,
                    status_code=400,
                    message="Empty request"
                )
            
            # Tokenize the request
            inputs = self.tokenizer(
                request.canonical_request,
                return_tensors="pt",
                truncation=True,
                max_length=256,
                padding=False
            )
            
            input_ids = inputs['input_ids'].squeeze()
            
            # Calculate anomaly score with explanations
            score, explanations = self.scorer.score_with_explanation(input_ids, top_k=5)
            
            # Make blocking decision
            block = score > self.threshold
            
            # Create explanation objects
            explain_objects = []
            for exp in explanations:
                explain_objects.append(inference_pb2.TokenExplain(
                    token=exp['token'],
                    logprob=exp['logprob'],
                    position=exp['position'],
                    anomaly_contribution=exp['anomaly_contribution']
                ))
            
            # Update statistics
            latency = (time.time() - start_time) * 1000  # Convert to ms
            with self._lock:
                self.request_count += 1
                self.total_latency += latency
            
            return inference_pb2.Response(
                score=score,
                block=block,
                explain=explain_objects,
                status_code=200,
                message="Success"
            )
            
        except Exception as e:
            logger.error(f"Error processing request: {e}")
            return inference_pb2.Response(
                score=0.0,
                block=False,
                status_code=500,
                message=f"Internal error: {str(e)}"
            )
    
    def BatchScore(self, request: inference_pb2.BatchRequest, context) -> inference_pb2.BatchResponse:
        """
        Score multiple requests in batch.
        
        Args:
            request: Batch request containing multiple canonical requests
            context: gRPC context
        
        Returns:
            Batch response with individual scores
        """
        start_time = time.time()
        responses = []
        
        for canonical_request in request.canonical_requests:
            # Create individual request and process
            individual_request = inference_pb2.Request(canonical_request=canonical_request)
            response = self.Score(individual_request, context)
            responses.append(response)
        
        total_latency = (time.time() - start_time) * 1000
        avg_latency = total_latency / len(request.canonical_requests) if request.canonical_requests else 0
        
        return inference_pb2.BatchResponse(
            responses=responses,
            total_processed=len(responses),
            avg_latency_ms=avg_latency
        )
    
    def HealthCheck(self, request: inference_pb2.HealthCheckRequest, context) -> inference_pb2.HealthCheckResponse:
        """
        Health check endpoint.
        
        Args:
            request: Health check request
            context: gRPC context
        
        Returns:
            Health check response with server status
        """
        uptime = int(time.time() - self.start_time)
        
        with self._lock:
            avg_latency = self.total_latency / self.request_count if self.request_count > 0 else 0
        
        return inference_pb2.HealthCheckResponse(
            status=inference_pb2.HealthCheckResponse.SERVING,
            message=f"Server healthy. Processed {self.request_count} requests. Avg latency: {avg_latency:.2f}ms",
            model_version="1.0.0",
            uptime_seconds=uptime
        )


def serve(
    model_dir: str,
    port: int = 50051,
    threshold: float = 50.0,
    max_workers: int = 10,
    device: str = "auto",
    compile_model: bool = True
):
    """
    Start the gRPC inference server.
    
    Args:
        model_dir: Directory containing the trained model
        port: Port to listen on
        threshold: Anomaly threshold
        max_workers: Maximum number of worker threads
        device: Device for inference
        compile_model: Whether to compile model for optimization
    """
    # Create gRPC server
    server = grpc.server(
        futures.ThreadPoolExecutor(max_workers=max_workers),
        options=[
            ('grpc.keepalive_time_ms', 30000),
            ('grpc.keepalive_timeout_ms', 5000),
            ('grpc.keepalive_permit_without_calls', True),
            ('grpc.http2.max_pings_without_data', 0),
            ('grpc.http2.min_time_between_pings_ms', 10000),
            ('grpc.http2.min_ping_interval_without_data_ms', 300000)
        ]
    )
    
    # Add servicer
    servicer = WAFInferenceServicer(
        model_dir=model_dir,
        threshold=threshold,
        device=device,
        compile_model=compile_model
    )
    
    inference_pb2_grpc.add_WAFInferenceServicer_to_server(servicer, server)
    
    # Listen on port
    listen_addr = f'[::]:{port}'
    server.add_insecure_port(listen_addr)
    
    # Start server
    server.start()
    logger.info(f"WAF Inference Server started on port {port}")
    logger.info(f"Model directory: {model_dir}")
    logger.info(f"Anomaly threshold: {threshold}")
    logger.info(f"Device: {servicer.device}")
    logger.info(f"Max workers: {max_workers}")
    
    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        logger.info("Shutting down server...")
        server.stop(5)


def main():
    """Main function to handle command line arguments and start server."""
    parser = argparse.ArgumentParser(
        description="WAF Inference gRPC Server",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    parser.add_argument(
        "--model_dir",
        default="../model",
        help="Directory containing the trained model"
    )
    
    parser.add_argument(
        "--port",
        type=int,
        default=50051,
        help="Port to listen on"
    )
    
    parser.add_argument(
        "--threshold",
        type=float,
        default=50.0,
        help="Anomaly threshold for blocking decisions"
    )
    
    parser.add_argument(
        "--max_workers",
        type=int,
        default=10,
        help="Maximum number of worker threads"
    )
    
    parser.add_argument(
        "--device",
        default="auto",
        choices=["auto", "cpu", "cuda"],
        help="Device for inference"
    )
    
    parser.add_argument(
        "--no_compile",
        action="store_true",
        help="Disable model compilation optimization"
    )
    
    args = parser.parse_args()
    
    # Validate model directory
    if not os.path.exists(args.model_dir):
        logger.error(f"Model directory not found: {args.model_dir}")
        return 1
    
    required_files = ["pytorch_model.bin", "config.json", "tokenizer.json"]
    for file in required_files:
        if not os.path.exists(os.path.join(args.model_dir, file)):
            logger.warning(f"Required file might be missing: {file}")
    
    try:
        serve(
            model_dir=args.model_dir,
            port=args.port,
            threshold=args.threshold,
            max_workers=args.max_workers,
            device=args.device,
            compile_model=not args.no_compile
        )
    except Exception as e:
        logger.error(f"Server failed to start: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())