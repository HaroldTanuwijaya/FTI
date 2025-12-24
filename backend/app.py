from flask import Flask, render_template, jsonify, request, session, redirect, url_for, make_response
from flask_pymongo import PyMongo
from flask_caching import Cache
from datetime import datetime, timedelta
import os
import bcrypt
import jwt
import csv
import io
import re
from functools import wraps
from collections import Counter
from models import User, Transaction, Budget, FTIScore, Goal, Alert, CategoryRule

app = Flask(__name__, 
            static_folder='../frontend/static',
            template_folder='../frontend/templates')
app.secret_key = os.getenv("SECRET_KEY", "your-secret-key-here")

# MongoDB Configuration
app.config["MONGO_URI"] = os.getenv("MONGO_URI", "mongodb://localhost:27017/fti_db")
mongo = PyMongo(app)

# Cache Configuration
app.config['CACHE_TYPE'] = 'simple'
app.config['CACHE_DEFAULT_TIMEOUT'] = 300  # 5 minutes
cache = Cache(app)

# Default categories
DEFAULT_CATEGORIES = [
    "Food & Dining", "Transportation", "Shopping", "Entertainment", 
    "Bills & Utilities", "Healthcare", "Education", "Travel", 
    "Income", "Investment", "Other"
]

# Auto-categorization keywords
CATEGORY_KEYWORDS = {
    "Food & Dining": ["restaurant", "cafe", "coffee", "food", "pizza", "burger", "lunch", "dinner", "breakfast", "grocery", "supermarket"],
    "Transportation": ["uber", "lyft", "taxi", "gas", "fuel", "parking", "metro", "bus", "train", "airline"],
    "Shopping": ["amazon", "store", "shop", "mall", "retail", "clothing", "electronics"],
    "Entertainment": ["movie", "cinema", "netflix", "spotify", "game", "concert", "theater"],
    "Bills & Utilities": ["electric", "water", "internet", "phone", "bill", "utility", "rent", "mortgage"],
    "Healthcare": ["hospital", "doctor", "pharmacy", "medical", "health", "clinic", "dental"],
    "Education": ["school", "university", "course", "book", "tuition", "education"],
    "Travel": ["hotel", "airbnb", "flight", "booking", "travel", "vacation"],
    "Income": ["salary", "paycheck", "income", "payment received", "deposit"],
    "Investment": ["stock", "crypto", "investment", "dividend", "interest"]
}

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'message': 'Token is missing'}), 401
        try:
            token = token.split(' ')[1]  # Remove 'Bearer ' prefix
            data = jwt.decode(token, app.secret_key, algorithms=['HS256'])
            current_user_id = data['user_id']
        except:
            return jsonify({'message': 'Token is invalid'}), 401
        return f(current_user_id, *args, **kwargs)
    return decorated

@app.route('/')
def dashboard():
    return render_template('dashboard.html')

@app.route('/login')
def login_page():
    return render_template('login.html')

@app.route('/register')
def register_page():
    return render_template('register.html')

@app.route('/goals')
def goals_page():
    return render_template('goals.html')

@app.route('/alerts')
def alerts_page():
    return render_template('alerts.html')

