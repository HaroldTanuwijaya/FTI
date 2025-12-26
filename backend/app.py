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
import ssl
app.config["MONGO_URI"] = os.getenv("MONGO_URI", "mongodb://localhost:27017/fti_db")
app.config["MONGO_TLS"] = True
app.config["MONGO_TLS_INSECURE"] = True  # For development only
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

@app.route('/analytics')
def analytics_page():
    return render_template('analytics.html')

@app.route('/api/analytics/overview', methods=['GET'])
@token_required
def get_analytics_overview(current_user_id):
    try:
        from bson import ObjectId
        
        # Get current month data
        now = datetime.now()
        current_month = datetime(now.year, now.month, 1)
        
        # Get basic financial data
        current_income = get_monthly_income(current_user_id, current_month, now)
        current_expenses = get_monthly_expenses(current_user_id, current_month, now)
        
        # Simple monthly trends (last 3 months)
        monthly_trends = []
        for i in range(3):
            month_start = (current_month - timedelta(days=30*i)).replace(day=1)
            month_end = (month_start + timedelta(days=32)).replace(day=1)
            
            income = get_monthly_income(current_user_id, month_start, month_end)
            expenses = get_monthly_expenses(current_user_id, month_start, month_end)
            
            monthly_trends.append({
                "month": month_start.strftime("%b %Y"),
                "income": float(income),
                "expenses": float(expenses),
                "net": float(income - expenses)
            })
        
        # Get category data
        try:
            three_months_ago = current_month - timedelta(days=90)
            category_data = get_category_breakdown(current_user_id, three_months_ago, now)
            if not category_data:
                category_data = [{"category": "No Data", "total": 1}]
        except:
            category_data = [{"category": "No Data", "total": 1}]
        
        # Calculate health metrics
        savings_rate = ((current_income - current_expenses) / current_income * 100) if current_income > 0 else 0
        
        health_metrics = {
            "savings_rate": float(savings_rate),
            "expense_volatility": 15.0,  # Placeholder
            "top_spending_day": {"date": "N/A", "amount": 0},
            "average_transaction_size": {
                "average": float(current_expenses / 10) if current_expenses > 0 else 0, 
                "count": 10
            }
        }
        
        # Goals analysis
        try:
            goals = list(mongo.db.goals.find({"user_id": ObjectId(current_user_id)}).limit(10))
            completed = sum(1 for g in goals if g.get("current_amount", 0) >= g.get("target_amount", 1))
            
            goals_analysis = {
                "total_goals": len(goals),
                "completed": completed,
                "in_progress": len(goals) - completed,
                "completion_rate": float((completed / len(goals) * 100) if goals else 0)
            }
        except:
            goals_analysis = {
                "total_goals": 0,
                "completed": 0,
                "in_progress": 0,
                "completion_rate": 0.0
            }
        
        # FTI breakdown
        fti_breakdown = {
            "cash_flow": float(min(100, max(0, savings_rate + 50))),
            "spending_control": 70.0,
            "savings_discipline": float(min(100, max(0, savings_rate * 5))),
            "stability": 60.0,
            "debt_management": 90.0,
            "goal_progress": float(goals_analysis["completion_rate"])
        }
        
        # Simple daily pattern
        daily_pattern = [
            {"day": "Monday", "total": float(current_expenses * 0.15), "average": float(current_expenses * 0.15)},
            {"day": "Tuesday", "total": float(current_expenses * 0.12), "average": float(current_expenses * 0.12)},
            {"day": "Wednesday", "total": float(current_expenses * 0.14), "average": float(current_expenses * 0.14)},
            {"day": "Thursday", "total": float(current_expenses * 0.16), "average": float(current_expenses * 0.16)},
            {"day": "Friday", "total": float(current_expenses * 0.18), "average": float(current_expenses * 0.18)},
            {"day": "Saturday", "total": float(current_expenses * 0.20), "average": float(current_expenses * 0.20)},
            {"day": "Sunday", "total": float(current_expenses * 0.05), "average": float(current_expenses * 0.05)}
        ]
        
        return jsonify({
            "monthly_trends": monthly_trends,
            "category_breakdown": category_data[:6],  # Limit to 6 categories
            "spending_patterns": {"daily_pattern": daily_pattern},
            "health_metrics": health_metrics,
            "goals_analysis": goals_analysis,
            "fti_score_breakdown": fti_breakdown
        })
        
    except Exception as e:
        print(f"Analytics error: {e}")
        # Return basic mock data
        return jsonify({
            "monthly_trends": [
                {"month": "Dec 2024", "income": 0, "expenses": 0, "net": 0},
                {"month": "Nov 2024", "income": 0, "expenses": 0, "net": 0},
                {"month": "Oct 2024", "income": 0, "expenses": 0, "net": 0}
            ],
            "category_breakdown": [{"category": "No Data", "total": 1}],
            "spending_patterns": {"daily_pattern": [
                {"day": "Monday", "total": 0, "average": 0},
                {"day": "Tuesday", "total": 0, "average": 0},
                {"day": "Wednesday", "total": 0, "average": 0},
                {"day": "Thursday", "total": 0, "average": 0},
                {"day": "Friday", "total": 0, "average": 0},
                {"day": "Saturday", "total": 0, "average": 0},
                {"day": "Sunday", "total": 0, "average": 0}
            ]},
            "health_metrics": {
                "savings_rate": 0,
                "expense_volatility": 0,
                "top_spending_day": {"date": "N/A", "amount": 0},
                "average_transaction_size": {"average": 0, "count": 0}
            },
            "goals_analysis": {
                "total_goals": 0,
                "completed": 0,
                "in_progress": 0,
                "completion_rate": 0
            },
            "fti_score_breakdown": {
                "cash_flow": 0,
                "spending_control": 0,
                "savings_discipline": 0,
                "stability": 0,
                "debt_management": 0,
                "goal_progress": 0
            }
        })

