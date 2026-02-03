"""
Database session management and configuration - MySQL.
"""

import os
from sqlalchemy import create_engine, text, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import Pool
from contextlib import contextmanager
from typing import Generator
from pathlib import Path

from src.models.domain import Base
from src.utils.logging import logger
from src.config.settings import DatabaseConfig


class Database:
    """
    MySQL database connection manager
    
    Handles connection pooling, session management, and configuration.
    """
    
    def __init__(self, config: DatabaseConfig = None):
        """
        Initialize database connection
        
        Args:
            config: Database configuration (defaults to env vars)
        """
        self.config = config or DatabaseConfig()
        
        # Build MySQL connection string
        connection_string = self.config.get_connection_string()
        
        logger.info(f"Connecting to MySQL: {self.config.database} @ {self.config.host}:{self.config.port}")
        
        # Create engine with connection pooling
        self.engine = create_engine(
            connection_string,
            pool_pre_ping=True,      # Verify connections before using
            pool_recycle=3600,       # Recycle connections after 1 hour
            pool_size=5,             # Connection pool size
            max_overflow=10,         # Max overflow connections
            echo=False               # Set to True for SQL query logging
        )
        
        # Session factory
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
        )
        
        # Register event listener to set session variables on connection checkout
        self._register_session_variable_listener()
        
        # Test connection
        self._test_connection()
    
    def _register_session_variable_listener(self):
        """
        Register SQLAlchemy event listener to set MySQL session variables.
        
        This sets variables like @aesKey on every connection so that secure views
        can decrypt data using AES_DECRYPT(@encryptedField, @aesKey).
        
        Similar to the Node.js approach:
        SET @aesKey = 'encryption_key';
        SET @customerIds = NULL;
        SET @workOrderIds = NULL;
        SET @serviceLocationIds = NULL;
        """
        @event.listens_for(self.engine, "connect")
        def set_session_variables(dbapi_conn, connection_record):
            """Set MySQL session variables when connection is established"""
            cursor = dbapi_conn.cursor()
            try:
                # Get encryption key from environment
                encrypt_key = os.getenv("DB_ENCRYPT_KEY", "")
                
                if encrypt_key:
                    # Set the encryption key for AES_DECRYPT in views
                    cursor.execute(f"SET @aesKey = '{encrypt_key}'")
                    logger.info("✅ Set @aesKey session variable for secure views")
                else:
                    logger.warning("⚠️  DB_ENCRYPT_KEY not set - secure views will return NULL for encrypted fields")
                
                # Initialize other session variables to NULL (can be set later if needed)
                cursor.execute("SET @customerIds = NULL")
                cursor.execute("SET @workOrderIds = NULL")
                cursor.execute("SET @serviceLocationIds = NULL")
                logger.info("✅ Initialized session variables (@customerIds, @workOrderIds, @serviceLocationIds)")
                
            except Exception as e:
                logger.error(f"❌ Failed to set session variables: {e}")
            finally:
                cursor.close()
        
        logger.info("Registered MySQL session variable listener for secure views")
    
    def _test_connection(self):
        """Test database connection on initialization"""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("SELECT DATABASE(), VERSION()"))
                db_name, version = result.fetchone()
                logger.success(f"✅ Connected to MySQL: {db_name} (v{version})")
        except Exception as e:
            logger.error(f"❌ Failed to connect to MySQL: {e}")
            raise
    
    def get_session(self) -> Session:
        """
        Get a new database session
        
        Returns:
            SQLAlchemy Session
        """
        return self.SessionLocal()
    
    @contextmanager
    def session_scope(self) -> Generator[Session, None, None]:
        """
        Provide a transactional scope around a series of operations
        
        Usage:
            with db.session_scope() as session:
                session.query(User).all()
        """
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            session.close()


# Global database instance (lazy initialization)
_db_instance = None


def get_database() -> Database:
    """Get or create global database instance"""
    global _db_instance
    if _db_instance is None:
        _db_instance = Database()
    return _db_instance


@contextmanager
def get_db() -> Generator[Session, None, None]:
    """
    Get database session with automatic cleanup (backwards compatible)
    
    Usage:
        with get_db() as db:
            users = db.query(User).all()
    """
    database = get_database()
    session = database.get_session()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Database error: {e}")
        raise
    finally:
        session.close()


def get_db_session() -> Generator[Session, None, None]:
    """
    Get database session for FastAPI dependency injection
    
    Usage:
        @app.get("/users")
        def get_users(db: Session = Depends(get_db_session)):
            return db.query(User).all()
    """
    database = get_database()
    session = database.get_session()
    try:
        yield session
    finally:
        session.close()
