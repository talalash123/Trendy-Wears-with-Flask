import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_pymongo import PyMongo
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from bson.objectid import ObjectId
from config import Config
from functools import wraps
from datetime import datetime

app = Flask(__name__)
app.config.from_object(Config)
app.secret_key = os.environ.get("SECRET_KEY", "dev_key_for_local")

UPLOAD_FOLDER = os.path.join('static', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

mongo = PyMongo(app)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('role') != 'admin':
            flash('Unauthorized access.')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def customer_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('role') != 'customer':
            flash('Unauthorized access.')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        users = mongo.db.users
        email = request.form['email'].lower()
        existing_user = users.find_one({'email': email})
        if existing_user:
            flash('Email already registered on Trendy Wears!')
            return redirect(url_for('register'))

        hashed_password = generate_password_hash(request.form['password'])
        selected_role = request.form.get('role', 'customer')
        users.insert_one({'email': email, 'password': hashed_password, 'role': selected_role, 'purchase_history': []})
        flash('Registration successful! Please login.')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        users = mongo.db.users
        email = request.form['email'].lower()
        password = request.form['password']
        user = users.find_one({'email': email})
        if user and check_password_hash(user['password'], password):
            session['user_id'] = str(user['_id'])
            session['email'] = user['email']
            session['role'] = user['role']
            flash('Logged in successfully!')
            return redirect(url_for('admin_dashboard') if user['role'] == 'admin' else url_for('customer_dashboard'))
        else:
            flash('Invalid email or password!')
            return redirect(url_for('login'))
    return render_template('login.html')

@app.route('/admin')
@admin_required
def admin_dashboard():
    products = list(mongo.db.products.find())
    return render_template('admin_dashboard.html', email=session['email'], products=products)

@app.route('/admin/add_product', methods=['GET', 'POST'])
@admin_required
def add_product():
    if request.method == 'POST':
        product_type = request.form['type']
        name = request.form['name']
        description = request.form['description']
        price = float(request.form['price'])
        image_file = request.files.get('image')

        if not image_file or image_file.filename == '':
            flash('Image is required.')
            return redirect(request.url)

        if image_file and allowed_file(image_file.filename):
            filename = secure_filename(image_file.filename)
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            image_file.save(image_path)
            image_url = url_for('static', filename='uploads/' + filename)
        else:
            flash('Invalid image format! Allowed formats: png, jpg, jpeg, gif.')
            return redirect(request.url)

        mongo.db.products.insert_one({
            'type': product_type,
            'name': name,
            'description': description,
            'price': price,
            'image_url': image_url
        })
        flash('Product added successfully!')
        return redirect(url_for('admin_dashboard'))
    return render_template('add_product.html')

@app.route('/admin/manage_orders')
@admin_required
def manage_orders():
    orders = list(mongo.db.orders.find({'status': {'$ne': 'Delivered'}}))
    for o in orders:
        o['items_list'] = []
        if o.get('type') == 'Buy Now':
            prod = mongo.db.products.find_one({'_id': o['product_id']})
            o['items_list'] = [{'name': prod['name'], 'price': prod['price'], 'qty': 1}]
        elif o.get('type') == 'Cart Order':
            for it in o.get('items', []):
                prod = mongo.db.products.find_one({'_id': ObjectId(it['product_id'])})
                if prod:
                    o['items_list'].append({'name': prod['name'], 'price': prod['price'], 'qty': it['quantity']})
        # no extra fields needed here

    return render_template('admin_manage_orders.html', orders=orders)


@app.route('/deliver_order', methods=['POST'])
@admin_required
def deliver_order():
    order_id = request.form.get('order_id')
    order = mongo.db.orders.find_one({'_id': ObjectId(order_id)})
    if not order:
        flash("Order not found.")
        return redirect(url_for('manage_orders'))

    # mark delivered
    mongo.db.orders.update_one(
        {'_id': ObjectId(order_id)},
        {'$set': {'status': 'Delivered', 'delivered_at': datetime.utcnow()}}
    )

    # add to customer's purchase_history in users collection
    mongo.db.users.update_one(
        {'email': order['customer_email']},
        {'$push': {
            'purchase_history': {
                'items': order.get('items_list', []),
                'total': round(sum(item['price'] * item['qty'] for item in order.get('items_list', [])), 2),
                'name': order.get('name'),
                'address': order.get('address'),
                'status': 'Delivered',
                'date': datetime.utcnow()
            }
        }}
    )

    flash("✔️ Order marked as Delivered.")
    return redirect(url_for('manage_orders'))

@app.route('/admin/edit_product/<product_id>', methods=['GET', 'POST'])
@admin_required
def edit_product(product_id):
    product = mongo.db.products.find_one({'_id': ObjectId(product_id)})
    if not product:
        flash('Product not found.')
        return redirect(url_for('admin_dashboard'))

    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        price = float(request.form['price'])
        updated_data = {'name': name, 'description': description, 'price': price}

        image_file = request.files.get('image')
        if image_file and image_file.filename != '':
            if allowed_file(image_file.filename):
                filename = secure_filename(image_file.filename)
                image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                image_file.save(image_path)
                updated_data['image_url'] = url_for('static', filename='uploads/' + filename)
            else:
                flash('Invalid image format!')
                return redirect(request.url)
        else:
            updated_data['image_url'] = product.get('image_url', '')

        mongo.db.products.update_one({'_id': ObjectId(product_id)}, {'$set': updated_data})
        flash('Product updated successfully!')
        return redirect(url_for('admin_dashboard'))

    return render_template('edit_product.html', product=product)

@app.route('/admin/delete_product/<product_id>')
@admin_required
def delete_product(product_id):
    mongo.db.products.delete_one({'_id': ObjectId(product_id)})
    flash('Product deleted successfully!')
    return redirect(url_for('admin_dashboard'))

@app.route('/customer_dashboard')
@customer_required
def customer_dashboard():
    category = request.args.get('type', 'All')

    if category == "Men":
        products = mongo.db.products.find({'type': 'Men'})
    elif category == "Women":
        products = mongo.db.products.find({'type': 'Women'})
    else:
        products = mongo.db.products.find()

    return render_template('customer_dashboard.html', products=products, selected_type=category if category != 'All' else None, email=session.get('email'))

@app.route('/add_to_cart/<product_id>')
@customer_required
def add_to_cart(product_id):
    user_id = str(session.get('user_id'))

    if not user_id:
        flash('User not logged in.')
        return redirect(url_for('login'))

    product = mongo.db.products.find_one({'_id': ObjectId(product_id)})
    if not product:
        flash('Product not found.')
        return redirect(url_for('customer_dashboard'))

    # Check if the user already has a cart
    cart = mongo.db.carts.find_one({'user_id': user_id})
    new_item = {
        'product_id': str(product['_id']),
        'name': product['name'],
        'price': float(product['price']),  # Ensure price is float
        'quantity': 1
    }

    if cart:
        items = cart.get('items', [])
        found = False

        # Update quantity if item exists
        for item in items:
            if item['product_id'] == new_item['product_id']:
                item['quantity'] += 1
                found = True
                break

        if not found:
            items.append(new_item)

        mongo.db.carts.update_one({'user_id': user_id}, {'$set': {'items': items}})
    else:
        # Insert new cart
        mongo.db.carts.insert_one({
            'user_id': user_id,
            'items': [new_item]
        })

    flash('Product added to cart.')
    return redirect(url_for('view_cart'))

@app.route('/view_cart')
@customer_required
def view_cart():
    user_id = str(session.get('user_id'))  # Ensure it's a string
    cart = mongo.db.carts.find_one({'user_id': user_id})

    cart_items = []
    total_price = 0.0

    if cart and 'items' in cart:
        for item in cart['items']:
            item['subtotal'] = float(item['price']) * int(item['quantity'])
            total_price += item['subtotal']
            cart_items.append(item)

    return render_template('cart.html', cart_items=cart_items, total_price=total_price)


@app.route('/buy_now/<product_id>', methods=['GET', 'POST'])
@customer_required
def buy_now(product_id):
    product = mongo.db.products.find_one({'_id': ObjectId(product_id)})
    if not product:
        flash('Product not found.')
        return redirect(url_for('customer_dashboard'))

    if request.method == 'POST':
        name = request.form['name']
        address = request.form['address']
        if not name or not address:
            flash('Please provide your name and address.')
            return redirect(request.url)

        order = {
            "type": "Buy Now",
            "product_id": product['_id'],
            "product_name": product['name'],
            "price": product['price'],
            "customer_email": session['email'],
            "name": name,
            "address": address,
            "status": "Ordered",
            "date": datetime.utcnow()
        }
        mongo.db.orders.insert_one(order)
        flash('Product ordered successfully!')
        return redirect(url_for('purchase_history'))

    return render_template('buy_now_form.html', product=product)

@app.route('/purchase-history')
@customer_required
def purchase_history():
    user = mongo.db.users.find_one({'email': session['email']})
    orders = user.get('purchase_history', [])
    return render_template('customer_purchase_history.html', orders=orders)

@app.route('/checkout_cart', methods=['GET', 'POST'])
@customer_required
def checkout_cart():
    cart = mongo.db.carts.find_one({'user_id': session['user_id']})
    if not cart or not cart.get('items'):
        flash('Your cart is empty.')
        return redirect(url_for('view_cart'))

    if request.method == 'POST':
        name = request.form['name']
        address = request.form['address']
        if not name or not address:
            flash('Please provide your name and address.')
            return redirect(request.url)

        mongo.db.orders.insert_one({
            'user_id': session['user_id'],
            'items': cart['items'],
            'name': name,
            'address': address,
            'status': 'Ordered',
            'type': 'Cart Order',
            'customer_email': session['email'],
            'date': datetime.utcnow()
        })

        mongo.db.carts.update_one({'user_id': session['user_id']}, {'$set': {'items': []}})

        flash('Cart order placed successfully!')
        return redirect(url_for('purchase_history'))

    return render_template('checkout_cart_form.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.')
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
