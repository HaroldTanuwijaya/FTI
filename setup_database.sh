#!/bin/bash

# MongoDB Database Setup Script for FTI

echo "🗄️  FTI Database Setup"
echo "====================="
echo ""

# Check if MongoDB is running
echo "📊 Checking MongoDB connection..."
if command -v mongosh &> /dev/null; then
    if ! mongosh --eval "db.version()" > /dev/null 2>&1; then
        echo "❌ MongoDB is not running. Please start MongoDB first."
        echo ""
        echo "To start MongoDB:"
        echo "  • macOS: brew services start mongodb-community"
        echo "  • Linux: sudo systemctl start mongod"
        echo "  • Windows: net start MongoDB"
        exit 1
    fi
    echo "✅ MongoDB is running"
elif command -v mongo &> /dev/null; then
    if ! mongo --eval "db.version()" > /dev/null 2>&1; then
        echo "❌ MongoDB is not running. Please start MongoDB first."
        exit 1
    fi
    echo "✅ MongoDB is running"
else
    echo "⚠️  MongoDB CLI not found. Assuming MongoDB is running..."
fi

echo ""

# Install Python dependencies if needed
if ! python -c "import pymongo" 2>/dev/null; then
    echo "📦 Installing Python dependencies..."
    pip install pymongo bcrypt python-dotenv
    echo "✅ Dependencies installed"
    echo ""
fi

# Initialize database collections
echo "🔧 Initializing database collections..."
python backend/init_db.py

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Database initialization complete!"
    echo ""
    
    # Ask if user wants sample data
    read -p "📝 Do you want to generate sample data for testing? (y/n): " -n 1 -r
    echo ""
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo ""
        echo "🎲 Generating sample data..."
        python backend/seed_data.py
        echo ""
        echo "✅ Sample data created!"
        echo ""
        echo "🔐 Test Login Credentials:"
        echo "   Email: demo@fti.com"
        echo "   Password: password123"
    fi
    
    echo ""
    echo "🎉 Database setup complete!"
    echo ""
    echo "Next steps:"
    echo "1. Start the application: python backend/app.py"
    echo "2. Visit: http://localhost:5000"
    echo "3. Login with demo credentials (if sample data was created)"
else
    echo ""
    echo "❌ Database initialization failed!"
    echo "Please check the error messages above."
    exit 1
fi
