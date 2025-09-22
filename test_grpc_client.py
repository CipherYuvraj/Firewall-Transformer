#!/usr/bin/env python3
"""
gRPC client for testing the anomaly detection service.
"""

import grpc
import sys
import os

# Add scripts directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'scripts'))

import anomaly_detection_pb2
import anomaly_detection_pb2_grpc


def test_grpc_server(server_address="localhost:50051"):
    """
    Test the gRPC anomaly detection server.
    """
    print(f"Connecting to gRPC server at {server_address}...")
    
    # Create gRPC channel
    with grpc.insecure_channel(server_address) as channel:
        stub = anomaly_detection_pb2_grpc.AnomalyDetectionStub(channel)
        
        print("✓ Connected to server")
        
        # Test 1: Get model info
        print("\n=== Test 1: Model Info ===")
        try:
            response = stub.GetModelInfo(anomaly_detection_pb2.Empty())
            print(f"Model Name: {response.model_name}")
            print(f"Model Parameters: {response.model_parameters:,}")
            print(f"Vocab Size: {response.vocab_size}")
            print(f"Max Sequence Length: {response.max_sequence_length}")
            print(f"Current Threshold: {response.current_threshold}")
        except grpc.RpcError as e:
            print(f"Error: {e}")
        
        # Test 2: Score individual requests
        print("\n=== Test 2: Individual Request Scoring ===")
        test_requests = [
            {
                "method": "GET",
                "path": "/api/users",
                "query_params": [{"key": "limit", "value": "10"}],
                "headers": [{"key": "user-agent", "value": "browser"}],
                "description": "Normal API request"
            },
            {
                "method": "POST",
                "path": "/api/login",
                "query_params": [],
                "headers": [{"key": "content-type", "value": "application/json"}],
                "description": "Normal login request"
            },
            {
                "method": "GET",
                "path": "/admin/config",
                "query_params": [{"key": "debug", "value": "true"}],
                "headers": [{"key": "authorization", "value": "token"}],
                "description": "Admin access"
            },
            {
                "method": "DELETE",
                "path": "/api/users/../../etc/passwd",
                "query_params": [],
                "headers": [{"key": "x-forwarded-for", "value": "attacker"}],
                "description": "Path traversal attack"
            }
        ]
        
        for i, req_data in enumerate(test_requests, 1):
            print(f"\nRequest {i}: {req_data['description']}")
            
            # Create request
            request = anomaly_detection_pb2.WebRequest(
                method=req_data["method"],
                path=req_data["path"],
                query_params=[
                    anomaly_detection_pb2.KeyValue(key=kv["key"], value=kv["value"])
                    for kv in req_data["query_params"]
                ],
                headers=[
                    anomaly_detection_pb2.KeyValue(key=kv["key"], value=kv["value"])
                    for kv in req_data["headers"]
                ]
            )
            
            try:
                response = stub.ScoreRequest(request)
                print(f"  Score: {response.score:.6f}")
                print(f"  Is Anomaly: {response.is_anomaly}")
                print(f"  Threshold: {response.threshold}")
                print(f"  Canonical: {response.canonical_text}")
            except grpc.RpcError as e:
                print(f"  Error: {e}")
        
        # Test 3: Batch scoring
        print("\n=== Test 3: Batch Scoring ===")
        try:
            batch_requests = [
                anomaly_detection_pb2.WebRequest(
                    method=req_data["method"],
                    path=req_data["path"],
                    query_params=[
                        anomaly_detection_pb2.KeyValue(key=kv["key"], value=kv["value"])
                        for kv in req_data["query_params"]
                    ],
                    headers=[
                        anomaly_detection_pb2.KeyValue(key=kv["key"], value=kv["value"])
                        for kv in req_data["headers"]
                    ]
                ) for req_data in test_requests
            ]
            
            batch_request = anomaly_detection_pb2.BatchRequest(requests=batch_requests)
            response = stub.ScoreBatch(batch_request)
            
            print(f"Batch scored {len(response.responses)} requests:")
            for i, resp in enumerate(response.responses, 1):
                print(f"  Request {i}: Score={resp.score:.6f}, Anomaly={resp.is_anomaly}")
                
        except grpc.RpcError as e:
            print(f"Error: {e}")
        
        # Test 4: Update threshold
        print("\n=== Test 4: Threshold Update ===")
        try:
            update_request = anomaly_detection_pb2.UpdateThresholdRequest(threshold=200.0)
            response = stub.UpdateThreshold(update_request)
            print(f"Threshold update success: {response.success}")
            print(f"Old threshold: {response.old_threshold}")
            print(f"New threshold: {response.new_threshold}")
        except grpc.RpcError as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    test_grpc_server()