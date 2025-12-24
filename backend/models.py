from datetime import datetime
from bson import ObjectId

class User:
    """User model for MongoDB"""
    
    @staticmethod
    def create_user(email, password_hash, name):
        return {
            "_id": ObjectId(),
            "email": email,
            "password_hash": password_hash,
            "name": name,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }

class Transaction:
    """Transaction model for MongoDB"""
    
    @staticmethod
    def create_transaction(user_id, amount, type, description, category="Uncategorized"):
        return {
            "_id": ObjectId(),
            "user_id": ObjectId(user_id),
            "amount": float(amount),
            "type": type,  # 'income' or 'expense'
            "description": description,
            "category": category,
            "date": datetime.utcnow(),
            "created_at": datetime.utcnow()
        }

class Budget:
    """Budget model for MongoDB"""
    
    @staticmethod
    def create_budget(user_id, month, total_amount, categories=None):
        return {
            "_id": ObjectId(),
            "user_id": ObjectId(user_id),
            "month": month,  # Format: "YYYY-MM"
            "total_amount": float(total_amount),
            "categories": categories or {},
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }

class FTIScore:
    """FTI Score model for MongoDB"""
    
    @staticmethod
    def create_score_record(user_id, score, components):
        return {
            "_id": ObjectId(),
            "user_id": ObjectId(user_id),
            "score": int(score),
            "components": {
                "cash_flow": components.get("cash_flow", 0),
                "spending_control": components.get("spending_control", 0),
                "savings_discipline": components.get("savings_discipline", 0),
                "stability": components.get("stability", 0),
                "debt": components.get("debt", 0),
                "goal_progress": components.get("goal_progress", 0)
            },
            "calculated_at": datetime.utcnow()
        }

class Goal:
    """Financial Goal model for MongoDB"""
    
    @staticmethod
    def create_goal(user_id, name, target_amount, current_amount, target_date):
        return {
            "_id": ObjectId(),
            "user_id": ObjectId(user_id),
            "name": name,
            "target_amount": float(target_amount),
            "current_amount": float(current_amount),
            "target_date": target_date,
            "status": "active",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }

class Alert:
    """Alert/Notification model for MongoDB"""
    
    @staticmethod
    def create_alert(user_id, title, message, alert_type="info"):
        return {
            "_id": ObjectId(),
            "user_id": ObjectId(user_id),
            "title": title,
            "message": message,
            "type": alert_type,  # info, warning, danger, success
            "read": False,
            "created_at": datetime.utcnow()
        }

class CategoryRule:
    """Auto-categorization rule model for MongoDB"""
    
    @staticmethod
    def create_rule(user_id, keywords, category, confidence=1.0):
        return {
            "_id": ObjectId(),
            "user_id": ObjectId(user_id),
            "keywords": keywords,  # List of keywords
            "category": category,
            "confidence": float(confidence),
            "created_at": datetime.utcnow()
        }
