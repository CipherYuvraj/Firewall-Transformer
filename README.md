# Transformer-Based Web Traffic Anomaly Detection

## 🎯 What This Is

A **machine learning system** that learns what normal web traffic looks like and flags suspicious/malicious requests. It uses a **Transformer model** (like ChatGPT, but for security) trained on your web logs.

## 🚀 Quick Start (3 Steps)

### 1. Train Tokenizer (Teaches the AI your vocabulary)
```bash
python scripts/train_tokenizer.py data/ecom_benign.jsonl --output_dir tokenizer_json --max_samples 10000
```

### 2. Train Model (Teaches the AI normal patterns) 
```bash
python scripts/train_model.py data/ecom_benign.jsonl --tokenizer_dir tokenizer_json --output_dir model_json --max_samples 10000 --batch_size 16 --num_epochs 5
```

### 3. Test It (See if it catches attacks)
```bash
python scripts/scoring.py --model_path model_json --test_data data/ecom_benign.jsonl
```

## 📊 How It Works

### Input: Your JSON Logs
```json
{"m":"GET","p":"/store/category/:num","q":{"sort":"rating","page":":num"},"b":"","s":"api.shop.example.com","h":{"ua":"Mozilla/5.0","ct":"text/plain","cl":":num","cookieKeys":["trk","sid","pref"]}}
```
- `m` = HTTP Method (GET, POST, etc.)
- `p` = Path (/store/category, /api/cart, etc.) 
- `q` = Query parameters (object: {"sort":"rating","page":":num"})
- `b` = Request body (for POST requests)
- `s` = Server/Host (api.shop.example.com, 10.0.0.10, etc.)
- `h` = Headers object with:
  - `ua` = User-Agent
  - `ct` = Content-Type
  - `cl` = Content-Length
  - `cookieKeys` = Array of cookie names

### Output: Anomaly Scores
- **Low Score (0-100)**: Normal traffic ✅
- **Medium Score (100-200)**: Suspicious traffic ⚠️  
- **High Score (200+)**: Likely attack 🚨

### Example Results
```
Normal GET /store/home        → Score: 68   ✅ Safe
Normal POST /store/api/cart   → Score: 94   ✅ Safe  
Admin access                  → Score: 143  ⚠️ Monitor
XSS Attack                    → Score: 266  🚨 Block!
Path Traversal Attack         → Score: 227  🚨 Block!
```

## 🧠 How The AI Learns

1. **Canonicalization**: Converts messy logs into clean format
   ```
   Raw: {"m":"GET","p":"/store/category/:num","q":{"sort":"rating"},"s":"api.shop.example.com"}
   Clean: [METHOD] GET [PATH] /store/category/:num [PARAMS] sort=rating [HEADERS] server:api.shop.example.com
   ```

2. **Tokenization**: Breaks text into AI-understandable pieces
   ```
   "[METHOD] GET" → [67, 313, 69, 320] (numbers the AI understands)
   ```

