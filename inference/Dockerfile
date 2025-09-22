FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY inference/ ./inference/
COPY scripts/ ./scripts/
COPY model/ ./model/
COPY tokenizer/ ./tokenizer/

# Generate gRPC code from protobuf
WORKDIR /app/inference
RUN python -m grpc_tools.protoc \
    --python_out=. \
    --grpc_python_out=. \
    --proto_path=. \
    inference.proto

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash appuser
RUN chown -R appuser:appuser /app
USER appuser

# Expose the gRPC port
EXPOSE 50051

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import grpc; import inference_pb2_grpc; import inference_pb2; \
    channel = grpc.insecure_channel('localhost:50051'); \
    stub = inference_pb2_grpc.WAFInferenceStub(channel); \
    response = stub.HealthCheck(inference_pb2.HealthCheckRequest()); \
    exit(0 if response.status == 1 else 1)"

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Command to run the server
CMD ["python", "server.py", "--model_dir", "../model", "--port", "50051"]