from flask import Blueprint, request, jsonify, current_app, g
from flask_jwt_extended import jwt_required, get_jwt_identity, create_access_token, get_jwt
from werkzeug.security import check_password_hash, generate_password_hash
import sqlite3
import os
from datetime import datetime
import json

# Create API blueprint for customer/user endpoints
api = Blueprint('api', __name__, url_prefix='/api')

def get_db_connection():
    conn = sqlite3.connect(current_app.config['DATABASE'])
    conn.row_factory = sqlite3.Row
    return conn

# Helper functions
def row_to_dict(row):
    return {key: row[key] for key in row.keys()}

# User Authentication endpoints
@api.route('/auth/login', methods=['POST'])
def login():
    data = request.get_json()
    
    if not data or not data.get('email') or not data.get('password'):
        return jsonify({'message': 'Missing email or password'}), 400
    
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE email = ?', (data['email'],)).fetchone()
    conn.close()
    
    if not user or not check_password_hash(user['password_hash'], data['password']):
        return jsonify({'message': 'Invalid email or password'}), 401
    
    # Create access token with user id
    access_token = create_access_token(identity=user['id'])
    return jsonify({'access_token': access_token, 'user_id': user['id']}), 200

@api.route('/auth/register', methods=['POST'])
def register():
    data = request.get_json()
    
    if not data or not data.get('username') or not data.get('email') or not data.get('password'):
        return jsonify({'message': 'Missing registration information'}), 400
    
    conn = get_db_connection()
    
    # Check if email already exists
    existing_user = conn.execute('SELECT id FROM users WHERE email = ?', (data['email'],)).fetchone()
    if existing_user:
        conn.close()
        return jsonify({'message': 'Email address already registered'}), 400
    
    # Check if username already exists
    existing_username = conn.execute('SELECT id FROM users WHERE username = ?', (data['username'],)).fetchone()
    if existing_username:
        conn.close()
        return jsonify({'message': 'Username already taken'}), 400
    
    try:
        # Create new user
        password_hash = generate_password_hash(data['password'])
        cursor = conn.execute(
            'INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)',
            (data['username'], data['email'], password_hash)
        )
        user_id = cursor.lastrowid
        
        # Create empty profile if profile data is provided
        if 'profile' in data:
            profile = data['profile']
            conn.execute('''
            INSERT INTO user_profiles (user_id, first_name, last_name, address, city, state, zip, phone)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                user_id,
                profile.get('first_name', ''),
                profile.get('last_name', ''),
                profile.get('address', ''),
                profile.get('city', ''),
                profile.get('state', ''),
                profile.get('zip', ''),
                profile.get('phone', '')
            ))
        
        conn.commit()
        conn.close()
        
        # Create access token
        access_token = create_access_token(identity=user_id)
        
        return jsonify({
            'message': 'Registration successful',
            'user_id': user_id,
            'access_token': access_token
        }), 201
    except Exception as e:
        conn.close()
        return jsonify({'message': f'Error registering user: {str(e)}'}), 500

# Public Product endpoints - no authentication required
@api.route('/products', methods=['GET'])
def get_products():
    category_id = request.args.get('category', type=int)
    search_query = request.args.get('search', '')
    
    conn = get_db_connection()
    
    query = '''
    SELECT p.*, c.name as category_name 
    FROM products p
    JOIN categories c ON p.category_id = c.id
    '''
    params = []
    
    if category_id:
        query += ' WHERE p.category_id = ?'
        params.append(category_id)
        if search_query:
            query += ' AND (p.name LIKE ? OR p.description LIKE ?)'
            params.extend(['%' + search_query + '%', '%' + search_query + '%'])
    elif search_query:
        query += ' WHERE p.name LIKE ? OR p.description LIKE ?'
        params.extend(['%' + search_query + '%', '%' + search_query + '%'])
    
    query += ' ORDER BY p.name'
    
    products = conn.execute(query, params).fetchall()
    conn.close()
    
    return jsonify({'products': [row_to_dict(product) for product in products]}), 200

@api.route('/products/<int:product_id>', methods=['GET'])
def get_product(product_id):
    conn = get_db_connection()
    product = conn.execute('''
    SELECT p.*, c.name as category_name 
    FROM products p
    JOIN categories c ON p.category_id = c.id
    WHERE p.id = ?
    ''', (product_id,)).fetchone()
    
    if product is None:
        conn.close()
        return jsonify({'message': 'Product not found'}), 404
    
    # Get related products
    related_products = conn.execute('''
    SELECT p.*, c.name as category_name 
    FROM products p
    JOIN categories c ON p.category_id = c.id
    WHERE p.category_id = ? AND p.id != ?
    LIMIT 4
    ''', (product['category_id'], product_id)).fetchall()
    
    conn.close()
    
    response = {
        'product': row_to_dict(product),
        'related_products': [row_to_dict(p) for p in related_products]
    }
    
    return jsonify(response), 200

# Public Category endpoints - no authentication required
@api.route('/categories', methods=['GET'])
def get_categories():
    conn = get_db_connection()
    categories = conn.execute('SELECT * FROM categories ORDER BY name').fetchall()
    conn.close()
    
    return jsonify({'categories': [row_to_dict(category) for category in categories]}), 200

@api.route('/categories/<int:category_id>', methods=['GET'])
def get_category(category_id):
    conn = get_db_connection()
    category = conn.execute('SELECT * FROM categories WHERE id = ?', (category_id,)).fetchone()
    
    if category is None:
        conn.close()
        return jsonify({'message': 'Category not found'}), 404
    
    # Get products in this category
    products = conn.execute('''
    SELECT p.*, c.name as category_name 
    FROM products p
    JOIN categories c ON p.category_id = c.id
    WHERE p.category_id = ?
    ''', (category_id,)).fetchall()
    
    conn.close()
    
    response = {
        'category': row_to_dict(category),
        'products': [row_to_dict(product) for product in products]
    }
    
    return jsonify(response), 200

# User profile endpoints - requires authentication
@api.route('/users/profile', methods=['GET'])
@jwt_required()
def get_user_profile():
    user_id = get_jwt_identity()
    conn = get_db_connection()
    
    user = conn.execute('SELECT id, username, email FROM users WHERE id = ?', (user_id,)).fetchone()
    profile = conn.execute('SELECT * FROM user_profiles WHERE user_id = ?', (user_id,)).fetchone()
    
    conn.close()
    
    if not user:
        return jsonify({'message': 'User not found'}), 404
    
    user_data = row_to_dict(user)
    
    if profile:
        user_data['profile'] = row_to_dict(profile)
    else:
        user_data['profile'] = None
    
    return jsonify({'user': user_data}), 200

@api.route('/users/profile', methods=['PUT'])
@jwt_required()
def update_user_profile():
    user_id = get_jwt_identity()
    data = request.get_json()
    
    if not data:
        return jsonify({'message': 'No data provided'}), 400
    
    conn = get_db_connection()
    
    # Check if profile exists
    profile = conn.execute('SELECT * FROM user_profiles WHERE user_id = ?', (user_id,)).fetchone()
    
    try:
        if profile:
            # Update existing profile
            conn.execute('''
            UPDATE user_profiles
            SET first_name = ?, last_name = ?, address = ?, city = ?, state = ?, zip = ?, phone = ?
            WHERE user_id = ?
            ''', (
                data.get('first_name', profile['first_name']),
                data.get('last_name', profile['last_name']),
                data.get('address', profile['address']),
                data.get('city', profile['city']),
                data.get('state', profile['state']),
                data.get('zip', profile['zip']),
                data.get('phone', profile['phone']),
                user_id
            ))
        else:
            # Create new profile
            conn.execute('''
            INSERT INTO user_profiles (user_id, first_name, last_name, address, city, state, zip, phone)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                user_id,
                data.get('first_name', ''),
                data.get('last_name', ''),
                data.get('address', ''),
                data.get('city', ''),
                data.get('state', ''),
                data.get('zip', ''),
                data.get('phone', '')
            ))
        
        # Update username if provided
        if 'username' in data:
            conn.execute('UPDATE users SET username = ? WHERE id = ?', (data['username'], user_id))
        
        conn.commit()
        conn.close()
        
        return jsonify({'message': 'Profile updated successfully'}), 200
    except Exception as e:
        conn.close()
        return jsonify({'message': f'Error updating profile: {str(e)}'}), 500

