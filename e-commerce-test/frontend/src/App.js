import React, { useState, useEffect } from 'react';
import { Routes, Route, Link, useNavigate, useLocation } from 'react-router-dom';
import axios from 'axios';

// API service
const api = axios.create({
  baseURL: 'http://localhost:5000',
  withCredentials: true
});

// Header component
function Header({ cartCount, onSearch }) {
  const [searchQuery, setSearchQuery] = useState('');
  const navigate = useNavigate();

  const handleSearch = (e) => {
    e.preventDefault();
    if (searchQuery.trim()) {
      onSearch(searchQuery);
      navigate(`/search?q=${encodeURIComponent(searchQuery)}`);
    }
  };

  return (
    <header className="header">
      <div className="container">
        <nav className="nav">
          <Link to="/store" className="logo">🛍️ E-Store</Link>
          
          <ul className="nav-links">
            <li><Link to="/store">Home</Link></li>
            <li><Link to="/store/category/1">Electronics</Link></li>
            <li><Link to="/store/category/2">Fashion</Link></li>
            <li><Link to="/store/category/3">Home</Link></li>
          </ul>
          
          <form className="search-box" onSubmit={handleSearch}>
            <input
              type="text"
              className="search-input"
              placeholder="Search products..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
            <button type="submit" className="search-btn">Search</button>
          </form>
          
          <Link to="/store/cart">
            Cart {cartCount > 0 && <span className="cart-badge">{cartCount}</span>}
          </Link>
        </nav>
      </div>
    </header>
  );
}

// Product card component
function ProductCard({ product, onAddToCart }) {
  return (
    <div className="product-card">
      <div className="product-category">{product.category}</div>
      <h3 className="product-title">{product.name}</h3>
      <div className="product-price">${product.price}</div>
      <p>Rating: {product.rating}/5</p>
      <div style={{ marginTop: '1rem', display: 'flex', gap: '0.5rem' }}>
        <Link to={`/store/product/${product.id}`} className="btn btn-primary">
          View Details
        </Link>
        <button 
          className="btn btn-success"
          onClick={() => onAddToCart(product)}
        >
          Add to Cart
        </button>
      </div>
    </div>
  );
}

// Home page component
function HomePage({ products, onAddToCart }) {
  const [categories] = useState(['electronics', 'fashion', 'home', 'beauty', 'sports', 'toys']);
  const [selectedCategory, setSelectedCategory] = useState('');

  const filteredProducts = selectedCategory 
    ? products.filter(p => p.category === selectedCategory)
    : products;

  return (
    <div className="main-content">
      <div className="container">
        <h1>Welcome to E-Store</h1>
        
        <div className="categories-list">
          <button 
            className={`category-btn ${!selectedCategory ? 'active' : ''}`}
            onClick={() => setSelectedCategory('')}
          >
            All Products
          </button>
          {categories.map(category => (
            <button
              key={category}
              className={`category-btn ${selectedCategory === category ? 'active' : ''}`}
              onClick={() => setSelectedCategory(category)}
            >
              {category.charAt(0).toUpperCase() + category.slice(1)}
            </button>
          ))}
        </div>

        <div className="products-grid">
          {filteredProducts.map(product => (
            <ProductCard 
              key={product.id} 
              product={product} 
              onAddToCart={onAddToCart}
            />
          ))}
        </div>
      </div>
    </div>
  );
}

