"""
Initialize database with mock data.
Run this script to populate the database with realistic test data.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.services.mock_data import populate_database
from src.utils.logger import logger


def main():
    """Main entry point for database initialization."""
    logger.info("="  * 60)
    logger.info("Field Service Intelligence Agent - Database Setup")
    logger.info("=" * 60)
    
    try:
        # Populate with mock data
        populate_database(
            num_technicians=10,
            num_jobs=50,
            num_work_logs=200,
            num_expenses=100,
            reset=True  # Set to False if you want to keep existing data
        )
        
        logger.info("")
        logger.success("✅ Database initialization complete!")
        logger.info("You can now:")
        logger.info("  1. Query the database with SQL tools")
        logger.info("  2. Start building the RAG agent")
        logger.info("  3. Test with realistic data")
        
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        import traceback
        logger.debug(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()
