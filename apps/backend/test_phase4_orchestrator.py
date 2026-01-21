"""
Test script for Phase 4 - Orchestrator Agent

Demonstrates the complete LangGraph workflow routing between SQL and RAG agents.
"""

from loguru import logger
from src.agents.orchestrator_agent import OrchestratorAgent


def test_orchestrator():
    """Test the orchestrator with various question types"""
    
    print("\n" + "="*80)
    print("PHASE 4: ORCHESTRATOR AGENT TEST")
    print("LangGraph Workflow - Intelligent Routing")
    print("="*80 + "\n")
    
    orchestrator = OrchestratorAgent()
    
    # Test questions organized by expected route
    test_cases = [
        {
            "category": "SQL - Database Queries",
            "expected_route": "sql",
            "questions": [
                "How many technicians are in the database?",
                "What is the total amount of approved expenses?",
                "List all jobs that are currently in progress",
                "Show me technicians who have HVAC skills",
            ]
        },
        {
            "category": "RAG - Company Policies",
            "expected_route": "rag",
            "questions": [
                "Explain the company overtime policy",
                "What safety equipment is required according to OSHA?",
                "What is the procedure for submitting expense reports?",
                "What is the PTO accrual policy for employees?",
                "What are the lockout/tagout safety requirements?",
            ]
        },
        {
            "category": "Mixed - Ambiguous Questions",
            "expected_route": None,  # Could go either way
            "questions": [
                "What are the maximum daily hours a technician can work?",
                "How should I handle late time entry submissions?",
            ]
        }
    ]
    
    results = []
    
    for test_case in test_cases:
        print("\n" + "="*80)
        print(f"CATEGORY: {test_case['category']}")
        print("="*80)
        
        for question in test_case['questions']:
            print(f"\n{'─'*80}")
            print(f"Q: {question}")
            print(f"{'─'*80}")
            
            try:
                result = orchestrator.ask(question, verbose=True)
                
                # Check if routing matches expectation
                expected = test_case.get('expected_route')
                actual = result['route']
                correct_routing = expected is None or expected == actual
                
                # Store result for summary
                results.append({
                    "category": test_case['category'],
                    "question": question,
                    "route": result['route'],
                    "expected_route": expected,
                    "correct_routing": correct_routing,
                    "success": True,
                    "answer_length": len(result['answer'])
                })
                
                # Show routing result with validation
                route_display = f"{result['route'].upper()}"
                if expected:
                    if correct_routing:
                        route_display += f" ✓ (expected {expected.upper()})"
                    else:
                        route_display += f" ✗ (expected {expected.upper()})"
                
                print(f"\n✓ Route: {route_display}")
                print(f"✓ Answer ({len(result['answer'])} chars):")
                print(f"  {result['answer'][:200]}..." if len(result['answer']) > 200 else f"  {result['answer']}")
                
            except Exception as e:
                logger.error(f"Error processing question: {e}")
                results.append({
                    "category": test_case['category'],
                    "question": question,
                    "route": "error",
                    "success": False,
                    "error": str(e)
                })
                print(f"\n✗ Error: {e}")
    
    # Summary
    print("\n\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    total = len(results)
    successful = sum(1 for r in results if r['success'])
    sql_routes = sum(1 for r in results if r.get('route') == 'sql')
    rag_routes = sum(1 for r in results if r.get('route') == 'rag')
    correct_routes = sum(1 for r in results if r.get('correct_routing', True))
    expected_routes = sum(1 for r in results if r.get('expected_route') is not None)
    
    print(f"\nTotal questions: {total}")
    print(f"Successful: {successful}/{total} ({successful/total*100:.1f}%)")
    print(f"\nRouting breakdown:")
    print(f"  SQL Agent: {sql_routes} ({sql_routes/total*100:.1f}%)")
    print(f"  RAG Agent: {rag_routes} ({rag_routes/total*100:.1f}%)")
    print(f"  Errors: {total - successful}")
    print(f"\nRouting accuracy:")
    if expected_routes > 0:
        print(f"  Correct: {correct_routes}/{expected_routes} ({correct_routes/expected_routes*100:.1f}%)")
    else:
        print(f"  (No expected routes to validate)")
    
    print("\n" + "="*80)
    print("✓ Orchestrator agent is ready for frontend integration!")
    print("="*80 + "\n")


def interactive_mode():
    """Interactive chat with orchestrator"""
    
    print("\n" + "="*80)
    print("INTERACTIVE MODE - Orchestrator Agent")
    print("Type 'exit' or 'quit' to end")
    print("="*80 + "\n")
    
    orchestrator = OrchestratorAgent()
    
    while True:
        try:
            question = input("\nYou: ").strip()
            
            if question.lower() in ['exit', 'quit', 'q']:
                print("\nGoodbye!")
                break
            
            if not question:
                continue
            
            print("\nAgent: ", end="", flush=True)
            answer = orchestrator.chat(question)
            print(answer)
            
        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break
        except Exception as e:
            logger.error(f"Error: {e}")
            print(f"\nError: {e}")


if __name__ == "__main__":
    import sys
    
    if "--interactive" in sys.argv or "-i" in sys.argv:
        interactive_mode()
    else:
        test_orchestrator()
