from flask import Flask, jsonify, request, session
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS
from models import db, User, Expense, Revenue, Livestock, Budget
from datetime import datetime, timedelta
import os
import requests
from dotenv import load_dotenv
import joblib
import numpy as np
import pandas as pd

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Configuration - FIXED
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-CHANGE-IN-PRODUCTION')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///farm_tracker.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_HTTPONLY'] = True

# CORS Configuration - ADDED
CORS(app, resources={
    r"/api/*": {
        "origins": ["http://localhost:8000", "http://127.0.0.1:8000", "http://localhost:5500", "http://127.0.0.1:5500"],
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"],
        "supports_credentials": True
    }
})

# N8N webhook URL
N8N_WEBHOOK_URL = os.getenv('N8N_WEBHOOK_URL', 'https://tube.app.n8n.cloud/webhook/expense-intake')

# Initialize extensions
db.init_app(app)
migrate = Migrate(app, db)

# Load ML model
MODEL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'models')
try:
    model = joblib.load(os.path.join(MODEL_DIR, "expense_model.pkl"))
    features = joblib.load(os.path.join(MODEL_DIR, "feature_names.pkl"))
    metadata = joblib.load(os.path.join(MODEL_DIR, "model_metadata.pkl"))
    print(f" Model loaded: {metadata['best_model']}")
    print(f" Test MAE: ${metadata['test_mae']:.2f}")
except Exception as e:
    print(f" ML models not loaded: {e}")
    print(" Prediction endpoint will not be available")
    model = None
    metadata = None

# Authentication decorator
def login_required(f):
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'success': False, 'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper

# Routes

