from flask import Blueprint, request, jsonify, current_app, g
from flask_jwt_extended import jwt_required, get_jwt_identity, create_access_token
from werkzeug.security import check_password_hash
import sqlite3
import os
from datetime import datetime
import json

# Create Admin API blueprint
admin_api = Blueprint('admin_api', __name__, url_prefix='/admin/api')

def get_db_connection():
    conn = sqlite3.connect(current_app.config['DATABASE'])
    conn.row_factory = sqlite3.Row
    return conn

# Helper functions
def row_to_dict(row):
    return {key: row[key] for key in row.keys()}

# Admin authentication decorator
def admin_required(fn):
    @jwt_required()
    def admin_wrapper(*args, **kwargs):
        user_id = get_jwt_identity()
        conn = get_db_connection()
        admin = conn.execute('SELECT * FROM admin_users WHERE id = ?', (user_id,)).fetchone()
        conn.close()
        
        if not admin:
            return jsonify({'message': 'Admin privileges required'}), 403
        return fn(*args, **kwargs)
    admin_wrapper.__name__ = fn.__name__ + '_admin'
    return admin_wrapper

# Authentication endpoints
@admin_api.route('/auth/login', methods=['POST'])
def login():
    data = request.get_json()
    
    if not data or not data.get('username') or not data.get('password'):
        return jsonify({'message': 'Missing username or password'}), 400
    
    conn = get_db_connection()
    admin = conn.execute('SELECT * FROM admin_users WHERE username = ?', (data['username'],)).fetchone()
    conn.close()
    
    if not admin or not check_password_hash(admin['password_hash'], data['password']):
        return jsonify({'message': 'Invalid username or password'}), 401
    
    # Create access token with admin id
    access_token = create_access_token(identity=admin['id'])
    return jsonify({
        'access_token': access_token, 
        'admin_id': admin['id'],
        'is_super_admin': bool(admin['is_super_admin'])
    }), 200

# Products management endpoints
@admin_api.route('/products', methods=['GET'])
@admin_required
def get_products():
    conn = get_db_connection()
    products = conn.execute('''
    SELECT p.*, c.name as category_name 
    FROM products p
    LEFT JOIN categories c ON p.category_id = c.id
    ORDER BY p.id DESC
    ''').fetchall()
    conn.close()
    
    return jsonify({'products': [row_to_dict(product) for product in products]}), 200

@admin_api.route('/products/<int:product_id>', methods=['GET'])
@admin_required
def get_product(product_id):
    conn = get_db_connection()
    product = conn.execute('''
    SELECT p.*, c.name as category_name 
    FROM products p
    LEFT JOIN categories c ON p.category_id = c.id
    WHERE p.id = ?
    ''', (product_id,)).fetchone()
    conn.close()
    
    if product is None:
        return jsonify({'message': 'Product not found'}), 404
    
    return jsonify({'product': row_to_dict(product)}), 200

