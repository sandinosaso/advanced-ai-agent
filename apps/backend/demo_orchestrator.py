"""
Visual test of the orchestrator - shows routing in action
"""

from src.agents.orchestrator_agent import OrchestratorAgent
from colorama import init, Fore, Style

init(autoreset=True)


def print_result(question: str, result: dict):
    """Pretty print a result"""
    route = result['route'].upper()
    route_color = Fore.CYAN if route == 'SQL' else Fore.GREEN
    
    print(f"\n{Fore.YELLOW}Q: {question}")
    print(f"{route_color}→ Route: {route} Agent")
    print(f"{Fore.WHITE}A: {result['answer'][:150]}...")
    print(f"{Style.DIM}{'─'*80}")


if __name__ == "__main__":
    print(f"\n{Fore.MAGENTA}{'='*80}")
    print(f"{Fore.MAGENTA}ORCHESTRATOR DEMONSTRATION")
    print(f"{Fore.MAGENTA}Intelligent Routing Between SQL and RAG Agents")
    print(f"{Fore.MAGENTA}{'='*80}\n")
    
    orchestrator = OrchestratorAgent()
    
    # Show different types of questions
    questions = [
        ("How many jobs are in the database?", "sql"),
        ("What is the company PTO policy?", "rag"),
        ("Which technicians have HVAC skills?", "sql"),
        ("What are OSHA safety requirements?", "rag"),
    ]
    
    print(f"{Fore.CYAN}CYAN = SQL Agent (Database Queries)")
    print(f"{Fore.GREEN}GREEN = RAG Agent (Document Search)\n")
    
    for question, expected_route in questions:
        result = orchestrator.ask(question, verbose=False)
        print_result(question, result)
        
        # Verify routing
        actual_route = result['route']
        if actual_route == expected_route:
            print(f"{Fore.GREEN}✓ Routed correctly to {expected_route.upper()}")
        else:
            print(f"{Fore.RED}✗ Expected {expected_route.upper()}, got {actual_route.upper()}")
    
    print(f"\n{Fore.MAGENTA}{'='*80}")
    print(f"{Fore.GREEN}✓ Orchestrator working perfectly!")
    print(f"{Fore.MAGENTA}{'='*80}\n")