@app.route('/api/auth/register', methods=['POST'])
def register():
    """Register a new user"""
    try:
        data = request.get_json()

        if not data or not all(k in data for k in ['username', 'email', 'password']):
            return jsonify({'success': False, 'error': 'Missing required fields'}), 400

        # Check if user already exists
        if User.query.filter_by(username=data['username']).first():
            return jsonify({'success': False, 'error': 'Username already exists'}), 400

        if User.query.filter_by(email=data['email']).first():
            return jsonify({'success': False, 'error': 'Email already exists'}), 400

        # Create new user
        user = User(username=data['username'], email=data['email'])
        user.set_password(data['password'])

        db.session.add(user)
        db.session.commit()

        # Auto-login after registration
        session['user_id'] = user.id

        return jsonify({
            'success': True,
            'message': 'User registered successfully',
            'user': user.to_dict()
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/auth/login', methods=['POST'])
def login():
    """Login user"""
    try:
        data = request.get_json()

        if not data or not all(k in data for k in ['username', 'password']):
            return jsonify({'success': False, 'error': 'Missing credentials'}), 400

        user = User.query.filter_by(username=data['username']).first()

        if not user or not user.check_password(data['password']):
            return jsonify({'success': False, 'error': 'Invalid credentials'}), 401

        session['user_id'] = user.id

        return jsonify({
            'success': True,
            'message': 'Login successful',
            'user': user.to_dict()
        }), 200

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/auth/logout', methods=['POST'])
@login_required
def logout():
    """Logout user"""
    session.pop('user_id', None)
    return jsonify({'success': True, 'message': 'Logout successful'}), 200

@app.route('/api/auth/me', methods=['GET'])
@login_required
def get_current_user():
    """Get current user info"""
    user = User.query.get(session['user_id'])
    if not user:
        return jsonify({'success': False, 'error': 'User not found'}), 404

    return jsonify({
        'success': True,
        'user': user.to_dict()
    }), 200

# Expense routes
@app.route('/api/expenses', methods=['GET'])
@login_required
def get_expenses():
    """Get all expenses for current user"""
    expenses = Expense.query.filter_by(user_id=session['user_id']).order_by(Expense.date.desc()).all()
    return jsonify({
        'success': True,
        'expenses': [expense.to_dict() for expense in expenses]
    }), 200

@app.route('/api/expenses', methods=['POST'])
@login_required
def create_expense():
    """Create new expense"""
    try:
        data = request.get_json()

        required_fields = ['amount', 'category', 'date']
        if not all(k in data for k in required_fields):
            return jsonify({'success': False, 'error': 'Missing required fields'}), 400

        expense = Expense(
            amount=float(data['amount']),
            category=data['category'],
            description=data.get('description', ''),
            date=datetime.fromisoformat(data['date']),
            user_id=session['user_id']
        )

        db.session.add(expense)
        db.session.commit()

        # Send data to N8N webhook (async, don't fail if it errors)
        try:
            n8n_payload = {
                'type': 'expense',
                'user_id': session['user_id'],
                'amount': expense.amount,
                'category': expense.category,
                'description': expense.description,
                'date': expense.date.isoformat(),
                'timestamp': datetime.now().isoformat()
            }
            requests.post(N8N_WEBHOOK_URL, json=n8n_payload, timeout=5)
        except Exception as e:
            print(f"N8N webhook failed: {e}")  # Log but don't fail the expense creation

        return jsonify({
            'success': True,
            'message': 'Expense created successfully',
            'expense': expense.to_dict()
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/expenses/<int:expense_id>', methods=['PUT'])
@login_required
def update_expense(expense_id):
    """Update expense"""
    try:
        expense = Expense.query.filter_by(id=expense_id, user_id=session['user_id']).first()
        if not expense:
            return jsonify({'success': False, 'error': 'Expense not found'}), 404

        data = request.get_json()

        if 'amount' in data:
            expense.amount = float(data['amount'])
        if 'category' in data:
            expense.category = data['category']
        if 'description' in data:
            expense.description = data['description']
        if 'date' in data:
            expense.date = datetime.fromisoformat(data['date'])

        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Expense updated successfully',
            'expense': expense.to_dict()
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/expenses/<int:expense_id>', methods=['DELETE'])
@login_required
def delete_expense(expense_id):
    """Delete expense"""
    try:
        expense = Expense.query.filter_by(id=expense_id, user_id=session['user_id']).first()
        if not expense:
            return jsonify({'success': False, 'error': 'Expense not found'}), 404

        db.session.delete(expense)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Expense deleted successfully'
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

# Revenue routes
@app.route('/api/revenues', methods=['GET'])
@login_required
def get_revenues():
    """Get all revenues for current user"""
    revenues = Revenue.query.filter_by(user_id=session['user_id']).order_by(Revenue.date.desc()).all()
    return jsonify({
        'success': True,
        'revenues': [revenue.to_dict() for revenue in revenues]
    }), 200

@app.route('/api/revenues', methods=['POST'])
@login_required
def create_revenue():
    """Create new revenue"""
    try:
        data = request.get_json()

        required_fields = ['amount', 'source', 'date']
        if not all(k in data for k in required_fields):
            return jsonify({'success': False, 'error': 'Missing required fields'}), 400

        revenue = Revenue(
            amount=float(data['amount']),
            source=data['source'],
            description=data.get('description', ''),
            date=datetime.fromisoformat(data['date']),
            user_id=session['user_id']
        )

        db.session.add(revenue)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Revenue created successfully',
            'revenue': revenue.to_dict()
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/revenues/<int:revenue_id>', methods=['PUT'])
@login_required
def update_revenue(revenue_id):
    """Update revenue"""
    try:
        revenue = Revenue.query.filter_by(id=revenue_id, user_id=session['user_id']).first()
        if not revenue:
            return jsonify({'success': False, 'error': 'Revenue not found'}), 404

        data = request.get_json()

        if 'amount' in data:
            revenue.amount = float(data['amount'])
        if 'source' in data:
            revenue.source = data['source']
        if 'description' in data:
            revenue.description = data['description']
        if 'date' in data:
            revenue.date = datetime.fromisoformat(data['date'])

        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Revenue updated successfully',
            'revenue': revenue.to_dict()
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/revenues/<int:revenue_id>', methods=['DELETE'])
@login_required
def delete_revenue(revenue_id):
    """Delete revenue"""
    try:
        revenue = Revenue.query.filter_by(id=revenue_id, user_id=session['user_id']).first()
        if not revenue:
            return jsonify({'success': False, 'error': 'Revenue not found'}), 404

        db.session.delete(revenue)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Revenue deleted successfully'
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

# Livestock routes
@app.route('/api/livestock', methods=['GET'])
@login_required
def get_livestock():
    """Get all livestock for current user"""
    livestock = Livestock.query.filter_by(user_id=session['user_id']).order_by(Livestock.created_at.desc()).all()
    return jsonify({
        'success': True,
        'livestock': [item.to_dict() for item in livestock]
    }), 200

@app.route('/api/livestock', methods=['POST'])
@login_required
def create_livestock():
    """Create new livestock entry"""
    try:
        data = request.get_json()

        required_fields = ['type', 'quantity']
        if not all(k in data for k in required_fields):
            return jsonify({'success': False, 'error': 'Missing required fields'}), 400

        livestock = Livestock(
            type=data['type'],
            breed=data.get('breed'),
            quantity=int(data['quantity']),
            age_months=int(data['age_months']) if data.get('age_months') else None,
            weight_kg=float(data['weight_kg']) if data.get('weight_kg') else None,
            purchase_date=datetime.fromisoformat(data['purchase_date']) if data.get('purchase_date') else None,
            purchase_price=float(data['purchase_price']) if data.get('purchase_price') else None,
            notes=data.get('notes'),
            user_id=session['user_id']
        )

        db.session.add(livestock)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Livestock created successfully',
            'livestock': livestock.to_dict()
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

# Budget routes
@app.route('/api/budget', methods=['GET'])
@login_required
def get_budget():
    """Get current budget for user"""
    budget = Budget.query.filter_by(user_id=session['user_id']).order_by(Budget.created_at.desc()).first()
    if not budget:
        return jsonify({
            'success': True,
            'budget': None
        }), 200

    return jsonify({
        'success': True,
        'budget': budget.to_dict()
    }), 200

@app.route('/api/budget', methods=['POST'])
@login_required
def create_budget():
    """Create or update budget"""
    try:
        data = request.get_json()

        if not data or 'total_budget' not in data:
            return jsonify({'success': False, 'error': 'Total budget required'}), 400

        # Delete existing budget
        Budget.query.filter_by(user_id=session['user_id']).delete()

        # Create new budget
        start_date = datetime.now().date()
        if data.get('period') == 'yearly':
            end_date = start_date.replace(year=start_date.year + 1)
        else:
            # Monthly - next month
            if start_date.month == 12:
                end_date = start_date.replace(year=start_date.year + 1, month=1)
            else:
                end_date = start_date.replace(month=start_date.month + 1)

        budget = Budget(
            total_budget=float(data['total_budget']),
            remaining_budget=float(data['total_budget']),
            period=data.get('period', 'monthly'),
            start_date=start_date,
            end_date=end_date,
            user_id=session['user_id']
        )

        db.session.add(budget)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Budget created successfully',
            'budget': budget.to_dict()
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

# Analytics routes
@app.route('/api/analytics/summary', methods=['GET'])
@login_required
def get_analytics_summary():
    """Get analytics summary"""
    try:
        user_id = session['user_id']

        # Get current month expenses
        current_month = datetime.now().replace(day=1)
        next_month = (current_month + timedelta(days=32)).replace(day=1)

        monthly_expenses = Expense.query.filter(
            Expense.user_id == user_id,
            Expense.date >= current_month,
            Expense.date < next_month
        ).all()

        total_expenses = sum(expense.amount for expense in monthly_expenses)

        # Get total livestock value
        livestock_items = Livestock.query.filter_by(user_id=user_id).all()
        total_livestock_value = sum(
            (item.purchase_price or 0) * item.quantity
            for item in livestock_items
        )

        # Get budget info
        budget = Budget.query.filter_by(user_id=user_id).first()
        budget_info = budget.to_dict() if budget else None

        return jsonify({
            'success': True,
            'summary': {
                'total_expenses_month': total_expenses,
                'total_livestock_value': total_livestock_value,
                'livestock_count': sum(item.quantity for item in livestock_items),
                'budget': budget_info
            }
        }), 200

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ML Prediction routes
@app.route('/api/predict', methods=['POST'])
@login_required
def predict_expenses():
    """Predict monthly expenses using ML model"""
    if not model:
        return jsonify({
            'success': False,
            'error': 'ML model not loaded'
        }), 500

    try:
        data = request.get_json()

        # Validate required fields
        required_fields = ['year', 'month', 'total_lag1', 'total_lag3',
                          'total_lag12', 'rolling_avg_3', 'diff_1', 'rolling_avg_6']
        missing_fields = [field for field in required_fields if field not in data]

        if missing_fields:
            return jsonify({
                'success': False,
                'error': f'Missing required fields: {", ".join(missing_fields)}'
            }), 400

        # Build features
        month = data['month']
        features_dict = {
            'Year': data['year'],
            'Month': month,
            'Month_sin': np.sin(2 * np.pi * month / 12.0),
            'Month_cos': np.cos(2 * np.pi * month / 12.0),
            'Total_Lag1': data['total_lag1'],
            'Total_Lag3': data['total_lag3'],
            'Total_Lag12': data['total_lag12'],
            'Rolling_Avg_3': data['rolling_avg_3'],
            'Diff_1': data['diff_1'],
            'Rolling_Avg_6': data['rolling_avg_6'],
        }

        # Create DataFrame and predict
        X = pd.DataFrame([features_dict])[features]
        prediction = model.predict(X)[0]
        mae = metadata['test_mae']

        return jsonify({
            'success': True,
            'prediction': {
                'value': round(float(prediction), 2),
                'lower_bound': round(float(prediction - mae), 2),
                'upper_bound': round(float(prediction + mae), 2),
                'currency': 'USD'
            },
            'confidence': {
                'expected_mae': round(float(mae), 2),
                'interval': f"${prediction - mae:,.2f} - ${prediction + mae:,.2f}"
            }
        }), 200

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/health', methods=['GET'])
def health():
    """Health check"""
    return jsonify({
        'status': 'healthy',
        'database': 'connected' if db.engine else 'disconnected',
        'ml_model': 'loaded' if model else 'not loaded',
        'timestamp': datetime.now().isoformat()
    }), 200

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=5001, debug=True)