3. **Training**: AI learns to predict missing words in normal requests
   - Shows AI: "[METHOD] GET [PATH] /store/[MASK]" 
   - AI learns: "[MASK] = category" (because that's normal in e-commerce)
   - Later: AI sees "/store/../../etc/passwd" and thinks "This is weird!"

4. **Scoring**: AI calculates how "surprised" it is by new requests
   - Familiar patterns = Low score = Safe
   - Strange patterns = High score = Attack

## 🎛️ Training Parameters (For Better Accuracy)

### Basic Training (Fast)
```bash
python scripts/train_model.py data/ecom_benign.jsonl \
  --tokenizer_dir tokenizer_json \
  --output_dir model_json \
  --max_samples 5000 \
  --batch_size 8 \
  --num_epochs 2
```

### High Accuracy Training (Slower but Better)
```bash
python scripts/train_model.py data/ecom_benign.jsonl \
  --tokenizer_dir tokenizer_json \
  --output_dir model_json \
  --max_samples 10000 \
  --batch_size 32 \
  --num_epochs 10 \
  --learning_rate 3e-4
```

### Production Training (Maximum Accuracy)
```bash
python scripts/train_model.py data/ecom_benign.jsonl \
  --tokenizer_dir tokenizer_json \
  --output_dir model_json \
  --batch_size 64 \
  --num_epochs 20 \
  --learning_rate 1e-4
```

## 📁 What Each File Does

```
📦 Firewall Trans/
├── 📂 data/
│   └── ecom_benign.jsonl         # Your e-commerce web traffic logs (10,000 samples)
├── 📂 scripts/
│   ├── canonicalize.py           # Cleans up messy log formats  
│   ├── train_tokenizer.py        # Teaches AI your vocabulary
│   ├── train_model.py            # Main AI training script
│   ├── scoring.py                # Tests trained AI on new data
│   ├── evaluate.py               # Measures AI accuracy
│   └── finetune.py               # Updates AI with new data
├── 📂 model_json/                # Your trained AI brain
├── 📂 tokenizer_json/            # AI's vocabulary
└── requirements.txt              # Software dependencies
```

## � Advanced Features

### Continuous Learning (Update Model with New Data)
```bash
python scripts/finetune.py --base_model model_json --new_data new_logs.jsonl --output_dir model_updated
```

### Evaluation (Check How Good Your Model Is)
```bash
python scripts/evaluate.py --model_path model_json --test_data test_logs.jsonl
```

## 💡 Tips for Best Results

### 1. **More Data = Better Detection**
- Use 10k+ samples for good results
- Use 50k+ samples for excellent results
- Use all your data for maximum accuracy

### 2. **Balance Your Data**
- Include normal traffic (90%)
- Include some attacks (10%) if you have labeled data
- More variety = better generalization

### 3. **Training Time vs Accuracy**
- 2 epochs = Quick test (5 minutes)
- 10 epochs = Good accuracy (30 minutes)  
- 20+ epochs = Maximum accuracy (hours)

### 4. **Memory Management**
- Small batch_size (8) = Less memory, slower
- Large batch_size (32) = More memory, faster
- Adjust based on your computer's RAM

## 🎯 Understanding Your Results

### Good Model Signs:
- ✅ Training loss decreases over time
- ✅ Normal traffic gets scores < 150
- ✅ Attacks get scores > 200
- ✅ Clear separation between normal/attack scores

### Bad Model Signs:
- ❌ Training loss doesn't decrease
- ❌ All scores are similar (no separation)
- ❌ Normal traffic gets very high scores
- ❌ Model says everything is an attack

## 🚨 Common Issues & Fixes

### "Out of Memory" Error
```bash
# Use smaller batch size
--batch_size 4
```

### "All Scores Are High"
```bash
# Train longer or use more data
--num_epochs 10 --max_samples 20000
```

### "Model Not Learning"
```bash
# Adjust learning rate
--learning_rate 1e-4
```

## 🎉 You're Ready!

Your AI security system can now:
- ✅ Learn from your web traffic patterns
- ✅ Detect XSS, SQL injection, path traversal attacks
- ✅ Score requests in real-time
- ✅ Improve over time with new data

**Start with basic training, then scale up for production!** 🚀
│   ├── pytorch_model.bin
│   ├── config.json
│   └── tokenizer.json
├── inference/              # gRPC inference server
│   ├── server.py
│   ├── inference.proto
│   ├── Dockerfile
│   └── requirements.txt
├── scripts/                # Training and evaluation scripts
│   ├── canonicalize.py     # Data canonicalization utilities
│   ├── train_tokenizer.py  # BPE tokenizer training
│   ├── train_model.py      # RoBERTa model training
│   ├── scoring.py          # PLL scoring implementation
│   ├── evaluate.py         # Model evaluation and metrics
│   └── finetune.py         # Safe continuous learning
├── data/                   # Data directory (placeholder)
├── requirements.txt        # Python dependencies
├── README.md              # This file
└── model_card.md          # Model documentation
```

## 🛠️ Installation

### Prerequisites

- Python 3.8+
- CUDA-compatible GPU (optional, for faster training/inference)
- Docker (for containerized deployment)

### Setup

1. **Clone the repository:**
```bash
git clone <repository_url>
cd web-traffic-anomaly-detection
```

2. **Create and activate virtual environment:**
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

3. **Install dependencies:**
```bash
pip install -r requirements.txt
```

## 📊 Data Preparation

### 1. JSON Log Processing

If you have JSON logs, use the dedicated processor to convert them to canonical format:

```bash
# Analyze your JSON structure first
python scripts/process_json_logs.py analyze your_logs.json

# Convert JSON logs to canonical format
python scripts/process_json_logs.py process your_logs.json data/logs_canonical.txt

# Create sample data for testing
python scripts/process_json_logs.py sample --output data/sample_canonical.txt
```

**Supported JSON formats:**
- **JSONL**: One JSON object per line (recommended)
- **JSON Array**: Array of JSON objects

**Required JSON fields:**
- `method` (or `http_method`, `verb`): HTTP method
- `path` (or `url`, `uri`): Request path  
- `query_params` (or `params`, `query`): Query parameters (optional)
- `headers` (or `request_headers`): HTTP headers (optional)
- `body` (or `request_body`, `payload`): Request body (optional)

### 2. Data Format

Your training data should be canonicalized web request logs. Each log entry should be a JSON object or dictionary with fields like:

```json
{
  "method": "GET",
  "path": "/api/users",
  "query_params": {"page": "1", "limit": "10"},
  "headers": {
    "User-Agent": "Mozilla/5.0",
    "Content-Type": "application/json"
  }
}
```

### 3. Canonicalization

The system automatically converts logs to standardized format:
```
[METHOD] GET [PATH] /api/users [PARAMS] page=1&limit=10 [HEADERS] content-type:application/json|user-agent:mozilla/5.0
```

### 4. Data Requirements

- **Training Data**: 10K+ canonicalized benign requests
- **Validation Data**: 1K+ benign requests (separate from training)
- **Test Data**: Labeled CSV with `text` and `label` columns (0=benign, 1=attack)

## 🎯 Training Pipeline

### Step 1: Process JSON Logs (if needed)

If you have JSON logs, convert them first:

```bash
# Process your JSON training data
python scripts/process_json_logs.py process train_logs.json data/logs_canonical.txt

# Process validation data
python scripts/process_json_logs.py process val_logs.json data/logs_validation.txt
```

### Step 2: Train Tokenizer

Train a ByteLevelBPE tokenizer on your canonicalized data:

```bash
python scripts/train_tokenizer.py data/logs_canonical.txt --output_dir tokenizer
```

**Parameters:**
- `vocab_size`: 8000
- `min_frequency`: 2
- Special tokens: `[METHOD]`, `[PATH]`, `[PARAMS]`, `[HEADERS]`

### Step 3: Train Model

Train the RoBERTa model using masked language modeling:

```bash
python scripts/train_model.py data/logs_canonical.txt \
    --tokenizer_dir tokenizer \
    --output_dir model \
    --val_file data/logs_validation.txt \
    --batch_size 32 \
    --num_epochs 3 \
    --learning_rate 5e-4
```

**Model Architecture:**
- Hidden size: 384
- Attention heads: 6
- Hidden layers: 6
- Max sequence length: 256
- Parameters: ~22M

### Step 4: Evaluate Model

Evaluate performance on labeled test data:

```bash
python scripts/evaluate.py data/test_labeled.csv \
    --model_dir model \
    --benign_file data/benign_validation.csv \
    --output_dir evaluation_results
```

**Outputs:**
- ROC curve plot (`roc_curve.png`)
- Performance metrics
- Recommended production threshold

## 🚀 Deployment

### Local Inference Server

Start the gRPC server locally:

```bash
cd inference

# Generate protobuf code
python -m grpc_tools.protoc \
    --python_out=. \
    --grpc_python_out=. \
    --proto_path=. \
    inference.proto

# Start server
python server.py --model_dir ../model --port 50051 --threshold 50.0
```

### Docker Deployment

Build and run the containerized server:

```bash
# Build Docker image
docker build -t waf-inference ./inference

# Run container
docker run -p 50051:50051 waf-inference
```

### Client Usage

Example gRPC client:

```python
import grpc
import inference_pb2
import inference_pb2_grpc

# Connect to server
channel = grpc.insecure_channel('localhost:50051')
stub = inference_pb2_grpc.WAFInferenceStub(channel)

# Score a request
request = inference_pb2.Request(
    canonical_request="[METHOD] GET [PATH] /api/test [PARAMS] [HEADERS]"
)

response = stub.Score(request)
print(f"Anomaly Score: {response.score}")
print(f"Block Decision: {response.block}")
```

## 🔄 Continuous Learning

Update the model with new benign data while preserving previous knowledge:

```bash
python scripts/finetune.py model new_benign_samples.txt replay_buffer.txt \
    --output_path model_updated \
    --learning_rate 1e-6 \
    --num_steps 100 \
    --replay_ratio 0.9
```

**Safety Features:**
- Sample validation (filters suspicious new data)
- Replay buffer (prevents catastrophic forgetting)
- Model backup (automatic backup before fine-tuning)
- Low learning rate (stable incremental updates)

## 📈 Performance Metrics

### Evaluation Metrics

The system provides comprehensive evaluation metrics:

- **ROC AUC**: Overall detection performance
- **Precision at 0.1% FPR**: Performance at low false positive rates
- **Optimal Threshold**: Best threshold based on Youden's J statistic
- **Production Threshold**: 99.9th percentile of benign scores

### Latency Performance

Expected inference latencies:
- **P50**: ~5-10ms per request
- **P95**: ~15-25ms per request
- **P99**: ~30-50ms per request

*Note: Latencies measured on modern hardware with GPU acceleration*

## 🔧 Configuration

### Model Hyperparameters

Key configuration options in `train_model.py`:

```python
config = RobertaConfig(
    vocab_size=8000,
    max_position_embeddings=256,
    hidden_size=384,
    num_attention_heads=6,
    num_hidden_layers=6,
    # ... other parameters
)
```

### Inference Settings

Server configuration in `server.py`:

```python
# Anomaly threshold for blocking
threshold = 50.0

# Model optimization
compile_model = True  # Use torch.compile()

# Server settings
max_workers = 10
port = 50051
```

## 🧪 Testing

### Unit Tests

Test individual components:

```bash
# Test canonicalization
python scripts/canonicalize.py

# Test scoring
python scripts/scoring.py

# Health check
python inference/server.py --help
```

### Integration Testing

Test the complete pipeline:

1. Generate sample data
2. Train tokenizer
3. Train model
4. Evaluate performance
5. Start inference server
6. Send test requests

## 🔍 Troubleshooting

### Common Issues

1. **CUDA Out of Memory**
   - Reduce batch size (`--batch_size 16`)
   - Use CPU inference (`--device cpu`)

2. **Low Performance**
   - Check data quality and canonicalization
   - Ensure sufficient training data (10K+ samples)
   - Verify label quality in test data

3. **High False Positives**
   - Increase anomaly threshold
   - Retrain with more diverse benign data
   - Use continuous learning to adapt

4. **Server Connection Issues**
   - Check port availability
   - Verify firewall settings
   - Ensure model files are properly loaded

### Debugging

Enable debug logging:

```bash
export PYTHONPATH=$PWD
python -c "import logging; logging.basicConfig(level=logging.DEBUG)"
```

## 📚 References

- [RoBERTa: A Robustly Optimized BERT Pretraining Approach](https://arxiv.org/abs/1907.11692)
- [Masked Language Modeling for Anomaly Detection](https://arxiv.org/abs/2010.02946)
- [Pseudo Log-Likelihood for Sequence Scoring](https://arxiv.org/abs/1910.03493)

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes and add tests
4. Submit a pull request

## 📞 Support

For questions and issues:
- Create a GitHub issue
- Check the troubleshooting section
- Review the model card for detailed specifications