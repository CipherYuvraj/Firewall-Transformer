# Data Directory

This directory contains the training and evaluation data for the web traffic anomaly detection system.

## Expected Files

### Training Data
- `logs_canonical.txt`: Canonicalized benign web requests (one per line)
- `logs_validation.txt`: Validation set of benign requests

### Evaluation Data
- `test_labeled.csv`: Labeled test data with columns:
  - `text`: Canonicalized request text
  - `label`: 0 for benign, 1 for attack
- `benign_validation.csv`: Additional benign samples for threshold calibration

## Working with JSON Log Data

### JSON Input Formats Supported

The system supports two JSON formats:

#### 1. JSONL Format (Recommended)
One JSON object per line:
```json
{"method": "GET", "path": "/api/users", "headers": {"User-Agent": "curl"}}
{"method": "POST", "path": "/login", "body": "{\"user\":\"admin\"}"}
```

#### 2. JSON Array Format
Array of JSON objects:
```json
[
  {"method": "GET", "path": "/api/users", "headers": {"User-Agent": "curl"}},
  {"method": "POST", "path": "/login", "body": "{\"user\":\"admin\"}"}
]
```

### JSON Field Mapping

Your JSON logs should contain these fields (flexible field names supported):

| Field | Aliases | Description | Example |
|-------|---------|-------------|---------|
| `method` | `http_method`, `verb` | HTTP method | `"GET"` |
| `path` | `url`, `uri`, `endpoint` | Request path | `"/api/users"` |
| `query_params` | `params`, `query` | Query parameters | `{"page": "1"}` |
| `headers` | `request_headers` | HTTP headers | `{"User-Agent": "curl"}` |
| `body` | `request_body`, `payload` | Request body | `"{\"user\":\"admin\"}"` |

### Processing JSON Logs

#### Step 1: Analyze Your JSON Structure
```bash
python scripts/process_json_logs.py analyze your_logs.json --max_samples 1000
```

This will show you:
- Available fields in your JSON
- Data types and examples
- Structure analysis

#### Step 2: Convert JSON to Canonical Format
```bash
python scripts/process_json_logs.py process your_logs.json data/logs_canonical.txt
```

Options:
- `--max_samples N`: Process only first N samples
- `--no_skip_errors`: Stop on first error instead of skipping

#### Step 3: Create Sample Data (for testing)
```bash
python scripts/process_json_logs.py sample --output data/sample_canonical.txt
```

### Sample Data Format

#### Original JSON Input
```json
{
  "method": "GET",
  "path": "/api/users",
  "query_params": {"page": "1", "limit": "10"},
  "headers": {
    "User-Agent": "Mozilla/5.0",
    "Authorization": "Bearer token123",
    "Content-Type": "application/json"
  }
}
```

#### Canonicalized Output
```
[METHOD] GET [PATH] /api/users [PARAMS] limit=10&page=1 [HEADERS] authorization:HDR_a1b2c3d4|content-type:application/json|user-agent:mozilla/5.0
```

### Complete Training Pipeline with JSON

#### 1. Process Your JSON Logs
```bash
# Convert training data
python scripts/process_json_logs.py process train_logs.json data/logs_canonical.txt

# Convert validation data  
python scripts/process_json_logs.py process val_logs.json data/logs_validation.txt
```

#### 2. Train Tokenizer
```bash
python scripts/train_tokenizer.py data/logs_canonical.txt --output_dir tokenizer
```

#### 3. Train Model
```bash
python scripts/train_model.py data/logs_canonical.txt \
    --tokenizer_dir tokenizer \
    --output_dir model \
    --val_file data/logs_validation.txt
```

#### 4. Evaluate Model
```bash
python scripts/evaluate.py data/test_labeled.csv \
    --model_dir model \
    --output_dir evaluation_results
```

### Data Quality Guidelines

#### For Training Data (JSON logs):
- **Minimum**: 10,000 benign requests
- **Recommended**: 50,000+ benign requests
- **Diversity**: Include various endpoints, methods, parameters
- **Clean Data**: Remove obvious attacks or anomalies

#### For Test Data (CSV):
- **Format**: CSV with `text` (canonicalized) and `label` (0/1) columns
- **Balance**: Mix of benign (0) and attack (1) samples
- **Attack Types**: Include SQL injection, XSS, path traversal, etc.
- **Size**: 1,000+ labeled samples

### Example JSON Log Formats

#### Web Server Access Logs
```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "method": "GET",
  "path": "/api/products",
  "query_string": "category=electronics&page=2",
  "headers": {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Accept": "application/json",
    "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
  },
  "status_code": 200,
  "response_size": 1524
}
```

#### API Gateway Logs
```json
{
  "requestId": "123e4567-e89b-12d3-a456-426614174000", 
  "httpMethod": "POST",
  "resourcePath": "/users",
  "queryStringParameters": null,
  "headers": {
    "Content-Type": "application/json",
    "X-API-Key": "ak_live_1234567890"
  },
  "body": "{\"name\":\"John Doe\",\"email\":\"john@example.com\"}"
}
```

#### Application Logs
```json
{
  "level": "INFO",
  "message": "HTTP Request",
  "http": {
    "method": "PUT", 
    "url": "/api/users/123",
    "headers": {
      "Content-Type": "application/json",
      "User-Agent": "MyApp/1.0"
    },
    "body": "{\"name\":\"Updated Name\"}"
  }
}
```

## Data Requirements

- **Minimum Training Data**: 10,000 benign requests
- **Recommended Training Data**: 50,000+ benign requests
- **Test Data**: 1,000+ labeled samples (mix of benign and attacks)
- **Attack Types**: Include diverse attack patterns (SQLi, XSS, etc.)
- **JSON Format**: Either JSONL or JSON array format
- **Field Coverage**: Include method, path, parameters, headers when available