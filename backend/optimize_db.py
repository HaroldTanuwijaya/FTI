"""
Database optimization script for FTI
Creates indexes and optimizes MongoDB collections
"""

from pymongo import MongoClient, ASCENDING, DESCENDING
import os

def create_indexes():
    """Create database indexes for optimal query performance"""
    
    # Connect to MongoDB
    mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017/fti_db")
    client = MongoClient(mongo_uri)
    db = client.get_database()
    
    print("Creating database indexes...")
    
    # Users collection indexes
    db.users.create_index([("email", ASCENDING)], unique=True)
    print("✓ Users: email index created")
    
    # Transactions collection indexes
    db.transactions.create_index([("user_id", ASCENDING), ("date", DESCENDING)])
    db.transactions.create_index([("user_id", ASCENDING), ("type", ASCENDING)])
    db.transactions.create_index([("user_id", ASCENDING), ("category", ASCENDING)])
    db.transactions.create_index([("user_id", ASCENDING), ("date", DESCENDING), ("type", ASCENDING)])
    print("✓ Transactions: user_id, date, type, category indexes created")
    
    # Budgets collection indexes
    db.budgets.create_index([("user_id", ASCENDING), ("month", ASCENDING)], unique=True)
    print("✓ Budgets: user_id + month compound index created")
    
    # Goals collection indexes
    db.goals.create_index([("user_id", ASCENDING), ("status", ASCENDING)])
    db.goals.create_index([("user_id", ASCENDING), ("target_date", ASCENDING)])
    print("✓ Goals: user_id, status, target_date indexes created")
    
    # Alerts collection indexes
    db.alerts.create_index([("user_id", ASCENDING), ("created_at", DESCENDING)])
    db.alerts.create_index([("user_id", ASCENDING), ("read", ASCENDING)])
    print("✓ Alerts: user_id, created_at, read indexes created")
    
    # FTI Score collection indexes
    db.fti_scores.create_index([("user_id", ASCENDING), ("calculated_at", DESCENDING)])
    print("✓ FTI Scores: user_id + calculated_at index created")
    
    # Alert settings collection indexes
    db.alert_settings.create_index([("user_id", ASCENDING)], unique=True)
    print("✓ Alert Settings: user_id index created")
    
    print("\n✅ All indexes created successfully!")
    print("\nIndex Statistics:")
    
    # Show index stats
    collections = ['users', 'transactions', 'budgets', 'goals', 'alerts', 'fti_scores', 'alert_settings']
    for collection in collections:
        indexes = list(db[collection].list_indexes())
        print(f"  {collection}: {len(indexes)} indexes")
    
    client.close()

if __name__ == "__main__":
    create_indexes()
