"""
Demo script for Phase 2: SQL Query Agent
Tests natural language database queries using LangChain SQL agent.
"""

from src.agents import SQLQueryAgent
from src.utils.logger import logger


def demo_schema_info():
    """Show database schema information."""
    logger.info("=" * 80)
    logger.info("PHASE 2 DEMO: SQL Query Agent")
    logger.info("=" * 80)
    
    agent = SQLQueryAgent()
    
    logger.info("\n📊 Database Schema:")
    print("\n" + agent.get_schema_info()[:500] + "...\n")


def demo_simple_queries():
    """Run simple example queries."""
    agent = SQLQueryAgent()
    
    # Simple queries to test
    test_queries = [
        "How many technicians are in the database?",
        "How many jobs are in progress?",
        "What is the total number of work logs?"
    ]
    
    logger.info("\n🔍 Running Simple Test Queries:")
    logger.info("=" * 80)
    
    for i, question in enumerate(test_queries, 1):
        logger.info(f"\n[Query {i}] {question}")
        print("-" * 80)
        
        try:
            answer = agent.query(question)
            print(f"\n✅ Answer: {answer}\n")
        except Exception as e:
            logger.error(f"Failed: {e}")


def demo_complex_queries():
    """Run more complex analytical queries."""
    agent = SQLQueryAgent()
    
    complex_queries = [
        "Which jobs are over budget? Show customer name and budget vs actual expenses.",
        "Which technicians logged more than their daily hour limit?",
        "What are the most common skills among technicians?"
    ]
    
    logger.info("\n🎯 Running Complex Analytical Queries:")
    logger.info("=" * 80)
    
    for i, question in enumerate(complex_queries, 1):
        logger.info(f"\n[Query {i}] {question}")
        print("-" * 80)
        
        try:
            answer = agent.query(question)
            print(f"\n✅ Answer: {answer}\n")
        except Exception as e:
            logger.error(f"Failed: {e}")


def interactive_mode():
    """Interactive query mode."""
    agent = SQLQueryAgent()
    
    logger.info("\n💬 Interactive Query Mode")
    logger.info("=" * 80)
    logger.info("Ask questions about the database (or 'quit' to exit)")
    
    print("\n" + "=" * 80 + "\n")
    
    while True:
        try:
            question = input("Your question: ").strip()
            
            if question.lower() in ['quit', 'exit', 'q']:
                logger.info("Exiting interactive mode")
                break
            
            if not question:
                continue
            
            print("\n" + "-" * 80)
            answer = agent.query(question)
            print(f"\n✅ Answer: {answer}\n")
            print("-" * 80 + "\n")
            
        except KeyboardInterrupt:
            logger.info("\nExiting interactive mode")
            break
        except Exception as e:
            logger.error(f"Error: {e}")


def main():
    """Run Phase 2 demo."""
    logger.info("Starting Phase 2 Demo: SQL Query Agent\n")
    
    # 1. Show schema
    demo_schema_info()
    
    # 2. Run simple queries
    demo_simple_queries()
    
    # 3. Run complex queries
    demo_complex_queries()
    
    # 4. Interactive mode (optional)
    print("\n" + "=" * 80)
    response = input("\nWould you like to try interactive mode? (y/n): ").strip().lower()
    if response == 'y':
        interactive_mode()
    
    logger.success("\n✅ Phase 2 Demo Complete!")


if __name__ == "__main__":
    main()
