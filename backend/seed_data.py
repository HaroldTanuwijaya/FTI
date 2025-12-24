"""
MongoDB Sample Data Generator
Creates sample data for testing FTI application
"""

from pymongo import MongoClient
from datetime import datetime, timedelta
import bcrypt
import os
from bson import ObjectId

def generate_sample_data():
    """Generate sample data for testing"""
    
    # Connect to MongoDB
    mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017/fti_db")
    client = MongoClient(mongo_uri)
    db = client.get_database()
    
    print("🎲 Generating Sample Data...")
    print("=" * 50)
    
    # Create sample user
    print("\n👤 Creating sample user...")
    password_hash = bcrypt.hashpw("password123".encode('utf-8'), bcrypt.gensalt())
    
    sample_user = {
        "_id": ObjectId(),
        "email": "demo@fti.com",
        "password_hash": password_hash,
        "name": "Demo User",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    
    # Check if user exists
    existing_user = db.users.find_one({"email": "demo@fti.com"})
    if existing_user:
        user_id = existing_user["_id"]
        print("✅ Sample user already exists")
    else:
        result = db.users.insert_one(sample_user)
        user_id = result.inserted_id
        print("✅ Sample user created: demo@fti.com / password123")
    
    # Create sample transactions
    print("\n💰 Creating sample transactions...")
    current_date = datetime.now()
    
    sample_transactions = [
        # Income
        {"amount": 5000, "type": "income", "description": "Monthly Salary", "category": "Income", "date": current_date - timedelta(days=25)},
        {"amount": 500, "type": "income", "description": "Freelance Project", "category": "Income", "date": current_date - timedelta(days=15)},
        
        # Expenses
        {"amount": 1200, "type": "expense", "description": "Rent Payment", "category": "Bills & Utilities", "date": current_date - timedelta(days=24)},
        {"amount": 150, "type": "expense", "description": "Electric Bill", "category": "Bills & Utilities", "date": current_date - timedelta(days=20)},
        {"amount": 80, "type": "expense", "description": "Internet Bill", "category": "Bills & Utilities", "date": current_date - timedelta(days=20)},
        {"amount": 250, "type": "expense", "description": "Grocery Shopping", "category": "Food & Dining", "date": current_date - timedelta(days=18)},
        {"amount": 45, "type": "expense", "description": "Restaurant Dinner", "category": "Food & Dining", "date": current_date - timedelta(days=16)},
        {"amount": 60, "type": "expense", "description": "Gas Station", "category": "Transportation", "date": current_date - timedelta(days=14)},
        {"amount": 120, "type": "expense", "description": "Amazon Shopping", "category": "Shopping", "date": current_date - timedelta(days=12)},
        {"amount": 35, "type": "expense", "description": "Netflix Subscription", "category": "Entertainment", "date": current_date - timedelta(days=10)},
        {"amount": 200, "type": "expense", "description": "Grocery Shopping", "category": "Food & Dining", "date": current_date - timedelta(days=8)},
        {"amount": 50, "type": "expense", "description": "Coffee Shop", "category": "Food & Dining", "date": current_date - timedelta(days=5)},
        {"amount": 75, "type": "expense", "description": "Pharmacy", "category": "Healthcare", "date": current_date - timedelta(days=3)},
        {"amount": 40, "type": "expense", "description": "Uber Ride", "category": "Transportation", "date": current_date - timedelta(days=2)},
        {"amount": 90, "type": "expense", "description": "Clothing Store", "category": "Shopping", "date": current_date - timedelta(days=1)},
    ]
    
    for transaction in sample_transactions:
        transaction["user_id"] = user_id
        transaction["created_at"] = datetime.utcnow()
    
    # Clear existing sample transactions
    db.transactions.delete_many({"user_id": user_id})
    db.transactions.insert_many(sample_transactions)
    print(f"✅ Created {len(sample_transactions)} sample transactions")
    
    # Create sample budget
    print("\n💵 Creating sample budget...")
    current_month = current_date.strftime("%Y-%m")
    
    sample_budget = {
        "user_id": user_id,
        "month": current_month,
        "total_amount": 3000,
        "categories": {
            "Food & Dining": 500,
            "Transportation": 200,
            "Shopping": 300,
            "Entertainment": 100,
            "Bills & Utilities": 1500
        },
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    
    db.budgets.replace_one(
        {"user_id": user_id, "month": current_month},
        sample_budget,
        upsert=True
    )
    print("✅ Sample budget created")
    
    # Create sample goals
    print("\n🎯 Creating sample goals...")
    sample_goals = [
        {
            "user_id": user_id,
            "name": "Emergency Fund",
            "target_amount": 10000,
            "current_amount": 3500,
            "target_date": (current_date + timedelta(days=180)).strftime("%Y-%m-%d"),
            "status": "active",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "user_id": user_id,
            "name": "Vacation Savings",
            "target_amount": 5000,
            "current_amount": 1200,
            "target_date": (current_date + timedelta(days=120)).strftime("%Y-%m-%d"),
            "status": "active",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "user_id": user_id,
            "name": "New Laptop",
            "target_amount": 2000,
            "current_amount": 800,
            "target_date": (current_date + timedelta(days=60)).strftime("%Y-%m-%d"),
            "status": "active",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
    ]
    
    db.goals.delete_many({"user_id": user_id})
    db.goals.insert_many(sample_goals)
    print(f"✅ Created {len(sample_goals)} sample goals")
    
    # Create sample alerts
    print("\n🔔 Creating sample alerts...")
    sample_alerts = [
        {
            "user_id": user_id,
            "title": "Budget Alert",
            "message": "You've used 75% of your monthly budget",
            "type": "warning",
            "read": False,
            "created_at": datetime.utcnow() - timedelta(days=2)
        },
        {
            "user_id": user_id,
            "title": "Goal Milestone",
            "message": "You've reached 50% of your Emergency Fund goal!",
            "type": "success",
            "read": False,
            "created_at": datetime.utcnow() - timedelta(days=5)
        }
    ]
    
    db.alerts.delete_many({"user_id": user_id})
    db.alerts.insert_many(sample_alerts)
    print(f"✅ Created {len(sample_alerts)} sample alerts")
    
    # Create alert settings
    print("\n⚙️  Creating alert settings...")
    alert_settings = {
        "user_id": user_id,
        "budget_alert": True,
        "large_transaction_alert": True,
        "goal_alert": True,
        "recurring_alert": True,
        "updated_at": datetime.utcnow()
    }
    
    db.alert_settings.replace_one(
        {"user_id": user_id},
        alert_settings,
        upsert=True
    )
    print("✅ Alert settings created")
    
    # Summary
    print("\n" + "=" * 50)
    print("✅ Sample data generation complete!")
    print("\n📊 Sample Data Summary:")
    print(f"   • User: demo@fti.com / password123")
    print(f"   • Transactions: {len(sample_transactions)}")
    print(f"   • Budget: ${sample_budget['total_amount']}")
    print(f"   • Goals: {len(sample_goals)}")
    print(f"   • Alerts: {len(sample_alerts)}")
    print("\n🎉 You can now login and test the application!")
    
    client.close()

if __name__ == "__main__":
    generate_sample_data()