@api.route('/users/password', methods=['PUT'])
@jwt_required()
def change_password():
    user_id = get_jwt_identity()
    data = request.get_json()
    
    if not data or not data.get('current_password') or not data.get('new_password'):
        return jsonify({'message': 'Current and new password required'}), 400
    
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    
    if not user or not check_password_hash(user['password_hash'], data['current_password']):
        conn.close()
        return jsonify({'message': 'Current password is incorrect'}), 401
    
    try:
        password_hash = generate_password_hash(data['new_password'])
        conn.execute('UPDATE users SET password_hash = ? WHERE id = ?', (password_hash, user_id))
        conn.commit()
        conn.close()
        
        return jsonify({'message': 'Password updated successfully'}), 200
    except Exception as e:
        conn.close()
        return jsonify({'message': f'Error updating password: {str(e)}'}), 500

# Orders endpoints - requires authentication
@api.route('/orders', methods=['GET'])
@jwt_required()
def get_user_orders():
    user_id = get_jwt_identity()
    conn = get_db_connection()
    
    orders = conn.execute('''
    SELECT * FROM orders WHERE user_id = ? ORDER BY order_date DESC
    ''', (user_id,)).fetchall()
    
    conn.close()
    
    return jsonify({'orders': [row_to_dict(order) for order in orders]}), 200