// Product detail page
function ProductPage({ onAddToCart }) {
  const [product, setProduct] = useState(null);
  const [loading, setLoading] = useState(true);
  const location = useLocation();
  const productId = location.pathname.split('/').pop();

  useEffect(() => {
    const fetchProduct = async () => {
      try {
        const response = await api.get(`/store/product/${productId}`);
        setProduct(response.data);
      } catch (error) {
        console.error('Error fetching product:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchProduct();
  }, [productId]);

  if (loading) return <div className="loading">Loading product...</div>;
  if (!product) return <div className="error">Product not found</div>;

  return (
    <div className="main-content">
      <div className="container">
        <div style={{ display: 'flex', gap: '2rem', alignItems: 'flex-start' }}>
          <div style={{ flex: 1 }}>
            <div style={{ background: '#f8f9fa', height: '300px', borderRadius: '8px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <span style={{ color: '#6c757d' }}>Product Image</span>
            </div>
          </div>
          <div style={{ flex: 1 }}>
            <h1>{product.name}</h1>
            <p className="product-category">{product.category}</p>
            <div className="product-price" style={{ fontSize: '2rem', margin: '1rem 0' }}>
              ${product.price}
            </div>
            <p>Rating: {product.rating}/5</p>
            <p>{product.description}</p>
            <button 
              className="btn btn-success"
              style={{ fontSize: '1.1rem', padding: '1rem 2rem' }}
              onClick={() => onAddToCart(product)}
            >
              Add to Cart
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// Search page
function SearchPage({ searchQuery, onAddToCart }) {
  const [searchResults, setSearchResults] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (searchQuery) {
      const fetchSearchResults = async () => {
        setLoading(true);
        try {
          const response = await api.get(`/store/search?q=${encodeURIComponent(searchQuery)}`);
          setSearchResults(response.data.results || []);
        } catch (error) {
          console.error('Error searching products:', error);
        } finally {
          setLoading(false);
        }
      };

      fetchSearchResults();
    }
  }, [searchQuery]);

  if (loading) return <div className="loading">Searching...</div>;

  return (
    <div className="main-content">
      <div className="container">
        <h1>Search Results for "{searchQuery}"</h1>
        {searchResults.length === 0 ? (
          <p>No products found for your search.</p>
        ) : (
          <div className="products-grid">
            {searchResults.map(product => (
              <ProductCard 
                key={product.id} 
                product={product} 
                onAddToCart={onAddToCart}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// Cart page
function CartPage({ cart, onUpdateCart, onRemoveFromCart }) {
  const [isCheckingOut, setIsCheckingOut] = useState(false);
  
  const total = cart.reduce((sum, item) => sum + (item.price * item.qty), 0);

  const handleCheckout = async () => {
    setIsCheckingOut(true);
    try {
      const response = await api.post('/store/api/checkout/create', {
        payment: 'card',
        addrId: '123'
      });
      alert(`Order created! Order ID: ${response.data.order_id}`);
      // Clear cart
      cart.forEach(item => onRemoveFromCart(item.productId));
    } catch (error) {
      console.error('Error during checkout:', error);
      alert('Checkout failed. Please try again.');
    } finally {
      setIsCheckingOut(false);
    }
  };

  return (
    <div className="main-content">
      <div className="container">
        <h1>Shopping Cart</h1>
        {cart.length === 0 ? (
          <p>Your cart is empty</p>
        ) : (
          <>
            {cart.map(item => (
              <div key={item.productId} className="cart-item">
                <div>
                  <h3>{item.name}</h3>
                  <p>${item.price} x {item.qty}</p>
                </div>
                <div>
                  <button 
                    className="btn btn-primary"
                    onClick={() => onUpdateCart(item.productId, item.qty + 1)}
                    style={{ marginRight: '0.5rem' }}
                  >
                    +
                  </button>
                  <button 
                    className="btn btn-primary"
                    onClick={() => onUpdateCart(item.productId, Math.max(1, item.qty - 1))}
                    style={{ marginRight: '0.5rem' }}
                  >
                    -
                  </button>
                  <button 
                    className="btn"
                    onClick={() => onRemoveFromCart(item.productId)}
                    style={{ backgroundColor: '#e74c3c', color: 'white' }}
                  >
                    Remove
                  </button>
                </div>
              </div>
            ))}
            <div className="cart-total">
              Total: ${total.toFixed(2)}
            </div>
            <button 
              className="btn btn-success"
              onClick={handleCheckout}
              disabled={isCheckingOut}
              style={{ fontSize: '1.1rem', padding: '1rem 2rem', marginTop: '1rem' }}
            >
              {isCheckingOut ? 'Processing...' : 'Checkout'}
            </button>
          </>
        )}
      </div>
    </div>
  );
}

// Main App component
function App() {
  const [products, setProducts] = useState([]);
  const [cart, setCart] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Fetch initial products
    const fetchProducts = async () => {
      try {
        const response = await api.get('/store/api/products');
        setProducts(response.data.products || []);
      } catch (error) {
        console.error('Error fetching products:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchProducts();
  }, []);

  const handleAddToCart = async (product) => {
    try {
      await api.post('/store/api/cart/add', {
        productId: product.id,
        qty: 1
      });
      
      // Update local cart state
      const existingItem = cart.find(item => item.productId === product.id);
      if (existingItem) {
        setCart(cart.map(item => 
          item.productId === product.id 
            ? { ...item, qty: item.qty + 1 }
            : item
        ));
      } else {
        setCart([...cart, {
          productId: product.id,
          name: product.name,
          price: product.price,
          qty: 1
        }]);
      }
      
      alert('Product added to cart!');
    } catch (error) {
      console.error('Error adding to cart:', error);
    }
  };

  const handleUpdateCart = (productId, newQty) => {
    if (newQty <= 0) {
      handleRemoveFromCart(productId);
      return;
    }
    
    setCart(cart.map(item => 
      item.productId === productId 
        ? { ...item, qty: newQty }
        : item
    ));
  };

  const handleRemoveFromCart = (productId) => {
    setCart(cart.filter(item => item.productId !== productId));
  };

  const handleSearch = (query) => {
    setSearchQuery(query);
  };

  if (loading) return <div className="loading">Loading...</div>;

  return (
    <div className="App">
      <Header cartCount={cart.length} onSearch={handleSearch} />
      
      <Routes>
        <Route 
          path="/store" 
          element={<HomePage products={products} onAddToCart={handleAddToCart} />} 
        />
        <Route 
          path="/store/product/:id" 
          element={<ProductPage onAddToCart={handleAddToCart} />} 
        />
        <Route 
          path="/store/search" 
          element={<SearchPage searchQuery={searchQuery} onAddToCart={handleAddToCart} />} 
        />
        <Route 
          path="/store/cart" 
          element={
            <CartPage 
              cart={cart} 
              onUpdateCart={handleUpdateCart}
              onRemoveFromCart={handleRemoveFromCart}
            />
          } 
        />
        <Route 
          path="/" 
          element={<HomePage products={products} onAddToCart={handleAddToCart} />} 
        />
      </Routes>
    </div>
  );
}

export default App;