@app.route('/api/auth/register', methods=['POST'])
def register():
    try:
        data = request.get_json()
        
        # Check if user exists
        if mongo.db.users.find_one({"email": data['email']}):
            return jsonify({"error": "User already exists"}), 400
        
        # Hash password
        password_hash = bcrypt.hashpw(data['password'].encode('utf-8'), bcrypt.gensalt())
        
        # Create user
        user_data = User.create_user(data['email'], password_hash, data['name'])
        result = mongo.db.users.insert_one(user_data)
        
        # Generate token
        token = jwt.encode({
            'user_id': str(result.inserted_id),
            'exp': datetime.utcnow() + timedelta(days=30)
        }, app.secret_key, algorithm='HS256')
        
        return jsonify({"token": token})
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/auth/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        
        # Find user
        user = mongo.db.users.find_one({"email": data['email']})
        if not user:
            return jsonify({"error": "Invalid credentials"}), 401
        
        # Check password
        if not bcrypt.checkpw(data['password'].encode('utf-8'), user['password_hash']):
            return jsonify({"error": "Invalid credentials"}), 401
        
        # Generate token
        token = jwt.encode({
            'user_id': str(user['_id']),
            'exp': datetime.utcnow() + timedelta(days=30)
        }, app.secret_key, algorithm='HS256')
        
        return jsonify({"token": token})
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/dashboard')
@token_required
@cache.memoize(timeout=60)  # Cache for 1 minute
def api_dashboard(current_user_id):
    try:
        current_month = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        next_month = (current_month + timedelta(days=32)).replace(day=1)
        
        dashboard_data = {
            "fti_score": calculate_fti_score(current_user_id),
            "monthly_income": get_monthly_income(current_user_id, current_month, next_month),
            "monthly_expenses": get_monthly_expenses(current_user_id, current_month, next_month),
            "net_flow": 0,
            "budget_used": get_budget_usage(current_user_id, current_month, next_month),
            "recent_transactions": get_recent_transactions(current_user_id),
            "total_transactions": get_transaction_count(current_user_id, current_month, next_month),
            "avg_daily_spend": get_avg_daily_spend(current_user_id, current_month, next_month),
            "top_category": get_top_category(current_user_id, current_month, next_month),
            "recurring_count": detect_recurring_transactions(current_user_id)
        }
        
        dashboard_data["net_flow"] = dashboard_data["monthly_income"] - dashboard_data["monthly_expenses"]
        
        return jsonify(dashboard_data)
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/transactions', methods=['POST'])
@token_required
def add_transaction(current_user_id):
    try:
        data = request.get_json()
        
        # Auto-categorize if category not provided or is "Other"
        category = data.get('category', 'Other')
        if category == 'Other' or not category:
            category = auto_categorize_transaction(data['description'])
        
        transaction_data = Transaction.create_transaction(
            current_user_id,
            data['amount'],
            data['type'],
            data['description'],
            category
        )
        
        result = mongo.db.transactions.insert_one(transaction_data)
        
        # Clear cache for this user
        cache.delete_memoized(api_dashboard, current_user_id)
        cache.delete_memoized(get_goals, current_user_id)
        
        # Check for alerts
        check_transaction_alerts(current_user_id, transaction_data)
        
        return jsonify({"success": True, "category": category})
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/budget', methods=['POST'])
@token_required
def set_budget(current_user_id):
    try:
        data = request.get_json()
        
        # Update or create budget for current month
        budget_data = Budget.create_budget(
            current_user_id,
            data['month'],
            data['total_amount']
        )
        
        mongo.db.budgets.replace_one(
            {"user_id": budget_data["user_id"], "month": data['month']},
            budget_data,
            upsert=True
        )
        
        # Clear cache
        cache.delete_memoized(api_dashboard, current_user_id)
        
        return jsonify({"success": True})
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/categories')
@token_required
@cache.cached(timeout=3600)  # Cache for 1 hour (static data)
def get_categories(current_user_id):
    return jsonify(DEFAULT_CATEGORIES)

