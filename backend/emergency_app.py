from flask import Flask, jsonify, request, session
from flask_cors import CORS
import sqlite3
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = 'emergency-secret-key-change-me'
CORS(app, supports_credentials=True)

DB_FILE = 'emergency.db'

def init_db():
    """Initialize database"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # Users table
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Expenses table
    c.execute('''CREATE TABLE IF NOT EXISTS expenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        amount REAL NOT NULL,
        category TEXT NOT NULL,
        description TEXT,
        date TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )''')
    
    # Revenues table
    c.execute('''CREATE TABLE IF NOT EXISTS revenues (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        amount REAL NOT NULL,
        source TEXT NOT NULL,
        description TEXT,
        date TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )''')
    
    # Livestock table
    c.execute('''CREATE TABLE IF NOT EXISTS livestock (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        type TEXT NOT NULL,
        breed TEXT,
        quantity INTEGER NOT NULL,
        purchase_date TEXT,
        purchase_price REAL,
        notes TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )''')
    
    conn.commit()
    conn.close()
    print("✓ Emergency database initialized")

init_db()

# Helper functions
def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def login_required(f):
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'success': False, 'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper

# Routes
@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'healthy',
        'version': 'emergency',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/auth/register', methods=['POST'])
def register():
    try:
        data = request.json
        conn = get_db()
        c = conn.cursor()
        
        # Check if user exists
        c.execute('SELECT id FROM users WHERE username = ?', (data['username'],))
        if c.fetchone():
            conn.close()
            return jsonify({'success': False, 'error': 'Username already exists'}), 400
        
        # Create user
        c.execute(
            'INSERT INTO users (username, password, email) VALUES (?, ?, ?)',
            (data['username'], data['password'], data['email'])
        )
        user_id = c.lastrowid
        conn.commit()
        conn.close()
        
        # Auto-login
        session['user_id'] = user_id
        
        return jsonify({
            'success': True,
            'user': {
                'id': user_id,
                'username': data['username'],
                'email': data['email']
            }
        }), 201
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/auth/login', methods=['POST'])
def login():
    try:
        data = request.json
        conn = get_db()
        c = conn.cursor()
        
        c.execute(
            'SELECT id, username, email FROM users WHERE username = ? AND password = ?',
            (data['username'], data['password'])
        )
        user = c.fetchone()
        conn.close()
        
        if not user:
            return jsonify({'success': False, 'error': 'Invalid credentials'}), 401
        
        session['user_id'] = user['id']
        
        return jsonify({
            'success': True,
            'user': {
                'id': user['id'],
                'username': user['username'],
                'email': user['email']
            }
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/auth/logout', methods=['POST'])
@login_required
def logout():
    session.pop('user_id', None)
    return jsonify({'success': True, 'message': 'Logged out'}), 200

@app.route('/api/auth/me', methods=['GET'])
@login_required
def get_current_user():
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT id, username, email FROM users WHERE id = ?', (session['user_id'],))
    user = c.fetchone()
    conn.close()
    
    if not user:
        return jsonify({'success': False, 'error': 'User not found'}), 404
    
    return jsonify({
        'success': True,
        'user': {
            'id': user['id'],
            'username': user['username'],
            'email': user['email']
        }
    }), 200

@app.route('/api/expenses', methods=['GET'])
@login_required
def get_expenses():
    conn = get_db()
    c = conn.cursor()
    c.execute(
        'SELECT * FROM expenses WHERE user_id = ? ORDER BY date DESC',
        (session['user_id'],)
    )
    expenses = [dict(row) for row in c.fetchall()]
    conn.close()
    
    return jsonify({'success': True, 'expenses': expenses}), 200

@app.route('/api/expenses', methods=['POST'])
@login_required
def create_expense():
    try:
        data = request.json
        conn = get_db()
        c = conn.cursor()
        
        c.execute(
            'INSERT INTO expenses (user_id, amount, category, description, date) VALUES (?, ?, ?, ?, ?)',
            (session['user_id'], data['amount'], data['category'], 
             data.get('description', ''), data['date'])
        )
        expense_id = c.lastrowid
        conn.commit()
        
        # Get the created expense
        c.execute('SELECT * FROM expenses WHERE id = ?', (expense_id,))
        expense = dict(c.fetchone())
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Expense created',
            'expense': expense
        }), 201
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/expenses/<int:expense_id>', methods=['DELETE'])
@login_required
def delete_expense(expense_id):
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute(
            'DELETE FROM expenses WHERE id = ? AND user_id = ?',
            (expense_id, session['user_id'])
        )
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Expense deleted'}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/revenues', methods=['GET'])
@login_required
def get_revenues():
    conn = get_db()
    c = conn.cursor()
    c.execute(
        'SELECT * FROM revenues WHERE user_id = ? ORDER BY date DESC',
        (session['user_id'],)
    )
    revenues = [dict(row) for row in c.fetchall()]
    conn.close()
    
    return jsonify({'success': True, 'revenues': revenues}), 200

@app.route('/api/revenues', methods=['POST'])
@login_required
def create_revenue():
    try:
        data = request.json
        conn = get_db()
        c = conn.cursor()
        
        c.execute(
            'INSERT INTO revenues (user_id, amount, source, description, date) VALUES (?, ?, ?, ?, ?)',
            (session['user_id'], data['amount'], data['source'],
             data.get('description', ''), data['date'])
        )
        revenue_id = c.lastrowid
        conn.commit()
        
        c.execute('SELECT * FROM revenues WHERE id = ?', (revenue_id,))
        revenue = dict(c.fetchone())
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Revenue created',
            'revenue': revenue
        }), 201
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/livestock', methods=['GET'])
@login_required
def get_livestock():
    conn = get_db()
    c = conn.cursor()
    c.execute(
        'SELECT * FROM livestock WHERE user_id = ? ORDER BY created_at DESC',
        (session['user_id'],)
    )
    livestock = [dict(row) for row in c.fetchall()]
    conn.close()
    
    return jsonify({'success': True, 'livestock': livestock}), 200

@app.route('/api/livestock', methods=['POST'])
@login_required
def create_livestock():
    try:
        data = request.json
        conn = get_db()
        c = conn.cursor()
        
        c.execute(
            'INSERT INTO livestock (user_id, type, breed, quantity, purchase_date, purchase_price, notes) VALUES (?, ?, ?, ?, ?, ?, ?)',
            (session['user_id'], data['type'], data.get('breed'), data['quantity'],
             data.get('purchase_date'), data.get('purchase_price'), data.get('notes'))
        )
        livestock_id = c.lastrowid
        conn.commit()
        
        c.execute('SELECT * FROM livestock WHERE id = ?', (livestock_id,))
        livestock = dict(c.fetchone())
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Livestock created',
            'livestock': livestock
        }), 201
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/budget', methods=['GET'])
@login_required
def get_budget():
    return jsonify({
        'success': True,
        'budget': {
            'total_budget': 0,
            'remaining_budget': 0,
            'period': 'monthly'
        }
    }), 200

@app.route('/api/analytics/summary', methods=['GET'])
@login_required
def get_analytics():
    conn = get_db()
    c = conn.cursor()
    
    # Get total expenses this month
    c.execute(
        'SELECT SUM(amount) as total FROM expenses WHERE user_id = ? AND date >= date("now", "start of month")',
        (session['user_id'],)
    )
    result = c.fetchone()
    total_expenses = result['total'] or 0
    
    # Get livestock count
    c.execute(
        'SELECT SUM(quantity) as total FROM livestock WHERE user_id = ?',
        (session['user_id'],)
    )
    result = c.fetchone()
    livestock_count = result['total'] or 0
    
    conn.close()
    
    return jsonify({
        'success': True,
        'summary': {
            'total_expenses_month': total_expenses,
            'livestock_count': livestock_count,
            'total_livestock_value': 0,
            'budget': None
        }
    }), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002, debug=True)
