// KICKLAB Ecommerce Interactive Behavior
document.addEventListener('DOMContentLoaded', () => {
    const products = [
        { id: 1, name: 'Air Jordan 1 High OG', category: 'Basketball', price: 180, badge: 'Hot', image: '👟' },
        { id: 2, name: 'Nike Dunk Low Retro', category: 'Casual', price: 115, badge: 'Popular', image: '👟' },
        { id: 3, name: 'Yeezy Boost 350 V2', category: 'Running', price: 230, badge: 'Limited', image: '👟' },
        { id: 4, name: 'Adidas Samba OG', category: 'Casual', price: 100, badge: 'Trending', image: '👟' },
        { id: 5, name: 'New Balance 990v6', category: 'Running', price: 200, badge: 'Premium', image: '👟' },
        { id: 6, name: 'Puma Suede Classic', category: 'Casual', price: 75, badge: 'Classic', image: '👟' },
        { id: 7, name: 'Converse Chuck 70', category: 'Casual', price: 90, badge: 'Iconic', image: '👟' },
        { id: 8, name: 'ASICS GEL-Kayano 14', category: 'Running', price: 150, badge: 'New', image: '👟' }
    ];

    let cart = [];
    const productGrid = document.getElementById('product-grid');
    const searchInput = document.getElementById('search-input');
    const categoryBtns = document.querySelectorAll('.category-btn');
    const cartBtn = document.getElementById('cart-btn');
    const closeCart = document.getElementById('close-cart');
    const cartDrawer = document.getElementById('cart-drawer');
    const cartItems = document.getElementById('cart-items');
    const cartCount = document.getElementById('cart-count');
    const cartSubtotal = document.getElementById('cart-subtotal');

    function renderProducts(items) {
        if (!productGrid) return;
        if (items.length === 0) {
            productGrid.innerHTML = '<div class="empty-state">No products found matching your criteria.</div>';
            return;
        }
        productGrid.innerHTML = items.map(p => `
            <div class="product-card">
                <span class="product-badge">${p.badge}</span>
                <div class="product-img-box">${p.image}</div>
                <div class="product-info">
                    <span class="product-cat">${p.category}</span>
                    <h3 class="product-title">${p.name}</h3>
                    <div class="product-footer">
                        <span class="product-price">$${p.price.toFixed(2)}</span>
                        <button class="add-to-cart-btn" data-id="${p.id}">Add to Cart</button>
                    </div>
                </div>
            </div>
        `).join('');

        document.querySelectorAll('.add-to-cart-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const id = parseInt(e.target.getAttribute('data-id'));
                addToCart(id);
            });
        });
    }

    function addToCart(id) {
        const item = products.find(p => p.id === id);
        if (!item) return;
        const existing = cart.find(c => c.id === id);
        if (existing) {
            existing.qty += 1;
        } else {
            cart.push({ ...item, qty: 1 });
        }
        updateCart();
        openCart();
    }

    function updateCart() {
        if (!cartCount || !cartItems || !cartSubtotal) return;
        const totalItems = cart.reduce((sum, item) => sum + item.qty, 0);
        const subtotal = cart.reduce((sum, item) => sum + (item.price * item.qty), 0);
        cartCount.textContent = totalItems;
        cartSubtotal.textContent = `$${subtotal.toFixed(2)}`;

        if (cart.length === 0) {
            cartItems.innerHTML = '<div class="empty-cart">Your cart is currently empty.</div>';
        } else {
            cartItems.innerHTML = cart.map(item => `
                <div class="cart-item">
                    <div class="cart-item-details">
                        <h4>${item.name}</h4>
                        <p>$${item.price} x ${item.qty}</p>
                    </div>
                    <div class="cart-item-actions">
                        <button class="qty-btn remove-qty" data-id="${item.id}">-</button>
                        <span>${item.qty}</span>
                        <button class="qty-btn add-qty" data-id="${item.id}">+</button>
                    </div>
                </div>
            `).join('');

            document.querySelectorAll('.add-qty').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    const id = parseInt(e.target.getAttribute('data-id'));
                    const item = cart.find(c => c.id === id);
                    if (item) { item.qty += 1; updateCart(); }
                });
            });

            document.querySelectorAll('.remove-qty').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    const id = parseInt(e.target.getAttribute('data-id'));
                    const idx = cart.findIndex(c => c.id === id);
                    if (idx !== -1) {
                        if (cart[idx].qty > 1) { cart[idx].qty -= 1; }
                        else { cart.splice(idx, 1); }
                        updateCart();
                    }
                });
            });
        }
    }

    function openCart() { if (cartDrawer) cartDrawer.classList.add('open'); }
    function closeCartDrawer() { if (cartDrawer) cartDrawer.classList.remove('open'); }

    if (cartBtn) cartBtn.addEventListener('click', openCart);
    if (closeCart) closeCart.addEventListener('click', closeCartDrawer);

    if (searchInput) {
        searchInput.addEventListener('input', (e) => {
            const query = e.target.value.toLowerCase().trim();
            const filtered = products.filter(p => p.name.toLowerCase().includes(query) || p.category.toLowerCase().includes(query));
            renderProducts(filtered);
        });
    }

    categoryBtns.forEach(btn => {
        btn.addEventListener('click', (e) => {
            categoryBtns.forEach(b => b.classList.remove('active'));
            e.target.classList.add('active');
            const cat = e.target.getAttribute('data-category');
            if (cat === 'All') {
                renderProducts(products);
            } else {
                renderProducts(products.filter(p => p.category === cat));
            }
        });
    });

    renderProducts(products);
    updateCart();
});