@app.route('/api/export/csv')
def export_csv():
    try:
        # Get token from query parameter for file download
        token = request.args.get('token')
        if not token:
            return jsonify({'message': 'Token is missing'}), 401
        
        try:
            data = jwt.decode(token, app.secret_key, algorithms=['HS256'])
            current_user_id = data['user_id']
        except:
            return jsonify({'message': 'Token is invalid'}), 401
        
        # Get all transactions for user
        from bson import ObjectId
        transactions = list(mongo.db.transactions.find({"user_id": ObjectId(current_user_id)})
                          .sort("date", -1))
        
        # Create CSV
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow(['Date', 'Type', 'Description', 'Category', 'Amount'])
        
        # Write transactions
        for transaction in transactions:
            writer.writerow([
                transaction.get('date', '').strftime('%Y-%m-%d') if transaction.get('date') else '',
                transaction.get('type', ''),
                transaction.get('description', ''),
                transaction.get('category', ''),
                transaction.get('amount', 0)
            ])
        
        # Create response
        response = make_response(output.getvalue())
        response.headers['Content-Type'] = 'text/csv'
        response.headers['Content-Disposition'] = f'attachment; filename=fti_transactions_{datetime.now().strftime("%Y-%m")}.csv'
        
        return response
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/reports/monthly')
@token_required
def monthly_report(current_user_id):
    try:
        # Generate simple monthly report (placeholder for PDF generation)
        current_month = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        next_month = (current_month + timedelta(days=32)).replace(day=1)
        
        report_data = {
            "month": current_month.strftime("%B %Y"),
            "fti_score": calculate_fti_score(current_user_id),
            "total_income": get_monthly_income(current_user_id, current_month, next_month),
            "total_expenses": get_monthly_expenses(current_user_id, current_month, next_month),
            "transaction_count": get_transaction_count(current_user_id, current_month, next_month),
            "top_categories": get_category_breakdown(current_user_id, current_month, next_month)
        }
        
        # For MVP, return JSON data (implement PDF generation in V1)
        return jsonify(report_data)
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Goals API
@app.route('/api/goals', methods=['GET'])
@token_required
@cache.memoize(timeout=120)  # Cache for 2 minutes
def get_goals(current_user_id):
    try:
        from bson import ObjectId
        goals = list(mongo.db.goals.find({"user_id": ObjectId(current_user_id)})
                    .sort("created_at", -1))
        
        formatted_goals = []
        for goal in goals:
            formatted_goals.append({
                "_id": str(goal["_id"]),
                "name": goal.get("name", ""),
                "target_amount": goal.get("target_amount", 0),
                "current_amount": goal.get("current_amount", 0),
                "target_date": goal.get("target_date", ""),
                "status": goal.get("status", "active")
            })
        
        return jsonify({"goals": formatted_goals})
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/goals', methods=['POST'])
@token_required
def create_goal(current_user_id):
    try:
        data = request.get_json()
        
        goal_data = Goal.create_goal(
            current_user_id,
            data['name'],
            data['target_amount'],
            data.get('current_amount', 0),
            data['target_date']
        )
        
        mongo.db.goals.insert_one(goal_data)
        
        # Clear cache
        cache.delete_memoized(get_goals, current_user_id)
        cache.delete_memoized(api_dashboard, current_user_id)
        
        return jsonify({"success": True})
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/goals/<goal_id>', methods=['DELETE'])
@token_required
def delete_goal(current_user_id, goal_id):
    try:
        from bson import ObjectId
        mongo.db.goals.delete_one({
            "_id": ObjectId(goal_id),
            "user_id": ObjectId(current_user_id)
        })
        
        # Clear cache
        cache.delete_memoized(get_goals, current_user_id)
        cache.delete_memoized(api_dashboard, current_user_id)
        
        return jsonify({"success": True})
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Alerts API
@app.route('/api/alerts', methods=['GET'])
@token_required
def get_alerts(current_user_id):
    try:
        from bson import ObjectId
        alerts = list(mongo.db.alerts.find({"user_id": ObjectId(current_user_id)})
                     .sort("created_at", -1)
                     .limit(20))
        
        formatted_alerts = []
        for alert in alerts:
            formatted_alerts.append({
                "title": alert.get("title", ""),
                "message": alert.get("message", ""),
                "type": alert.get("type", "info"),
                "created_at": alert.get("created_at", datetime.now()).isoformat()
            })
        
        return jsonify({"alerts": formatted_alerts})
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/alerts/settings', methods=['GET'])
@token_required
def get_alert_settings(current_user_id):
    try:
        from bson import ObjectId
        settings = mongo.db.alert_settings.find_one({"user_id": ObjectId(current_user_id)})
        
        if not settings:
            return jsonify({
                "budget_alert": True,
                "large_transaction_alert": True,
                "goal_alert": True,
                "recurring_alert": True
            })
        
        return jsonify({
            "budget_alert": settings.get("budget_alert", True),
            "large_transaction_alert": settings.get("large_transaction_alert", True),
            "goal_alert": settings.get("goal_alert", True),
            "recurring_alert": settings.get("recurring_alert", True)
        })
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/alerts/settings', methods=['POST'])
@token_required
def save_alert_settings(current_user_id):
    try:
        from bson import ObjectId
        data = request.get_json()
        
        mongo.db.alert_settings.replace_one(
            {"user_id": ObjectId(current_user_id)},
            {
                "user_id": ObjectId(current_user_id),
                "budget_alert": data.get("budget_alert", True),
                "large_transaction_alert": data.get("large_transaction_alert", True),
                "goal_alert": data.get("goal_alert", True),
                "recurring_alert": data.get("recurring_alert", True),
                "updated_at": datetime.utcnow()
            },
            upsert=True
        )
        
        return jsonify({"success": True})
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def calculate_fti_score(user_id):
    try:
        from bson import ObjectId
        current_month = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        next_month = (current_month + timedelta(days=32)).replace(day=1)
        
        # Get financial data
        income = get_monthly_income(user_id, current_month, next_month)
        expenses = get_monthly_expenses(user_id, current_month, next_month)
        
        # Cash Flow Health (25%) - Income vs Expenses
        cash_flow_ratio = (income - expenses) / income if income > 0 else 0
        cash_flow_score = min(100, max(0, cash_flow_ratio * 100))
        
        # Spending Control (20%) - Budget adherence
        budget_usage = get_budget_usage(user_id, current_month, next_month)
        spending_control_score = max(0, 100 - budget_usage) if budget_usage > 0 else 70
        
        # Savings Discipline (20%) - Savings rate
        savings_rate = ((income - expenses) / income * 100) if income > 0 else 0
        savings_discipline_score = min(100, max(0, savings_rate * 5))  # 20% savings = 100 score
        
        # Stability & Consistency (15%) - Transaction regularity
        transaction_count = get_transaction_count(user_id, current_month, next_month)
        stability_score = min(100, transaction_count * 5)  # More transactions = more tracking
        
        # Debt & Obligations (10%) - Placeholder for future debt tracking
        debt_score = 90
        
        # Goal Progress (10%) - Average goal completion
        goals = list(mongo.db.goals.find({"user_id": ObjectId(user_id), "status": "active"}))
        if goals:
            total_progress = sum((g.get("current_amount", 0) / g.get("target_amount", 1)) * 100 for g in goals)
            goal_progress_score = min(100, total_progress / len(goals))
        else:
            goal_progress_score = 60  # Default if no goals
        
        # Weighted calculation
        fti_score = (
            cash_flow_score * 0.25 +
            spending_control_score * 0.20 +
            savings_discipline_score * 0.20 +
            stability_score * 0.15 +
            debt_score * 0.10 +
            goal_progress_score * 0.10
        )
        
        return round(fti_score)
    
    except Exception as e:
        print(f"FTI Score calculation error: {e}")
        return 0

