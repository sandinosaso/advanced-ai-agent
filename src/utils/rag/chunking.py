"""
Text chunking utilities for processing long documents.
Used for splitting job descriptions before embedding.
"""

from typing import List

from langchain_text_splitters import RecursiveCharacterTextSplitter


def chunk_text(
    text: str,
    chunk_size: int = 500,
    chunk_overlap: int = 50,
    separators: List[str] = ["\n\n", "\n", ". ", " ", ""],
) -> List[str]:
    """
    Split text into chunks for embedding.
    
    Args:
        text: Text to split
        chunk_size: Maximum size of each chunk
        chunk_overlap: Number of characters to overlap between chunks
        separators: List of separators to use for splitting (in priority order)
        
    Returns:
        List of text chunks
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=separators,
        length_function=len,
    )
    
    chunks = splitter.split_text(text)
    return chunks


if __name__ == "__main__":
    # Test chunking
    sample_text = """
    We are looking for a Senior Python Developer with 5+ years of experience.
    
    Requirements:
    - Strong Python skills
    - Experience with FastAPI or Django
    - Knowledge of SQL databases
    - Docker and Kubernetes experience
    
    Responsibilities:
    - Design and implement backend services
    - Work with cross-functional teams
    - Mentor junior developers
    
    Benefits:
    - Competitive salary
    - Remote work options
    - Health insurance
    """
    
    chunks = chunk_text(sample_text, chunk_size=100, chunk_overlap=20)
    print(f"Split into {len(chunks)} chunks:")
    for i, chunk in enumerate(chunks, 1):
        print(f"\nChunk {i}:")
        print(chunk)
