# Production Training Script for Maximum Accuracy (Windows PowerShell)

Write-Host "🚀 Starting Production Training for Extreme Accuracy..." -ForegroundColor Green

# Step 1: Train tokenizer on all 10,000 samples
Write-Host "📚 Training tokenizer on full dataset..." -ForegroundColor Cyan
python scripts/train_tokenizer.py data/ecom_benign.jsonl --output_dir tokenizer_production --max_samples 10000 --vocab_size 10000

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Tokenizer training completed successfully!" -ForegroundColor Green
    
    # Step 2: Train model with maximum settings  
    Write-Host "🧠 Training model with production settings..." -ForegroundColor Cyan
    python scripts/train_model.py data/ecom_benign.jsonl --tokenizer_dir tokenizer_production --output_dir model_production --max_samples 10000 --batch_size 32 --num_epochs 15 --learning_rate 1e-4 --hidden_size 512 --num_hidden_layers 8 --num_attention_heads 8
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Production training completed successfully!" -ForegroundColor Green
        Write-Host "Model saved in: model_production/" -ForegroundColor Yellow
    } else {
        Write-Host "❌ Model training failed!" -ForegroundColor Red
    }
} else {
    Write-Host "❌ Tokenizer training failed!" -ForegroundColor Red
}