def get_spending_patterns(user_id, start_date, end_date):
    try:
        from bson import ObjectId
        
        # Daily spending pattern
        pipeline = [
            {"$match": {
                "user_id": ObjectId(user_id),
                "type": "expense",
                "date": {"$gte": start_date, "$lte": end_date}
            }},
            {"$group": {
                "_id": {"$dayOfWeek": "$date"},
                "total": {"$sum": "$amount"},
                "count": {"$sum": 1}
            }},
            {"$sort": {"_id": 1}}
        ]
        
        daily_pattern = list(mongo.db.transactions.aggregate(pipeline))
        days = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
        
        formatted_daily = []
        for i in range(7):
            day_data = next((d for d in daily_pattern if d["_id"] == i+1), {"total": 0, "count": 0})
            formatted_daily.append({
                "day": days[i],
                "total": day_data["total"],
                "count": day_data["count"],
                "average": day_data["total"] / day_data["count"] if day_data["count"] > 0 else 0
            })
        
        return {
            "daily_pattern": formatted_daily,
            "peak_spending_day": max(formatted_daily, key=lambda x: x["total"])["day"],
            "most_frequent_day": max(formatted_daily, key=lambda x: x["count"])["day"]
        }
        
    except Exception:
        return {"daily_pattern": [], "peak_spending_day": "N/A", "most_frequent_day": "N/A"}

def calculate_savings_rate(user_id, start_date, end_date):
    try:
        income = get_monthly_income(user_id, start_date, end_date)
        expenses = get_monthly_expenses(user_id, start_date, end_date)
        return ((income - expenses) / income * 100) if income > 0 else 0
    except:
        return 0

def calculate_expense_volatility(user_id, start_date, end_date):
    try:
        from bson import ObjectId
        
        # Get monthly expenses for volatility calculation
        monthly_expenses = []
        current = start_date
        
        while current < end_date:
            next_month = (current + timedelta(days=32)).replace(day=1)
            expense = get_monthly_expenses(user_id, current, next_month)
            if expense > 0:
                monthly_expenses.append(expense)
            current = next_month
        
        if len(monthly_expenses) < 2:
            return 0
        
        # Calculate coefficient of variation
        import statistics
        mean_expense = statistics.mean(monthly_expenses)
        std_expense = statistics.stdev(monthly_expenses)
        
        return (std_expense / mean_expense * 100) if mean_expense > 0 else 0
        
    except:
        return 0