def get_monthly_income(user_id, start_date, end_date):
    try:
        from bson import ObjectId
        pipeline = [
            {
                "$match": {
                    "user_id": ObjectId(user_id),
                    "type": "income",
                    "date": {"$gte": start_date, "$lt": end_date}
                }
            },
            {
                "$group": {
                    "_id": None,
                    "total": {"$sum": "$amount"}
                }
            }
        ]
        
        result = list(mongo.db.transactions.aggregate(pipeline, allowDiskUse=True))
        return result[0]["total"] if result else 0
    
    except Exception:
        return 0

def get_monthly_expenses(user_id, start_date, end_date):
    try:
        from bson import ObjectId
        pipeline = [
            {
                "$match": {
                    "user_id": ObjectId(user_id),
                    "type": "expense",
                    "date": {"$gte": start_date, "$lt": end_date}
                }
            },
            {
                "$group": {
                    "_id": None,
                    "total": {"$sum": "$amount"}
                }
            }
        ]
        
        result = list(mongo.db.transactions.aggregate(pipeline, allowDiskUse=True))
        return result[0]["total"] if result else 0
    
    except Exception:
        return 0

def get_budget_usage(user_id, start_date, end_date):
    try:
        from bson import ObjectId
        budget = mongo.db.budgets.find_one({
            "user_id": ObjectId(user_id), 
            "month": start_date.strftime("%Y-%m")
        })
        
        if not budget:
            return 0
        
        total_budget = budget.get("total_amount", 0)
        if total_budget == 0:
            return 0
        
        expenses = get_monthly_expenses(user_id, start_date, end_date)
        usage_percentage = (expenses / total_budget) * 100
        
        return min(round(usage_percentage), 100)
    
    except Exception:
        return 0

def get_recent_transactions(user_id):
    try:
        from bson import ObjectId
        transactions = list(mongo.db.transactions.find({"user_id": ObjectId(user_id)})
                          .sort("date", -1)
                          .limit(5))
        
        formatted_transactions = []
        for transaction in transactions:
            formatted_transactions.append({
                "description": transaction.get("description", ""),
                "amount": transaction.get("amount", 0),
                "type": transaction.get("type", "expense"),
                "category": transaction.get("category", "Uncategorized"),
                "date": transaction.get("date", datetime.now()).strftime("%m/%d")
            })
        
        return formatted_transactions
    
    except Exception:
        return []

def get_transaction_count(user_id, start_date, end_date):
    try:
        from bson import ObjectId
        count = mongo.db.transactions.count_documents({
            "user_id": ObjectId(user_id),
            "date": {"$gte": start_date, "$lt": end_date}
        })
        return count
    except Exception:
        return 0