@api.route('/orders/<int:order_id>', methods=['GET'])
@jwt_required()
def get_order_detail(order_id):
    user_id = get_jwt_identity()
    conn = get_db_connection()
    
    # Ensure order belongs to user
    order = conn.execute('SELECT * FROM orders WHERE id = ? AND user_id = ?', (order_id, user_id)).fetchone()
    
    if not order:
        conn.close()
        return jsonify({'message': 'Order not found'}), 404
    
    # Get order items
    items = conn.execute('''
    SELECT oi.*, p.name as product_name, p.image_url
    FROM order_items oi
    JOIN products p ON oi.product_id = p.id
    WHERE oi.order_id = ?
    ''', (order_id,)).fetchall()
    
    conn.close()
    
    order_data = row_to_dict(order)
    try:
        order_data['shipping_info'] = json.loads(order_data['shipping_info'])
    except:
        pass
    
    order_data['items'] = [row_to_dict(item) for item in items]
    
    return jsonify({'order': order_data}), 200

@api.route('/orders', methods=['POST'])
@jwt_required()
def create_order():
    user_id = get_jwt_identity()
    data = request.get_json()
    
    if not data or not data.get('cart_items') or not data.get('shipping_info'):
        return jsonify({'message': 'Missing order information'}), 400
    
    cart_items = data['cart_items']
    shipping_info = data['shipping_info']
    
    if not isinstance(cart_items, list) or len(cart_items) == 0:
        return jsonify({'message': 'Cart items must be a non-empty list'}), 400
    
    conn = get_db_connection()
    
    try:
        # Calculate total amount and check stock
        total_amount = 0
        for item in cart_items:
            product = conn.execute('SELECT * FROM products WHERE id = ?', (item['product_id'],)).fetchone()
            
            if not product:
                conn.close()
                return jsonify({'message': f'Product with ID {item["product_id"]} not found'}), 404
            
            if product['stock'] < item['quantity']:
                conn.close()
                return jsonify({'message': f'Not enough stock for {product["name"]}'}), 400
            
            total_amount += product['price'] * item['quantity']
        
        # Create order
        cursor = conn.execute('''
        INSERT INTO orders (user_id, order_date, total_amount, status, shipping_info)
        VALUES (?, ?, ?, ?, ?)
        ''', (user_id, datetime.now().isoformat(), total_amount, 'Pending', json.dumps(shipping_info)))
        
        order_id = cursor.lastrowid
        
        # Create order items and update stock
        for item in cart_items:
            product = conn.execute('SELECT * FROM products WHERE id = ?', (item['product_id'],)).fetchone()
            
            conn.execute('''
            INSERT INTO order_items (order_id, product_id, quantity, price)
            VALUES (?, ?, ?, ?)
            ''', (order_id, item['product_id'], item['quantity'], product['price']))
            
            conn.execute('''
            UPDATE products
            SET stock = stock - ?
            WHERE id = ?
            ''', (item['quantity'], item['product_id']))
        
        # Clear user's cart
        conn.execute('DELETE FROM cart WHERE user_id = ?', (user_id,))
        
        conn.commit()
        conn.close()
        
        return jsonify({'message': 'Order created successfully', 'order_id': order_id}), 201
    except Exception as e:
        conn.close()
        return jsonify({'message': f'Error creating order: {str(e)}'}), 500

