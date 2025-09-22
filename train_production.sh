#!/bin/bash
# Production Training Script for Maximum Accuracy

echo "🚀 Starting Production Training for Extreme Accuracy..."

# Step 1: Train tokenizer on all 10,000 samples
echo "📚 Training tokenizer on full dataset..."
python scripts/train_tokenizer.py data/ecom_benign.jsonl \
  --output_dir tokenizer_production \
  --max_samples 10000 \
  --vocab_size 10000

# Step 2: Train model with maximum settings
echo "🧠 Training model with production settings..."
python scripts/train_model.py data/ecom_benign.jsonl \
  --tokenizer_dir tokenizer_production \
  --output_dir model_production \
  --max_samples 10000 \
  --batch_size 32 \
  --num_epochs 15 \
  --learning_rate 1e-4 \
  --hidden_size 512 \
  --num_hidden_layers 8 \
  --num_attention_heads 8

echo "✅ Production training completed!"
echo "Model saved in: model_production/"