def get_top_spending_day(user_id, start_date, end_date):
    try:
        from bson import ObjectId
        
        pipeline = [
            {"$match": {
                "user_id": ObjectId(user_id),
                "type": "expense",
                "date": {"$gte": start_date, "$lte": end_date}
            }},
            {"$group": {
                "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$date"}},
                "total": {"$sum": "$amount"}
            }},
            {"$sort": {"total": -1}},
            {"$limit": 1}
        ]
        
        result = list(mongo.db.transactions.aggregate(pipeline))
        if result:
            return {
                "date": result[0]["_id"],
                "amount": result[0]["total"]
            }
        return {"date": "N/A", "amount": 0}
        
    except:
        return {"date": "N/A", "amount": 0}

def get_avg_transaction_size(user_id, start_date, end_date):
    try:
        from bson import ObjectId
        
        pipeline = [
            {"$match": {
                "user_id": ObjectId(user_id),
                "type": "expense",
                "date": {"$gte": start_date, "$lte": end_date}
            }},
            {"$group": {
                "_id": None,
                "avg_amount": {"$avg": "$amount"},
                "total_transactions": {"$sum": 1}
            }}
        ]
        
        result = list(mongo.db.transactions.aggregate(pipeline))
        if result:
            return {
                "average": result[0]["avg_amount"],
                "count": result[0]["total_transactions"]
            }
        return {"average": 0, "count": 0}
        
    except:
        return {"average": 0, "count": 0}

def get_goals_analysis(user_id):
    try:
        from bson import ObjectId
        
        goals = list(mongo.db.goals.find({"user_id": ObjectId(user_id)}))
        
        if not goals:
            return {"total_goals": 0, "completed": 0, "in_progress": 0, "completion_rate": 0}
        
        completed = sum(1 for g in goals if g.get("current_amount", 0) >= g.get("target_amount", 1))
        in_progress = len(goals) - completed
        
        return {
            "total_goals": len(goals),
            "completed": completed,
            "in_progress": in_progress,
            "completion_rate": (completed / len(goals) * 100) if goals else 0,
            "total_target": sum(g.get("target_amount", 0) for g in goals),
            "total_saved": sum(g.get("current_amount", 0) for g in goals)
        }
        
    except:
        return {"total_goals": 0, "completed": 0, "in_progress": 0, "completion_rate": 0}

def get_fti_score_breakdown(user_id):
    try:
        from bson import ObjectId
        current_month = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        next_month = (current_month + timedelta(days=32)).replace(day=1)
        
        # Get individual component scores (simplified version of calculate_fti_score)
        income = get_monthly_income(user_id, current_month, next_month)
        expenses = get_monthly_expenses(user_id, current_month, next_month)
        
        # Calculate each component
        cash_flow_score = min(100, max(0, ((income - expenses) / income * 100))) if income > 0 else 0
        savings_rate = ((income - expenses) / income * 100) if income > 0 else 0
        savings_score = min(100, max(0, savings_rate * 5))
        
        return {
            "cash_flow": round(cash_flow_score),
            "spending_control": 70,  # Placeholder
            "savings_discipline": round(savings_score),
            "stability": 60,  # Placeholder
            "debt_management": 90,  # Placeholder
            "goal_progress": 65   # Placeholder
        }
        
    except:
        return {
            "cash_flow": 0,
            "spending_control": 0,
            "savings_discipline": 0,
            "stability": 0,
            "debt_management": 0,
            "goal_progress": 0
        }

@app.route('/transactions')
def transactions_page():
    return render_template('transactions.html')