@admin_api.route('/products', methods=['POST'])
@admin_required
def create_product():
    data = request.get_json()
    
    if not data or not all(k in data for k in ('name', 'price', 'stock', 'category_id')):
        return jsonify({'message': 'Missing required product information'}), 400
    
    conn = get_db_connection()
    try:
        cursor = conn.execute('''
        INSERT INTO products (name, description, price, stock, image_url, category_id)
        VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            data['name'], 
            data.get('description', ''), 
            data['price'], 
            data['stock'], 
            data.get('image_url', 'static/images/placeholder.jpg'), 
            data['category_id']
        ))
        
        product_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return jsonify({'message': 'Product created successfully', 'product_id': product_id}), 201
    except Exception as e:
        conn.close()
        return jsonify({'message': f'Error creating product: {str(e)}'}), 500

@admin_api.route('/products/<int:product_id>', methods=['PUT'])
@admin_required
def update_product(product_id):
    conn = get_db_connection()
    product = conn.execute('SELECT * FROM products WHERE id = ?', (product_id,)).fetchone()
    
    if not product:
        conn.close()
        return jsonify({'message': 'Product not found'}), 404
    
    data = request.get_json()
    
    if not data:
        return jsonify({'message': 'No data provided'}), 400
    
    try:
        conn.execute('''
        UPDATE products
        SET name = ?, description = ?, price = ?, stock = ?, image_url = ?, category_id = ?
        WHERE id = ?
        ''', (
            data.get('name', product['name']),
            data.get('description', product['description']),
            data.get('price', product['price']),
            data.get('stock', product['stock']),
            data.get('image_url', product['image_url']),
            data.get('category_id', product['category_id']),
            product_id
        ))
        
        conn.commit()
        conn.close()
        
        return jsonify({'message': 'Product updated successfully'}), 200
    except Exception as e:
        conn.close()
        return jsonify({'message': f'Error updating product: {str(e)}'}), 500

@admin_api.route('/products/<int:product_id>', methods=['DELETE'])
@admin_required
def delete_product(product_id):
    conn = get_db_connection()
    product = conn.execute('SELECT * FROM products WHERE id = ?', (product_id,)).fetchone()
    
    if not product:
        conn.close()
        return jsonify({'message': 'Product not found'}), 404
    
    try:
        conn.execute('DELETE FROM products WHERE id = ?', (product_id,))
        conn.commit()
        conn.close()
        
        return jsonify({'message': 'Product deleted successfully'}), 200
    except Exception as e:
        conn.close()
        return jsonify({'message': f'Error deleting product: {str(e)}'}), 500

# Categories management endpoints
@admin_api.route('/categories', methods=['GET'])
@admin_required
def get_categories():
    conn = get_db_connection()
    categories = conn.execute('SELECT * FROM categories ORDER BY name').fetchall()
    conn.close()
    
    return jsonify({'categories': [row_to_dict(category) for category in categories]}), 200

@admin_api.route('/categories/<int:category_id>', methods=['GET'])
@admin_required
def get_category(category_id):
    conn = get_db_connection()
    category = conn.execute('SELECT * FROM categories WHERE id = ?', (category_id,)).fetchone()
    conn.close()
    
    if category is None:
        return jsonify({'message': 'Category not found'}), 404
    
    return jsonify({'category': row_to_dict(category)}), 200

@admin_api.route('/categories', methods=['POST'])
@admin_required
def create_category():
    data = request.get_json()
    
    if not data or not data.get('name'):
        return jsonify({'message': 'Category name is required'}), 400
    
    conn = get_db_connection()
    try:
        cursor = conn.execute('''
        INSERT INTO categories (name, description)
        VALUES (?, ?)
        ''', (data['name'], data.get('description', '')))
        
        category_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return jsonify({'message': 'Category created successfully', 'category_id': category_id}), 201
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({'message': 'Category name must be unique'}), 400
    except Exception as e:
        conn.close()
        return jsonify({'message': f'Error creating category: {str(e)}'}), 500

@admin_api.route('/categories/<int:category_id>', methods=['PUT'])
@admin_required
def update_category(category_id):
    conn = get_db_connection()
    category = conn.execute('SELECT * FROM categories WHERE id = ?', (category_id,)).fetchone()
    
    if not category:
        conn.close()
        return jsonify({'message': 'Category not found'}), 404
    
    data = request.get_json()
    
    if not data:
        return jsonify({'message': 'No data provided'}), 400
    
    try:
        conn.execute('''
        UPDATE categories
        SET name = ?, description = ?
        WHERE id = ?
        ''', (
            data.get('name', category['name']),
            data.get('description', category['description']),
            category_id
        ))
        
        conn.commit()
        conn.close()
        
        return jsonify({'message': 'Category updated successfully'}), 200
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({'message': 'Category name must be unique'}), 400
    except Exception as e:
        conn.close()
        return jsonify({'message': f'Error updating category: {str(e)}'}), 500

@admin_api.route('/categories/<int:category_id>', methods=['DELETE'])
@admin_required
def delete_category(category_id):
    conn = get_db_connection()
    category = conn.execute('SELECT * FROM categories WHERE id = ?', (category_id,)).fetchone()
    
    if not category:
        conn.close()
        return jsonify({'message': 'Category not found'}), 404
    
    # Check if category is in use
    products = conn.execute('SELECT COUNT(*) as count FROM products WHERE category_id = ?', (category_id,)).fetchone()
    
    if products and products['count'] > 0:
        conn.close()
        return jsonify({'message': 'Cannot delete category that has products'}), 400
    
    try:
        conn.execute('DELETE FROM categories WHERE id = ?', (category_id,))
        conn.commit()
        conn.close()
        
        return jsonify({'message': 'Category deleted successfully'}), 200
    except Exception as e:
        conn.close()
        return jsonify({'message': f'Error deleting category: {str(e)}'}), 500

# Users management endpoints
@admin_api.route('/users', methods=['GET'])
@admin_required
def get_users():
    conn = get_db_connection()
    users = conn.execute('''
    SELECT u.id, u.username, u.email, 
           up.first_name, up.last_name, up.address, up.city, up.state, up.zip, up.phone
    FROM users u
    LEFT JOIN user_profiles up ON u.id = up.user_id
    ORDER BY u.id
    ''').fetchall()
    conn.close()
    
    return jsonify({'users': [row_to_dict(user) for user in users]}), 200

@admin_api.route('/users/<int:user_id>', methods=['GET'])
@admin_required
def get_user(user_id):
    conn = get_db_connection()
    
    user = conn.execute('''
    SELECT u.id, u.username, u.email, 
           up.first_name, up.last_name, up.address, up.city, up.state, up.zip, up.phone
    FROM users u
    LEFT JOIN user_profiles up ON u.id = up.user_id
    WHERE u.id = ?
    ''', (user_id,)).fetchone()
    
    if not user:
        conn.close()
        return jsonify({'message': 'User not found'}), 404
    
    # Get user orders
    orders = conn.execute('''
    SELECT id, order_date, total_amount, status
    FROM orders
    WHERE user_id = ?
    ORDER BY order_date DESC
    ''', (user_id,)).fetchall()
    
    conn.close()
    
    user_data = row_to_dict(user)
    user_data['orders'] = [row_to_dict(order) for order in orders]
    
    return jsonify({'user': user_data}), 200

# Orders management endpoints
@admin_api.route('/orders', methods=['GET'])
@admin_required
def get_orders():
    status_filter = request.args.get('status', '')
    
    conn = get_db_connection()
    
    query = '''
    SELECT o.id, o.order_date, o.total_amount, o.status, 
           u.username as username, u.id as user_id
    FROM orders o
    JOIN users u ON o.user_id = u.id
    '''
    
    params = []
    if status_filter:
        query += ' WHERE o.status = ?'
        params.append(status_filter)
        
    query += ' ORDER BY o.order_date DESC'
    
    orders = conn.execute(query, params).fetchall()
    conn.close()
    
    return jsonify({'orders': [row_to_dict(order) for order in orders]}), 200

@admin_api.route('/orders/<int:order_id>', methods=['GET'])
@admin_required
def get_order(order_id):
    conn = get_db_connection()
    
    order = conn.execute('''
    SELECT o.*, u.username, u.email
    FROM orders o
    JOIN users u ON o.user_id = u.id
    WHERE o.id = ?
    ''', (order_id,)).fetchone()
    
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

@admin_api.route('/orders/<int:order_id>/status', methods=['PUT'])
@admin_required
def update_order_status(order_id):
    data = request.get_json()
    
    if not data or not data.get('status'):
        return jsonify({'message': 'Order status is required'}), 400
    
    conn = get_db_connection()
    
    order = conn.execute('SELECT * FROM orders WHERE id = ?', (order_id,)).fetchone()
    
    if not order:
        conn.close()
        return jsonify({'message': 'Order not found'}), 404
    
    try:
        conn.execute('UPDATE orders SET status = ? WHERE id = ?', (data['status'], order_id))
        conn.commit()
        conn.close()
        
        return jsonify({'message': 'Order status updated successfully'}), 200
    except Exception as e:
        conn.close()
        return jsonify({'message': f'Error updating order status: {str(e)}'}), 500

# Admin users management (super admin only)
@admin_api.route('/admin-users', methods=['GET'])
@admin_required
def get_admin_users():
    # Get the current admin user
    user_id = get_jwt_identity()
    conn = get_db_connection()
    
    current_admin = conn.execute('SELECT * FROM admin_users WHERE id = ?', (user_id,)).fetchone()
    
    # Only super admin can access admin users list
    if not current_admin or not current_admin['is_super_admin']:
        conn.close()
        return jsonify({'message': 'Super admin privileges required'}), 403
    
    admin_users = conn.execute('SELECT id, username, email, is_super_admin FROM admin_users').fetchall()
    conn.close()
    
    return jsonify({'admin_users': [row_to_dict(admin) for admin in admin_users]}), 200

@admin_api.route('/admin-users', methods=['POST'])
@admin_required
def create_admin_user():
    # Get the current admin user
    user_id = get_jwt_identity()
    conn = get_db_connection()
    
    current_admin = conn.execute('SELECT * FROM admin_users WHERE id = ?', (user_id,)).fetchone()
    
    # Only super admin can create admin users
    if not current_admin or not current_admin['is_super_admin']:
        conn.close()
        return jsonify({'message': 'Super admin privileges required'}), 403
    
    data = request.get_json()
    
    if not data or not all(k in data for k in ('username', 'password', 'email')):
        return jsonify({'message': 'Missing required admin information'}), 400
    
    try:
        # Hash the password
        password_hash = check_password_hash(data['password'])
        
        cursor = conn.execute('''
        INSERT INTO admin_users (username, password_hash, email, is_super_admin)
        VALUES (?, ?, ?, ?)
        ''', (
            data['username'],
            password_hash,
            data['email'],
            data.get('is_super_admin', False)
        ))
        
        admin_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return jsonify({'message': 'Admin user created successfully', 'admin_id': admin_id}), 201
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({'message': 'Username already exists'}), 400
    except Exception as e:
        conn.close()
        return jsonify({'message': f'Error creating admin user: {str(e)}'}), 500 