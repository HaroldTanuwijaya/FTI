"""
MongoDB Database Initialization Script
Creates all collections with schemas and indexes for FTI application
"""

from pymongo import MongoClient, ASCENDING, DESCENDING
from datetime import datetime
import os

def init_database():
    """Initialize MongoDB database with collections and indexes"""
    
    # Connect to MongoDB
    mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017/fti_db")
    client = MongoClient(mongo_uri)
    db = client.get_database()
    
    print("🗄️  Initializing FTI Database...")
    print("=" * 50)
    
    # 1. Users Collection
    print("\n📋 Creating 'users' collection...")
    if "users" not in db.list_collection_names():
        db.create_collection("users", validator={
            "$jsonSchema": {
                "bsonType": "object",
                "required": ["email", "password_hash", "name", "created_at"],
                "properties": {
                    "email": {"bsonType": "string"},
                    "password_hash": {"bsonType": "binData"},
                    "name": {"bsonType": "string"},
                    "created_at": {"bsonType": "date"},
                    "updated_at": {"bsonType": "date"}
                }
            }
        })
    db.users.create_index([("email", ASCENDING)], unique=True)
    print("✅ Users collection created with email index")
    
    # 2. Transactions Collection
    print("\n📋 Creating 'transactions' collection...")
    if "transactions" not in db.list_collection_names():
        db.create_collection("transactions", validator={
            "$jsonSchema": {
                "bsonType": "object",
                "required": ["user_id", "amount", "type", "description", "date"],
                "properties": {
                    "user_id": {"bsonType": "objectId"},
                    "amount": {"bsonType": "double"},
                    "type": {"bsonType": "string", "enum": ["income", "expense"]},
                    "description": {"bsonType": "string"},
                    "category": {"bsonType": "string"},
                    "date": {"bsonType": "date"},
                    "created_at": {"bsonType": "date"}
                }
            }
        })
    db.transactions.create_index([("user_id", ASCENDING), ("date", DESCENDING)])
    db.transactions.create_index([("user_id", ASCENDING), ("type", ASCENDING)])
    db.transactions.create_index([("user_id", ASCENDING), ("category", ASCENDING)])
    db.transactions.create_index([("user_id", ASCENDING), ("date", DESCENDING), ("type", ASCENDING)])
    print("✅ Transactions collection created with 4 indexes")
    
    # 3. Budgets Collection
    print("\n📋 Creating 'budgets' collection...")
    if "budgets" not in db.list_collection_names():
        db.create_collection("budgets", validator={
            "$jsonSchema": {
                "bsonType": "object",
                "required": ["user_id", "month", "total_amount"],
                "properties": {
                    "user_id": {"bsonType": "objectId"},
                    "month": {"bsonType": "string"},
                    "total_amount": {"bsonType": "double"},
                    "categories": {"bsonType": "object"},
                    "created_at": {"bsonType": "date"},
                    "updated_at": {"bsonType": "date"}
                }
            }
        })
    db.budgets.create_index([("user_id", ASCENDING), ("month", ASCENDING)], unique=True)
    print("✅ Budgets collection created with compound index")
    
    # 4. Goals Collection
    print("\n📋 Creating 'goals' collection...")
    if "goals" not in db.list_collection_names():
        db.create_collection("goals", validator={
            "$jsonSchema": {
                "bsonType": "object",
                "required": ["user_id", "name", "target_amount", "current_amount", "target_date"],
                "properties": {
                    "user_id": {"bsonType": "objectId"},
                    "name": {"bsonType": "string"},
                    "target_amount": {"bsonType": "double"},
                    "current_amount": {"bsonType": "double"},
                    "target_date": {"bsonType": "string"},
                    "status": {"bsonType": "string", "enum": ["active", "completed", "cancelled"]},
                    "created_at": {"bsonType": "date"},
                    "updated_at": {"bsonType": "date"}
                }
            }
        })
    db.goals.create_index([("user_id", ASCENDING), ("status", ASCENDING)])
    db.goals.create_index([("user_id", ASCENDING), ("target_date", ASCENDING)])
    print("✅ Goals collection created with 2 indexes")
    
    # 5. Alerts Collection
    print("\n📋 Creating 'alerts' collection...")
    if "alerts" not in db.list_collection_names():
        db.create_collection("alerts", validator={
            "$jsonSchema": {
                "bsonType": "object",
                "required": ["user_id", "title", "message", "type"],
                "properties": {
                    "user_id": {"bsonType": "objectId"},
                    "title": {"bsonType": "string"},
                    "message": {"bsonType": "string"},
                    "type": {"bsonType": "string", "enum": ["info", "warning", "danger", "success"]},
                    "read": {"bsonType": "bool"},
                    "created_at": {"bsonType": "date"}
                }
            }
        })
    db.alerts.create_index([("user_id", ASCENDING), ("created_at", DESCENDING)])
    db.alerts.create_index([("user_id", ASCENDING), ("read", ASCENDING)])
    print("✅ Alerts collection created with 2 indexes")
    
    # 6. FTI Scores Collection
    print("\n📋 Creating 'fti_scores' collection...")
    if "fti_scores" not in db.list_collection_names():
        db.create_collection("fti_scores", validator={
            "$jsonSchema": {
                "bsonType": "object",
                "required": ["user_id", "score", "components", "calculated_at"],
                "properties": {
                    "user_id": {"bsonType": "objectId"},
                    "score": {"bsonType": "int"},
                    "components": {
                        "bsonType": "object",
                        "properties": {
                            "cash_flow": {"bsonType": "double"},
                            "spending_control": {"bsonType": "double"},
                            "savings_discipline": {"bsonType": "double"},
                            "stability": {"bsonType": "double"},
                            "debt": {"bsonType": "double"},
                            "goal_progress": {"bsonType": "double"}
                        }
                    },
                    "calculated_at": {"bsonType": "date"}
                }
            }
        })
    db.fti_scores.create_index([("user_id", ASCENDING), ("calculated_at", DESCENDING)])
    print("✅ FTI Scores collection created with index")
    
    # 7. Alert Settings Collection
    print("\n📋 Creating 'alert_settings' collection...")
    if "alert_settings" not in db.list_collection_names():
        db.create_collection("alert_settings", validator={
            "$jsonSchema": {
                "bsonType": "object",
                "required": ["user_id"],
                "properties": {
                    "user_id": {"bsonType": "objectId"},
                    "budget_alert": {"bsonType": "bool"},
                    "large_transaction_alert": {"bsonType": "bool"},
                    "goal_alert": {"bsonType": "bool"},
                    "recurring_alert": {"bsonType": "bool"},
                    "updated_at": {"bsonType": "date"}
                }
            }
        })
    db.alert_settings.create_index([("user_id", ASCENDING)], unique=True)
    print("✅ Alert Settings collection created with index")
    
    # Summary
    print("\n" + "=" * 50)
    print("✅ Database initialization complete!")
    print("\n📊 Collections Summary:")
    print(f"   • users: {db.users.count_documents({})} documents")
    print(f"   • transactions: {db.transactions.count_documents({})} documents")
    print(f"   • budgets: {db.budgets.count_documents({})} documents")
    print(f"   • goals: {db.goals.count_documents({})} documents")
    print(f"   • alerts: {db.alerts.count_documents({})} documents")
    print(f"   • fti_scores: {db.fti_scores.count_documents({})} documents")
    print(f"   • alert_settings: {db.alert_settings.count_documents({})} documents")
    
    print("\n📈 Total Indexes:")
    total_indexes = 0
    for collection in ['users', 'transactions', 'budgets', 'goals', 'alerts', 'fti_scores', 'alert_settings']:
        indexes = len(list(db[collection].list_indexes()))
        total_indexes += indexes
        print(f"   • {collection}: {indexes} indexes")
    print(f"\n   Total: {total_indexes} indexes created")
    
    print("\n🎉 Database is ready for use!")
    
    client.close()

if __name__ == "__main__":
    init_database()