# Cart endpoints - requires authentication
@api.route('/cart', methods=['GET'])
@jwt_required()
def get_cart():
    user_id = get_jwt_identity()
    conn = get_db_connection()
    
    cart_items = conn.execute('''
    SELECT c.id, c.product_id, c.quantity, p.name, p.price, p.image_url, p.stock
    FROM cart c
    JOIN products p ON c.product_id = p.id
    WHERE c.user_id = ?
    ''', (user_id,)).fetchall()
    
    conn.close()
    
    return jsonify({'cart_items': [row_to_dict(item) for item in cart_items]}), 200

@api.route('/cart/add', methods=['POST'])
@jwt_required()
def add_to_cart():
    user_id = get_jwt_identity()
    data = request.get_json()
    
    if not data or not data.get('product_id') or not data.get('quantity'):
        return jsonify({'message': 'Product ID and quantity are required'}), 400
    
    product_id = data['product_id']
    quantity = int(data['quantity'])
    
    if quantity <= 0:
        return jsonify({'message': 'Quantity must be greater than zero'}), 400
    
    conn = get_db_connection()
    
    # Check if product exists
    product = conn.execute('SELECT * FROM products WHERE id = ?', (product_id,)).fetchone()
    
    if not product:
        conn.close()
        return jsonify({'message': 'Product not found'}), 404
    
    # Check if enough stock
    if product['stock'] < quantity:
        conn.close()
        return jsonify({'message': 'Not enough stock available'}), 400
    
    # Check if item already in cart
    cart_item = conn.execute('SELECT * FROM cart WHERE user_id = ? AND product_id = ?', 
                            (user_id, product_id)).fetchone()
    
    try:
        if cart_item:
            # Update quantity
            new_quantity = cart_item['quantity'] + quantity
            conn.execute('''
            UPDATE cart SET quantity = ? WHERE id = ?
            ''', (new_quantity, cart_item['id']))
        else:
            # Add new item
            conn.execute('''
            INSERT INTO cart (user_id, product_id, quantity)
            VALUES (?, ?, ?)
            ''', (user_id, product_id, quantity))
        
        conn.commit()
        conn.close()
        
        return jsonify({'message': 'Item added to cart successfully'}), 200
    except Exception as e:
        conn.close()
        return jsonify({'message': f'Error adding to cart: {str(e)}'}), 500

@api.route('/cart/update', methods=['PUT'])
@jwt_required()
def update_cart():
    user_id = get_jwt_identity()
    data = request.get_json()
    
    if not data or not data.get('cart_items'):
        return jsonify({'message': 'Cart items are required'}), 400
    
    cart_items = data['cart_items']
    
    conn = get_db_connection()
    
    try:
        for item in cart_items:
            if 'id' not in item or 'quantity' not in item:
                continue
                
            if item['quantity'] <= 0:
                # Remove item if quantity is 0 or negative
                conn.execute('DELETE FROM cart WHERE id = ? AND user_id = ?', 
                           (item['id'], user_id))
            else:
                # Update quantity
                conn.execute('UPDATE cart SET quantity = ? WHERE id = ? AND user_id = ?', 
                           (item['quantity'], item['id'], user_id))
        
        conn.commit()
        conn.close()
        
        return jsonify({'message': 'Cart updated successfully'}), 200
    except Exception as e:
        conn.close()
        return jsonify({'message': f'Error updating cart: {str(e)}'}), 500

@api.route('/cart/clear', methods=['DELETE'])
@jwt_required()
def clear_cart():
    user_id = get_jwt_identity()
    conn = get_db_connection()
    
    try:
        conn.execute('DELETE FROM cart WHERE user_id = ?', (user_id,))
        conn.commit()
        conn.close()
        
        return jsonify({'message': 'Cart cleared successfully'}), 200
    except Exception as e:
        conn.close()
        return jsonify({'message': f'Error clearing cart: {str(e)}'}), 500 