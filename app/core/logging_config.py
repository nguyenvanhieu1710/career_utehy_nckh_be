import logging
import sys
import warnings
import os


def setup_logging():
    """Configure logging for the application"""
    
    # Determine log level from environment (default: INFO for dev)
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    
    # Root logger configuration
    logging.basicConfig(
        level=getattr(logging, log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # SQLAlchemy - Tắt query logs, chỉ giữ warnings/errors
    logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
    logging.getLogger('sqlalchemy.pool').setLevel(logging.WARNING)
    logging.getLogger('sqlalchemy.dialects').setLevel(logging.WARNING)
    logging.getLogger('sqlalchemy.orm').setLevel(logging.WARNING)
    
    # Tắt Pydantic warnings (orm_mode, schema_extra deprecated)
    warnings.filterwarnings('ignore', category=UserWarning, module='pydantic')
    
    # Uvicorn - Giảm verbosity, chỉ giữ thông tin quan trọng
    logging.getLogger('uvicorn').setLevel(logging.INFO)
    logging.getLogger('uvicorn.access').setLevel(logging.INFO)
    logging.getLogger('uvicorn.error').setLevel(logging.INFO)
    
    # FastAPI - INFO level
    logging.getLogger('fastapi').setLevel(logging.INFO)
    
    # App logs - INFO level
    logging.getLogger('app').setLevel(logging.INFO)
    
    # Log startup message
    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured - Level: {log_level}")
