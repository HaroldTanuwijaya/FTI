"""
Performance monitoring and optimization utilities
"""

import time
from functools import wraps
from flask import g, request
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def log_performance(f):
    """Decorator to log API endpoint performance"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        start_time = time.time()
        result = f(*args, **kwargs)
        end_time = time.time()
        
        duration = (end_time - start_time) * 1000  # Convert to milliseconds
        
        if duration > 1000:  # Log slow requests (>1 second)
            logger.warning(f"SLOW REQUEST: {request.path} took {duration:.2f}ms")
        else:
            logger.info(f"{request.path} completed in {duration:.2f}ms")
        
        return result
    return decorated_function

def get_query_stats(mongo_db):
    """Get MongoDB query statistics"""
    stats = {}
    
    collections = ['users', 'transactions', 'budgets', 'goals', 'alerts']
    
    for collection in collections:
        coll_stats = mongo_db.command("collStats", collection)
        stats[collection] = {
            "count": coll_stats.get("count", 0),
            "size": coll_stats.get("size", 0),
            "avgObjSize": coll_stats.get("avgObjSize", 0),
            "indexes": len(list(mongo_db[collection].list_indexes()))
        }
    
    return stats

def optimize_query_plan(collection, query):
    """Analyze and suggest optimizations for a query"""
    explain = collection.find(query).explain()
    
    execution_stats = explain.get("executionStats", {})
    
    return {
        "executionTimeMillis": execution_stats.get("executionTimeMillis", 0),
        "totalDocsExamined": execution_stats.get("totalDocsExamined", 0),
        "totalKeysExamined": execution_stats.get("totalKeysExamined", 0),
        "nReturned": execution_stats.get("nReturned", 0)
    }