@app.route('/api/transactions/history', methods=['GET'])
@token_required
def get_transaction_history(current_user_id):
    try:
        from bson import ObjectId
        
        # Get query parameters
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 20))
        sort_by = request.args.get('sort', 'date')
        sort_order = request.args.get('order', 'desc')
        category_filter = request.args.get('category', '')
        type_filter = request.args.get('type', '')
        
        # Build query
        query = {"user_id": ObjectId(current_user_id)}
        if category_filter:
            query["category"] = category_filter
        if type_filter:
            query["type"] = type_filter
        
        # Build sort
        sort_direction = -1 if sort_order == 'desc' else 1
        sort_field = sort_by if sort_by in ['date', 'amount', 'category', 'type'] else 'date'
        
        # Get total count
        total = mongo.db.transactions.count_documents(query)
        
        # Get transactions with pagination
        skip = (page - 1) * limit
        transactions = list(mongo.db.transactions.find(query)
                          .sort(sort_field, sort_direction)
                          .skip(skip)
                          .limit(limit))
        
        # Format transactions
        formatted_transactions = []
        for t in transactions:
            formatted_transactions.append({
                "id": str(t["_id"]),
                "amount": t["amount"],
                "type": t["type"],
                "description": t["description"],
                "category": t["category"],
                "date": t["date"].strftime("%Y-%m-%d %H:%M")
            })
        
        return jsonify({
            "transactions": formatted_transactions,
            "pagination": {
                "current_page": page,
                "total_pages": (total + limit - 1) // limit,
                "total_items": total,
                "items_per_page": limit
            }
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

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
def api_dashboard(current_user_id):
    try:
        # Get period from query parameter
        period = request.args.get('period', 'month')
        
        # Calculate date range based on period
        now = datetime.now()
        if period == 'today':
            start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = now
        elif period == 'week':
            start_date = now - timedelta(days=now.weekday())
            start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = now
        elif period == 'month':
            start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            end_date = (start_date + timedelta(days=32)).replace(day=1)
        elif period == 'year':
            start_date = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
            end_date = now
        else:  # all
            start_date = datetime(2000, 1, 1)
            end_date = now
        
        dashboard_data = {
            "fti_score": calculate_fti_score(current_user_id),
            "monthly_income": get_monthly_income(current_user_id, start_date, end_date),
            "monthly_expenses": get_monthly_expenses(current_user_id, start_date, end_date),
            "net_flow": 0,
            "wallet_balance": get_wallet_balance(current_user_id),
            "budget_used": get_budget_usage(current_user_id, start_date, end_date),
            "recent_transactions": get_recent_transactions(current_user_id),
            "monthly_summary": {
                "transaction_count": get_transaction_count(current_user_id, start_date, end_date),
                "daily_average": get_avg_daily_spend(current_user_id, start_date, end_date),
                "top_category": get_top_category(current_user_id, start_date, end_date),
                "transaction_count": get_monthly_transaction_count(current_user_id, start_date, end_date)
            }
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
        
        # Check for alerts
        check_transaction_alerts(current_user_id, transaction_data)
        
        return jsonify({"success": True, "category": category})
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/budget', methods=['POST'])
@token_required
def set_budget(current_user_id):
    try:
        from bson import ObjectId
        data = request.get_json()
        
        # Get current month if not provided
        current_month = data.get('month', datetime.now().strftime("%Y-%m"))
        
        # Create budget data
        budget_data = {
            "user_id": ObjectId(current_user_id),
            "month": current_month,
            "total_amount": float(data['total_amount']),
            "categories": {},
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        # Update or insert
        mongo.db.budgets.update_one(
            {"user_id": ObjectId(current_user_id), "month": current_month},
            {"$set": budget_data},
            upsert=True
        )
        
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
def monthly_report():
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
                "deadline": goal.get("deadline", ""),
                "status": goal.get("status", "active")
            })
        
        return jsonify({"goals": formatted_goals})
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/goals', methods=['POST'])
@token_required
def create_goal(current_user_id):
    try:
        from bson import ObjectId
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        if not data.get('name'):
            return jsonify({"error": "Name is required"}), 400
        if not data.get('target_amount'):
            return jsonify({"error": "Target amount is required"}), 400
        if not data.get('deadline'):
            return jsonify({"error": "Deadline is required"}), 400
        
        goal_data = {
            "user_id": ObjectId(current_user_id),
            "name": data['name'],
            "target_amount": float(data['target_amount']),
            "current_amount": float(data.get('current_amount', 0)),
            "deadline": data['deadline'],
            "status": "active",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        mongo.db.goals.insert_one(goal_data)
        
        return jsonify({"success": True})
    
    except ValueError as e:
        return jsonify({"error": "Invalid number format"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/goals/<goal_id>', methods=['GET'])
@token_required
def get_goal(current_user_id, goal_id):
    try:
        from bson import ObjectId
        goal = mongo.db.goals.find_one({
            "_id": ObjectId(goal_id),
            "user_id": ObjectId(current_user_id)
        })
        
        if not goal:
            return jsonify({"error": "Goal not found"}), 404
        
        return jsonify({
            "_id": str(goal["_id"]),
            "name": goal.get("name", ""),
            "target_amount": goal.get("target_amount", 0),
            "current_amount": goal.get("current_amount", 0),
            "deadline": goal.get("deadline", ""),
            "status": goal.get("status", "active")
        })
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/goals/<goal_id>', methods=['PUT'])
@token_required
def update_goal(current_user_id, goal_id):
    try:
        from bson import ObjectId
        data = request.get_json()
        
        update_data = {
            "current_amount": float(data.get('current_amount', 0)),
            "updated_at": datetime.utcnow()
        }
        
        # Optionally update other fields if provided
        if 'name' in data:
            update_data['name'] = data['name']
        if 'target_amount' in data:
            update_data['target_amount'] = float(data['target_amount'])
        if 'deadline' in data:
            update_data['deadline'] = data['deadline']
        
        result = mongo.db.goals.update_one(
            {"_id": ObjectId(goal_id), "user_id": ObjectId(current_user_id)},
            {"$set": update_data}
        )
        
        if result.matched_count == 0:
            return jsonify({"error": "Goal not found"}), 404
        
        return jsonify({"message": "Goal updated successfully"})
    
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
        
        return jsonify({"success": True})
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Spending Trends API
@app.route('/api/spending-trends')
@token_required
def get_spending_trends(current_user_id):
    try:
        from bson import ObjectId
        from collections import defaultdict
        
        # Get last 7 days
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        seven_days_ago = today - timedelta(days=6)
        
        # Get transactions
        transactions = list(mongo.db.transactions.find({
            "user_id": ObjectId(current_user_id),
            "date": {"$gte": seven_days_ago, "$lte": datetime.now()}
        }))
        
        # Aggregate by day
        daily_data = defaultdict(lambda: {"income": 0, "expense": 0})
        
        for t in transactions:
            date_key = t['date'].strftime('%Y-%m-%d')
            if t['type'] == 'income':
                daily_data[date_key]['income'] += t['amount']
            else:
                daily_data[date_key]['expense'] += t['amount']
        
        # Build 7-day array
        trends = []
        for i in range(7):
            date = seven_days_ago + timedelta(days=i)
            date_key = date.strftime('%Y-%m-%d')
            trends.append({
                "date": date_key,
                "label": "Today" if i == 6 else date.strftime('%a'),
                "income": daily_data[date_key]['income'],
                "expense": daily_data[date_key]['expense']
            })
        
        return jsonify({"trends": trends})
    
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
                "_id": str(alert.get("_id")),
                "title": alert.get("title", ""),
                "message": alert.get("message", ""),
                "type": alert.get("type", "info"),
                "read": alert.get("read", False),
                "created_at": alert.get("created_at", datetime.now()).isoformat()
            })
        
        return jsonify({"alerts": formatted_alerts})
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/alerts/mark-read', methods=['POST'])
@token_required
def mark_alerts_read(current_user_id):
    try:
        from bson import ObjectId
        mongo.db.alerts.update_many(
            {"user_id": ObjectId(current_user_id)},
            {"$set": {"read": True}}
        )
        return jsonify({"success": True})
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

# User Settings API
@app.route('/api/settings/currency', methods=['GET'])
@token_required
def get_currency(current_user_id):
    try:
        from bson import ObjectId
        user = mongo.db.users.find_one({"_id": ObjectId(current_user_id)})
        return jsonify({"currency": user.get("currency", "USD")})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/settings/currency', methods=['POST'])
@token_required
def set_currency(current_user_id):
    try:
        from bson import ObjectId
        data = request.get_json()
        
        mongo.db.users.update_one(
            {"_id": ObjectId(current_user_id)},
            {"$set": {"currency": data.get("currency", "USD")}}
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
        if income > 0 and expenses > 0:
            cash_flow_ratio = (income - expenses) / income
            cash_flow_score = min(100, max(0, cash_flow_ratio * 100))
        elif income > 0 and expenses == 0:
            # Has income but no expenses - neutral score until they start tracking
            cash_flow_score = 50
        else:
            # No financial activity
            cash_flow_score = 0
        
        # Spending Control (20%) - Budget adherence
        budget_usage = get_budget_usage(user_id, current_month, next_month)
        spending_control_score = max(0, 100 - budget_usage) if budget_usage > 0 else 70
        
        # Savings Discipline (20%) - Savings rate
        if income > 0 and expenses > 0:
            savings_rate = ((income - expenses) / income * 100)
            savings_discipline_score = min(100, max(0, savings_rate * 5))  # 20% savings = 100 score
        elif income > 0 and expenses == 0:
            # Has income but no expenses recorded - assume no active saving habit yet
            savings_discipline_score = 30  # Low score until they start tracking expenses
        else:
            # No income or financial activity
            savings_discipline_score = 0
        
        # Stability & Consistency (15%) - Transaction regularity
        transaction_count = get_transaction_count(user_id, current_month, next_month)
        if transaction_count == 0:
            stability_score = 0  # No transactions = no stability
        else:
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

def get_wallet_balance(user_id):
    try:
        from bson import ObjectId
        # Get all transactions
        transactions = mongo.db.transactions.find({"user_id": ObjectId(user_id)})
        
        total_income = 0
        total_expenses = 0
        
        for t in transactions:
            if t['type'] == 'income':
                total_income += t['amount']
            else:
                total_expenses += t['amount']
        
        return round(total_income - total_expenses, 2)
    except:
        return 0

def get_budget_usage(user_id, start_date, end_date):
    try:
        from bson import ObjectId
        # Always use current month for budget lookup
        current_month = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        budget = mongo.db.budgets.find_one({
            "user_id": ObjectId(user_id), 
            "month": current_month.strftime("%Y-%m")
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
        from bson import ObjectId
        
        # Get all expense transactions for the period
        transactions = list(mongo.db.transactions.find({
            "user_id": ObjectId(user_id),
            "type": "expense",
            "date": {"$gte": start_date, "$lt": end_date}
        }))
        
        if not transactions:
            return 0
        
        # Group by date to get unique spending days
        spending_days = set()
        total_expenses = 0
        
        for transaction in transactions:
            transaction_date = transaction['date'].date()
            spending_days.add(transaction_date)
            total_expenses += transaction['amount']
        
        # Calculate average based on actual spending days, not calendar days
        active_days = len(spending_days)
        return round(total_expenses / active_days, 2) if active_days > 0 else 0
        
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

def get_monthly_transaction_count(user_id, start_date, end_date):
    try:
        from bson import ObjectId
        count = mongo.db.transactions.count_documents({
            "user_id": ObjectId(user_id),
            "date": {"$gte": start_date, "$lte": end_date}
        })
        return count
    except Exception:
        return 0

def detect_recurring_transactions(user_id):
    try:
        from bson import ObjectId
        # Look for transactions in current month
        now = datetime.now()
        start_of_month = datetime(now.year, now.month, 1)
        
        transactions = list(mongo.db.transactions.find({
            "user_id": ObjectId(user_id),
            "date": {"$gte": start_of_month},
            "type": "expense"  # Only count expense transactions
        }))
        
        # Group by similar descriptions and amounts (more accurate detection)
        recurring_patterns = {}
        for t in transactions:
            description = t.get("description", "").lower().strip()
            amount = round(float(t.get("amount", 0)), 2)
            key = f"{description}_{amount}"
            
            if key in recurring_patterns:
                recurring_patterns[key] += 1
            else:
                recurring_patterns[key] = 1
        
        # Count actual recurring transactions (appeared 2+ times this month)
        recurring_transactions = sum(count for count in recurring_patterns.values() if count >= 2)
        return recurring_transactions
    
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
