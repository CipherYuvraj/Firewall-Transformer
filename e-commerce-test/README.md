# E-commerce Test Application

A simple e-commerce website built with React (JavaScript) frontend and Flask backend, designed to generate traffic patterns that match your WAF Transformer training data.

## 🎯 Purpose

This application is specifically designed to:
- Generate HTTP requests matching your model's training patterns (`/store/*`, `/store/api/*`)
- Provide realistic e-commerce functionality for attack testing
- Log requests in a format compatible with your Kafka pipeline
- Test your anomaly detection model with real traffic

## 🚀 Quick Start

### 1. Start the Backend
```bash
cd backend
pip install -r requirements.txt
python app.py
```
Backend will run on: `http://localhost:5000`

### 2. Start the Frontend
```bash
cd frontend
npm install
npm start
```
Frontend will run on: `http://localhost:3000`

## 📊 API Endpoints (Matching Training Data)

The backend implements all endpoints found in your training data:

### Product Endpoints
- `GET /store/home` - Home page
- `GET /store/product/:id` - Product details
- `GET /store/api/products?category=X&page=Y` - Product listing
- `GET /store/search?q=X&page=Y` - Product search
- `GET /store/api/suggest?q=X` - Search suggestions

### Category Endpoints
- `GET /store/category/:id?page=X&sort=Y` - Category products

### Cart Endpoints
- `GET /store/cart` - View cart
- `POST /store/api/cart/add` - Add to cart
- `POST /store/api/cart/update` - Update cart

### Checkout Endpoints
- `GET /store/checkout` - Checkout page
- `POST /store/api/checkout/create` - Create order

### User Endpoints
- `POST /store/api/user/register` - User registration
- `POST /store/api/user/login` - User login

### Other Endpoints
- `GET /store/order/:id` - Order details
- `POST /store/api/wishlist/add` - Add to wishlist
- `GET /store/api/reviews/:id?page=X` - Product reviews
- `POST /store/api/review/submit` - Submit review

## 🔍 Request Logging

All requests are logged in JSON format compatible with your Kafka pipeline:

```json
{
  "timestamp": "2025-09-23T...",
  "method": "GET",
  "path": "/store/product/1",
  "query": {"page": "1"},
  "headers": {
    "ua": "Mozilla/5.0...",
    "ct": "application/json",
    "cl": "123"
  },
  "cookies": ["sid", "cart"],
  "body": "",
  "source": "127.0.0.1"
}
```

## 🛡️ Testing with Your Model

1. **Start both frontend and backend**
2. **Use the website normally** - browse products, search, add to cart, checkout
3. **Monitor logs** - All requests will be logged to console and can be piped to your Kafka pipeline
4. **Run attack simulations** - Use tools like Burp Suite or custom scripts to test attack patterns
5. **Collect traffic data** - Feed the logged requests to your anomaly detection model

## 🎯 Traffic Patterns Generated

The website generates traffic patterns matching your training data:
- **Normal browsing**: Product views, category navigation, search queries
- **E-commerce actions**: Cart operations, checkout, user registration/login
- **API calls**: Product suggestions, reviews, wishlist operations
- **Various HTTP methods**: GET, POST requests with appropriate headers and payloads

## 🔧 Customization

- **Backend**: Modify `backend/app.py` to add more endpoints or change logging format
- **Frontend**: Update `frontend/src/App.js` to add new features or modify UI
- **Data**: Adjust product categories, search terms, and sample data in `backend/app.py`

## 📝 Notes

- Backend runs on port 5000, frontend on port 3000
- CORS is enabled for cross-origin requests
- Session-based cart management
- Request logging includes all details needed for anomaly detection
- Compatible with your existing Kafka pipeline for log collection