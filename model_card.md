# Model Card: Web Traffic Anomaly Detection RoBERTa

## Model Details

### Model Description
A RoBERTa-based Transformer model trained for anomaly detection in web traffic using Masked Language Modeling (MLM). The model learns patterns from benign web requests and identifies anomalies using Pseudo Log-Likelihood (PLL) scoring.

- **Developed by**: Web Security AI Team
- **Model type**: RoBERTa for Masked Language Modeling
- **Language(s)**: Web traffic request data (canonicalized)
- **License**: MIT
- **Model size**: ~22M parameters

### Model Architecture

```
RobertaForMaskedLM(
  (roberta): RobertaModel(
    hidden_size=384,
    num_attention_heads=6,
    num_hidden_layers=6,
    vocab_size=8000,
    max_position_embeddings=256
  )
  (lm_head): RobertaLMHead(
    (dense): Linear(384, 384)
    (layer_norm): LayerNorm(384)
    (decoder): Linear(384, 8000)
  )
)
```

## Intended Use

### Primary Use Cases
- **Web Application Firewall (WAF)**: Real-time detection of malicious web requests
- **Security Monitoring**: Identifying anomalous patterns in web traffic
- **Threat Detection**: Early warning system for web-based attacks

### Out-of-Scope Use Cases
- Network traffic analysis (non-HTTP protocols)
- File content analysis
- General text classification tasks
- Real-time streaming analytics requiring sub-millisecond latency

## Training Data

### Data Description
- **Training Set**: 50,000+ canonicalized benign web requests
- **Validation Set**: 5,000 benign requests (held-out)
- **Data Sources**: Production web traffic logs from multiple applications
- **Time Range**: 6 months of historical data
- **Geographic Coverage**: Global traffic patterns

### Data Preprocessing
1. **Canonicalization**: Standardized format `[METHOD] <method> [PATH] <path> [PARAMS] <params> [HEADERS] <headers>`
2. **Sensitive Data**: Hashed using SHA-256 (first 8 characters)
3. **Truncation**: Request bodies and headers limited to 2048 characters
4. **Tokenization**: ByteLevelBPE with 8000 vocabulary size

### Data Characteristics
- **Request Methods**: GET (60%), POST (25%), PUT (10%), DELETE (3%), Others (2%)
- **Path Diversity**: 10,000+ unique API endpoints
- **Parameter Types**: Query parameters, form data, JSON payloads
- **Header Variety**: 200+ unique header types

## Training Procedure

### Training Hyperparameters
- **Optimizer**: AdamW
- **Learning Rate**: 5e-4
- **Batch Size**: 32
- **Epochs**: 3
- **Warmup Steps**: 500
- **Weight Decay**: 0.01
- **Dropout**: 0.1
- **MLM Probability**: 15%

### Training Infrastructure
- **Hardware**: NVIDIA A100 40GB GPU
- **Training Time**: ~6 hours
- **Framework**: PyTorch 2.0 + HuggingFace Transformers
- **Mixed Precision**: FP16 enabled

### Training Loss
```
Epoch 1: Loss = 2.85
Epoch 2: Loss = 2.42
Epoch 3: Loss = 2.31
Final Loss: 2.31
```

## Evaluation

### Metrics
Performance on labeled test set (10,000 samples: 8,000 benign, 2,000 attacks):

| Metric | Value |
|--------|-------|
| ROC AUC | 0.9847 |
| Precision at 0.1% FPR | 0.8923 |
| Optimal Threshold | 42.7 |
| Production Threshold (99.9th %ile) | 58.3 |

### Test Data
- **Attack Types**: SQL injection, XSS, path traversal, command injection, LDAP injection
- **Benign Traffic**: Legitimate API calls, web browsing, mobile app traffic
- **Labeling**: Expert security analysts with 95%+ inter-annotator agreement

### Performance Analysis

#### ROC Curve Analysis
- Excellent separation between benign and malicious traffic
- Strong performance even at very low false positive rates
- Optimal operating point balances precision and recall

#### Latency Performance
| Percentile | Latency (ms) |
|------------|--------------|
| P50 | 8.2 |
| P95 | 23.7 |
| P99 | 41.5 |
| P99.9 | 67.8 |

#### Failure Analysis
- **False Positives**: Mostly legitimate but unusual API usage patterns
- **False Negatives**: Sophisticated attacks that closely mimic benign patterns
- **Edge Cases**: Very long URLs, unusual character encodings

## Limitations

### Technical Limitations
- **Sequence Length**: Limited to 256 tokens (may truncate very long requests)
- **Vocabulary**: 8000 tokens may not cover all possible parameter values
- **Context Window**: No cross-request context or session awareness
- **Real-time Constraints**: Inference latency may not suit all real-time applications

### Data Limitations
- **Training Data Bias**: Predominantly English-language applications
- **Temporal Drift**: Performance may degrade on significantly newer attack patterns
- **Domain Specificity**: Trained on web application traffic, may not generalize to APIs

### Operational Limitations
- **Threshold Sensitivity**: Performance depends on proper threshold calibration
- **Concept Drift**: Requires periodic retraining or fine-tuning
- **Interpretability**: Limited explainability for complex attack vectors

## Ethical Considerations

### Bias and Fairness
- **Geographic Bias**: Training data primarily from North American and European sources
- **Application Bias**: May perform differently across various web application types
- **Language Bias**: Optimized for English-language content and parameters

### Privacy Considerations
- **Data Anonymization**: All sensitive values are hashed during preprocessing
- **PII Protection**: No personally identifiable information stored in model
- **Audit Trail**: All training data sources tracked and documented

### Security Implications
- **Adversarial Robustness**: Model may be vulnerable to carefully crafted evasion attacks
- **Model Theft**: Standard protections needed to prevent model extraction
- **Deployment Security**: Requires secure model serving infrastructure

## Recommendations

### Production Deployment
1. **Threshold Setting**: Start with production threshold (58.3) and adjust based on business requirements
2. **Monitoring**: Implement continuous monitoring of false positive/negative rates
3. **Fallback**: Deploy with traditional rule-based systems as backup
4. **A/B Testing**: Gradual rollout with careful performance monitoring

### Model Maintenance
1. **Retraining Schedule**: Full retraining every 6 months
2. **Continuous Learning**: Weekly fine-tuning with new benign samples
3. **Performance Monitoring**: Daily evaluation on held-out test sets
4. **Threshold Adjustment**: Monthly review and calibration

### Integration Guidelines
1. **Latency Requirements**: Suitable for applications tolerating 10-50ms latency
2. **Throughput**: Can handle 1000+ requests/second with proper infrastructure
3. **Resource Requirements**: 2GB GPU memory minimum for inference
4. **Scaling**: Supports horizontal scaling with load balancing

## Model Card Authors
- AI Security Team
- Data Science Team
- Security Engineering Team

## Model Card Contact
For questions about this model card, contact: ai-security@company.com

## How to Cite
```bibtex
@misc{web_traffic_anomaly_roberta_2024,
  title={RoBERTa-based Web Traffic Anomaly Detection},
  author={AI Security Team},
  year={2024},
  howpublished={Internal Technical Report}
}
```

## Version History
- **v1.0.0** (2024-01): Initial release
- **v1.1.0** (2024-03): Performance improvements and bug fixes
- **v1.2.0** (2024-06): Enhanced continuous learning capabilities

---

*This model card was created following the framework proposed by Mitchell et al. (2019) and updated according to current best practices for ML model documentation.*