def get_avg_daily_spend(user_id, start_date, end_date):
    try:
        expenses = get_monthly_expenses(user_id, start_date, end_date)
        days_in_month = (end_date - start_date).days
        return round(expenses / days_in_month, 2) if days_in_month > 0 else 0
    except Exception:
        return 0

def get_top_category(user_id, start_date, end_date):
    try:
        from bson import ObjectId
        pipeline = [
            {
                "$match": {
                    "user_id": ObjectId(user_id),
                    "type": "expense",
                    "date": {"$gte": start_date, "$lt": end_date}
                }
            },
            {
                "$group": {
                    "_id": "$category",
                    "total": {"$sum": "$amount"}
                }
            },
            {"$sort": {"total": -1}},
            {"$limit": 1}
        ]
        
        result = list(mongo.db.transactions.aggregate(pipeline, allowDiskUse=True))
        return result[0]["_id"] if result else "None"
    except Exception:
        return "None"

def detect_recurring_transactions(user_id):
    try:
        from bson import ObjectId
        # Look for transactions with similar descriptions in the last 3 months
        three_months_ago = datetime.now() - timedelta(days=90)
        
        transactions = list(mongo.db.transactions.find({
            "user_id": ObjectId(user_id),
            "date": {"$gte": three_months_ago}
        }))
        
        # Group by similar descriptions (simplified detection)
        descriptions = [t.get("description", "").lower().strip() for t in transactions]
        description_counts = Counter(descriptions)
        
        # Count descriptions that appear 2+ times (potential recurring)
        recurring_count = sum(1 for count in description_counts.values() if count >= 2)
        return recurring_count
    
    except Exception:
        return 0

def get_category_breakdown(user_id, start_date, end_date):
    try:
        from bson import ObjectId
        pipeline = [
            {
                "$match": {
                    "user_id": ObjectId(user_id),
                    "type": "expense",
                    "date": {"$gte": start_date, "$lt": end_date}
                }
            },
            {
                "$group": {
                    "_id": "$category",
                    "total": {"$sum": "$amount"}
                }
            },
            {"$sort": {"total": -1}}
        ]
        
        result = list(mongo.db.transactions.aggregate(pipeline, allowDiskUse=True))
        return {item["_id"]: item["total"] for item in result}
    
    except Exception:
        return {}

# Auto-categorization function
def auto_categorize_transaction(description):
    """Use keyword matching to auto-categorize transactions"""
    description_lower = description.lower()
    
    # Check against keyword dictionary
    for category, keywords in CATEGORY_KEYWORDS.items():
        for keyword in keywords:
            if keyword in description_lower:
                return category
    
    return "Other"

# Alert checking function
def check_transaction_alerts(user_id, transaction):
    """Check if transaction triggers any alerts"""
    try:
        from bson import ObjectId
        
        # Get alert settings
        settings = mongo.db.alert_settings.find_one({"user_id": ObjectId(user_id)})
        if not settings:
            settings = {"budget_alert": True, "large_transaction_alert": True}
        
        # Large transaction alert
        if settings.get("large_transaction_alert") and transaction["amount"] > 500:
            alert_data = Alert.create_alert(
                user_id,
                "Large Transaction Detected",
                f"A {transaction['type']} of ${transaction['amount']:.2f} was recorded for {transaction['description']}",
                "warning"
            )
            mongo.db.alerts.insert_one(alert_data)
        
        # Budget threshold alert
        if settings.get("budget_alert") and transaction["type"] == "expense":
            current_month = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            next_month = (current_month + timedelta(days=32)).replace(day=1)
            
            budget_usage = get_budget_usage(user_id, current_month, next_month)
            if budget_usage >= 80 and budget_usage < 100:
                alert_data = Alert.create_alert(
                    user_id,
                    "Budget Alert",
                    f"You've used {budget_usage}% of your monthly budget",
                    "warning"
                )
                mongo.db.alerts.insert_one(alert_data)
            elif budget_usage >= 100:
                alert_data = Alert.create_alert(
                    user_id,
                    "Budget Exceeded",
                    f"You've exceeded your monthly budget by {budget_usage - 100}%",
                    "danger"
                )
                mongo.db.alerts.insert_one(alert_data)
    
    except Exception as e:
        print(f"Alert check error: {e}")

if __name__ == '__main__':
    app.run(debug=True)
