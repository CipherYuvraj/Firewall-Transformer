#!/usr/bin/env python3
"""
E-commerce Backend API
Designed to generate traffic patterns matching WAF Transformer training data
"""

from flask import Flask, request, jsonify, session
from flask_cors import CORS
import json
import random
import time
import logging
from datetime import datetime
import uuid

app = Flask(__name__)
app.secret_key = 'ecommerce-secret-key-2025'
CORS(app, supports_credentials=True)

# Configure logging for Kafka pipeline compatibility
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Sample data matching training patterns
CATEGORIES = ["electronics", "fashion", "home", "beauty", "sports", "toys"]
SEARCH_TERMS = ["shoe", "shirt", "laptop", "phone", "headphones", "bag", "watch", "book"]
PAYMENT_METHODS = ["card", "cod", "wallet"]

# Sample products
PRODUCTS = []
for i in range(1, 101):
    PRODUCTS.append({
        "id": i,
        "name": f"Product {i}",
        "category": random.choice(CATEGORIES),
        "price": round(random.uniform(10, 500), 2),
        "rating": round(random.uniform(3.0, 5.0), 1),
        "description": f"High quality {random.choice(SEARCH_TERMS)}"
    })

def log_request():
    """Log request in format compatible with model training data"""
    try:
        # Extract request details
        method = request.method
        path = request.path
        query_params = dict(request.args)
        headers = dict(request.headers)
        user_agent = headers.get('User-Agent', 'Unknown')
        content_type = headers.get('Content-Type', 'text/plain')
        content_length = headers.get('Content-Length', '0')
        
        # Get cookies
        cookies = list(request.cookies.keys())
        
        # Get body for POST requests
        body = ""
        if method == "POST" and request.is_json:
            body = json.dumps(request.get_json())
        elif method == "POST":
            body = str(request.form.to_dict())
        
        # Create log entry matching training format
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "method": method,
            "path": path,
            "query": query_params,
            "headers": {
                "ua": user_agent,
                "ct": content_type,
                "cl": content_length
            },
            "cookies": cookies,
            "body": body,
            "source": request.remote_addr
        }
        
        logger.info(f"REQUEST: {json.dumps(log_entry)}")
        
    except Exception as e:
        logger.error(f"Error logging request: {e}")

@app.before_request
def before_request():
    """Log all requests before processing"""
    log_request()

# Root and Home Routes
@app.route('/store')
@app.route('/store/')
@app.route('/store/home')
def home():
    """Home page - matches training pattern: GET /store/home"""
    return jsonify({
        "page": "home",
        "featured_products": random.sample(PRODUCTS, 6),
        "categories": CATEGORIES
    })

# Product Routes
@app.route('/store/product/<int:product_id>')
def get_product(product_id):
    """Get single product - matches: GET /store/product/:num"""
    product = next((p for p in PRODUCTS if p["id"] == product_id), None)
    if not product:
        return jsonify({"error": "Product not found"}), 404
    
    return jsonify(product)

@app.route('/store/api/products')
def get_products():
    """Get products with filters - matches: GET /store/api/products ? category=fashion&page=:num"""
    category = request.args.get('category')
    page = int(request.args.get('page', 1))
    per_page = 20
    
    filtered_products = PRODUCTS
    if category:
        filtered_products = [p for p in PRODUCTS if p["category"] == category]
    
    # Pagination
    start = (page - 1) * per_page
    end = start + per_page
    page_products = filtered_products[start:end]
    
    return jsonify({
        "products": page_products,
        "page": page,
        "total": len(filtered_products),
        "has_more": end < len(filtered_products)
    })

# Search Routes
@app.route('/store/search')
def search_products():
    """Search products - matches: GET /store/search ? page=:num&q=laptop"""
    query = request.args.get('q', '')
    page = int(request.args.get('page', 1))
    per_page = 20
    
    if query:
        results = [p for p in PRODUCTS if query.lower() in p["name"].lower() or query.lower() in p["description"].lower()]
    else:
        results = PRODUCTS
    
    start = (page - 1) * per_page
    end = start + per_page
    page_results = results[start:end]
    
    return jsonify({
        "query": query,
        "results": page_results,
        "page": page,
        "total": len(results)
    })

@app.route('/store/api/suggest')
def suggest():
    """Search suggestions - matches: GET /store/api/suggest ? q=laptop"""
    query = request.args.get('q', '')
    suggestions = [term for term in SEARCH_TERMS if query.lower() in term.lower()]
    return jsonify({"suggestions": suggestions[:5]})

# Category Routes
@app.route('/store/category/<int:category_id>')
def get_category(category_id):
    """Get category products - matches: GET /store/category/:num ? page=:num&sort=price"""
    if category_id < 1 or category_id > len(CATEGORIES):
        return jsonify({"error": "Category not found"}), 404
    
    category = CATEGORIES[category_id - 1]
    page = int(request.args.get('page', 1))
    sort_by = request.args.get('sort', 'name')
    per_page = 20
    
    category_products = [p for p in PRODUCTS if p["category"] == category]
    
    # Sort products
    if sort_by == 'price':
        category_products.sort(key=lambda x: x['price'])
    elif sort_by == 'rating':
        category_products.sort(key=lambda x: x['rating'], reverse=True)
    
    start = (page - 1) * per_page
    end = start + per_page
    page_products = category_products[start:end]
    
    return jsonify({
        "category": category,
        "products": page_products,
        "page": page,
        "total": len(category_products)
    })

# Cart Routes
@app.route('/store/cart')
def get_cart():
    """Get cart - matches: GET /store/cart"""
    cart_items = session.get('cart', [])
    total = sum(item.get('price', 0) * item.get('qty', 1) for item in cart_items)
    
    return jsonify({
        "items": cart_items,
        "total": total,
        "count": len(cart_items)
    })

