#!/usr/bin/env python3
"""
Quick test to verify classification improvements work correctly
"""

# Test cases that should be classified as SQL
sql_test_cases = [
    "What are the asset types available?",
    "List the asset types available in the system",
    "What inspection templates exist?",
    "Show me all expense types",
    "What service locations do we have?",
    "List all crew names",
    "How many active employees are there?",
    "What work order statuses are configured?",
]

# Test cases that should be classified as RAG
rag_test_cases = [
    "How do I create an asset?",
    "How do I add a new asset type?",
    "What are the steps to create an inspection?",
    "How do I assign a crew to a work order?",
]

# Test cases that should be classified as GENERAL
general_test_cases = [
    "What is machine learning?",
    "Explain quantum computing",
    "What's the weather today?",
]

print("=" * 80)
print("CLASSIFICATION TEST CASES")
print("=" * 80)

print("\n✅ Should be classified as SQL (business data queries):")
for i, question in enumerate(sql_test_cases, 1):
    print(f"  {i}. {question}")

print("\n📚 Should be classified as RAG (system usage questions):")
for i, question in enumerate(rag_test_cases, 1):
    print(f"  {i}. {question}")

print("\n💭 Should be classified as GENERAL (non-business questions):")
for i, question in enumerate(general_test_cases, 1):
    print(f"  {i}. {question}")

print("\n" + "=" * 80)
print("To test: Start the API and try these questions in the chat interface")
print("=" * 80)
