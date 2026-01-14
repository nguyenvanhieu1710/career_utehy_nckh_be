"""
MongoDB connection and configuration
"""
import os
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from beanie import init_beanie
import logging

logger = logging.getLogger(__name__)

class MongoDB:
    client: Optional[AsyncIOMotorClient] = None
    database: Optional[AsyncIOMotorDatabase] = None

# Global MongoDB instance
mongodb = MongoDB()

async def connect_to_mongo():
    """Create database connection"""
    try:
        # Get MongoDB configuration from environment
        mongo_host = os.getenv("MONGO_HOST", "")
        mongo_port = int(os.getenv("MONGO_PORT", ""))
        mongo_user = os.getenv("MONGO_USER", "")
        mongo_password = os.getenv("MONGO_PASSWORD", "")
        mongo_database = os.getenv("MONGO_DATABASE", "")
        
        # Build connection string
        if mongo_user and mongo_password:
            connection_string = f"mongodb://{mongo_user}:{mongo_password}@{mongo_host}:{mongo_port}/{mongo_database}?authSource=admin"
        else:
            connection_string = f"mongodb://{mongo_host}:{mongo_port}/{mongo_database}"
        
        # Create client
        mongodb.client = AsyncIOMotorClient(connection_string)
        mongodb.database = mongodb.client[mongo_database]
        
        # Test connection
        await mongodb.client.admin.command('ping')
        # logger.info("✅ MongoDB connection successful")
        
        # Initialize Beanie with document models
        from app.models.mongo.job import Job
        from app.models.mongo.company import Company
        
        await init_beanie(
            database=mongodb.database,
            document_models=[
                Job,
                Company,
            ]
        )
        
    except Exception as e:
        logger.error(f"❌ MongoDB connection failed: {e}")
        raise e

async def close_mongo_connection():
    """Close database connection"""
    if mongodb.client:
        mongodb.client.close()
        logger.info("MongoDB connection closed")

def get_database() -> AsyncIOMotorDatabase:
    """Get MongoDB database instance"""
    if mongodb.database is None:
        raise RuntimeError("MongoDB not initialized. Call connect_to_mongo() first.")
    return mongodb.database

# Health check function
async def mongodb_health_check() -> bool:
    """Check if MongoDB is healthy"""
    try:
        if mongodb.client:
            await mongodb.client.admin.command('ping')
            return True
        return False
    except Exception:
        return False