@app.route('/store/api/cart/add', methods=['POST'])
def add_to_cart():
    """Add to cart - matches: POST /store/api/cart/add"""
    data = request.get_json() or {}
    product_id = data.get('productId')
    qty = data.get('qty', 1)
    
    if not product_id:
        return jsonify({"error": "Product ID required"}), 400
    
    product = next((p for p in PRODUCTS if p["id"] == int(product_id)), None)
    if not product:
        return jsonify({"error": "Product not found"}), 404
    
    cart = session.get('cart', [])
    cart.append({
        "productId": product_id,
        "name": product["name"],
        "price": product["price"],
        "qty": qty
    })
    session['cart'] = cart
    
    return jsonify({"success": True, "cart_count": len(cart)})

@app.route('/store/api/cart/update', methods=['POST'])
def update_cart():
    """Update cart - matches: POST /store/api/cart/update"""
    data = request.get_json() or {}
    product_id = data.get('productId')
    qty = data.get('qty', 1)
    
    cart = session.get('cart', [])
    for item in cart:
        if item.get('productId') == product_id:
            item['qty'] = qty
            break
    
    session['cart'] = cart
    return jsonify({"success": True})

# Checkout Routes
@app.route('/store/checkout')
def checkout_page():
    """Checkout page - matches: GET /store/checkout"""
    cart = session.get('cart', [])
    total = sum(item.get('price', 0) * item.get('qty', 1) for item in cart)
    
    return jsonify({
        "cart": cart,
        "total": total,
        "payment_methods": PAYMENT_METHODS
    })

@app.route('/store/api/checkout/create', methods=['POST'])
def create_checkout():
    """Create checkout - matches: POST /store/api/checkout/create"""
    data = request.get_json() or {}
    payment_method = data.get('payment')
    address_id = data.get('addrId')
    
    if payment_method not in PAYMENT_METHODS:
        return jsonify({"error": "Invalid payment method"}), 400
    
    # Create order
    order_id = random.randint(1000, 9999)
    cart = session.get('cart', [])
    total = sum(item.get('price', 0) * item.get('qty', 1) for item in cart)
    
    # Clear cart
    session['cart'] = []
    
    return jsonify({
        "order_id": order_id,
        "total": total,
        "payment_method": payment_method,
        "status": "confirmed"
    })

# Order Routes
@app.route('/store/order/<int:order_id>')
def get_order(order_id):
    """Get order - matches: GET /store/order/:num"""
    return jsonify({
        "order_id": order_id,
        "status": "delivered",
        "total": round(random.uniform(50, 300), 2),
        "items": random.randint(1, 5)
    })

# User Routes
@app.route('/store/api/user/register', methods=['POST'])
def register_user():
    """Register user - matches: POST /store/api/user/register"""
    data = request.get_json() or {}
    ref = data.get('ref', 'direct')
    lang = data.get('lang', 'en')
    
    user_id = str(uuid.uuid4())
    session['user_id'] = user_id
    
    return jsonify({
        "user_id": user_id,
        "status": "registered",
        "ref": ref,
        "lang": lang
    })

@app.route('/store/api/user/login', methods=['POST'])
def login_user():
    """Login user - matches: POST /store/api/user/login"""
    data = request.get_json() or {}
    email = data.get('email')
    has_pwd = data.get('hasPwd')
    
    if not email:
        return jsonify({"error": "Email required"}), 400
    
    user_id = str(uuid.uuid4())
    session['user_id'] = user_id
    
    return jsonify({
        "user_id": user_id,
        "email": email,
        "status": "logged_in"
    })

# Wishlist Routes
@app.route('/store/api/wishlist/add', methods=['POST'])
def add_to_wishlist():
    """Add to wishlist - matches: POST /store/api/wishlist/add"""
    data = request.get_json() or {}
    product_id = data.get('productId')
    
    if not product_id:
        return jsonify({"error": "Product ID required"}), 400
    
    wishlist = session.get('wishlist', [])
    if product_id not in wishlist:
        wishlist.append(product_id)
        session['wishlist'] = wishlist
    
    return jsonify({"success": True, "wishlist_count": len(wishlist)})

# Reviews Routes
@app.route('/store/api/reviews/<int:product_id>')
def get_reviews(product_id):
    """Get product reviews - matches: GET /store/api/reviews/:num ? page=:num"""
    page = int(request.args.get('page', 1))
    per_page = 10
    
    # Generate sample reviews
    reviews = []
    for i in range(per_page):
        reviews.append({
            "id": i + (page - 1) * per_page,
            "rating": random.randint(3, 5),
            "comment": f"Great product {i+1}!",
            "user": f"User{i+1}"
        })
    
    return jsonify({
        "product_id": product_id,
        "reviews": reviews,
        "page": page
    })

@app.route('/store/api/review/submit', methods=['POST'])
def submit_review():
    """Submit review - matches: POST /store/api/review/submit"""
    data = request.get_json() or {}
    product_id = data.get('productId')
    rating = data.get('rating')
    
    if not product_id or not rating:
        return jsonify({"error": "Product ID and rating required"}), 400
    
    return jsonify({
        "success": True,
        "product_id": product_id,
        "rating": rating
    })

# Health check
@app.route('/health')
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "timestamp": datetime.now().isoformat()})

if __name__ == '__main__':
    print("🛍️  Starting E-commerce Backend API...")
    print("📊 Configured to match WAF Transformer training patterns")
    print("🔍 Request logging enabled for Kafka pipeline")
    print("🚀 Server starting on http://localhost:5000")
    
    app.run(debug=True, host='0.0.0.0', port=5000)