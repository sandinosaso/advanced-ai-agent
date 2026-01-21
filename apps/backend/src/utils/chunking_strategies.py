"""
Chunking strategies for Phase 3 RAG implementation

This module implements multiple chunking approaches to demonstrate trade-offs:
1. Fixed-size chunking (baseline)
2. Recursive character splitting (smart boundaries)
3. Semantic chunking (similarity-based grouping)
4. Document-structure chunking (header-based splitting)

Each strategy has different characteristics for precision, recall, and coherence.
"""

import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from langchain_text_splitters import (
    RecursiveCharacterTextSplitter,
    CharacterTextSplitter,
)
from loguru import logger


@dataclass
class Chunk:
    """Represents a text chunk with metadata"""
    text: str
    start_char: int
    end_char: int
    chunk_index: int
    metadata: Dict[str, Any]
    
    def __len__(self) -> int:
        return len(self.text)
    
    def __repr__(self) -> str:
        preview = self.text[:50] + "..." if len(self.text) > 50 else self.text
        return f"Chunk({self.chunk_index}, {len(self.text)} chars, '{preview}')"


class ChunkingStrategy:
    """Base class for chunking strategies"""
    
    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        logger.info(f"Initialized {self.__class__.__name__} (size={chunk_size}, overlap={chunk_overlap})")
    
    def chunk_text(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> List[Chunk]:
        """Override this method in subclasses"""
        raise NotImplementedError
    
    def visualize_chunks(self, chunks: List[Chunk], max_preview: int = 100) -> str:
        """Create visual representation of chunks for debugging"""
        lines = []
        lines.append(f"\n{'='*80}")
        lines.append(f"Chunking Strategy: {self.__class__.__name__}")
        lines.append(f"Total chunks: {len(chunks)}")
        lines.append(f"Config: size={self.chunk_size}, overlap={self.chunk_overlap}")
        lines.append(f"{'='*80}\n")
        
        for chunk in chunks:
            preview = chunk.text[:max_preview].replace('\n', ' ')
            if len(chunk.text) > max_preview:
                preview += "..."
            
            lines.append(f"Chunk {chunk.chunk_index}:")
            lines.append(f"  Length: {len(chunk.text)} chars")
            lines.append(f"  Position: {chunk.start_char}-{chunk.end_char}")
            lines.append(f"  Metadata: {chunk.metadata}")
            lines.append(f"  Preview: {preview}")
            lines.append("")
        
        return "\n".join(lines)


class FixedSizeChunking(ChunkingStrategy):
    """
    Simple fixed-size chunking with overlap
    
    Pros:
    - Predictable chunk sizes
    - Fast and simple
    - Good for uniform content
    
    Cons:
    - Can split sentences/paragraphs awkwardly
    - No semantic awareness
    - May lose context at boundaries
    """
    
    def chunk_text(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> List[Chunk]:
        if metadata is None:
            metadata = {}
        
        chunks = []
        text_length = len(text)
        chunk_index = 0
        start = 0
        
        while start < text_length:
            end = min(start + self.chunk_size, text_length)
            chunk_text = text[start:end]
            
            chunks.append(Chunk(
                text=chunk_text,
                start_char=start,
                end_char=end,
                chunk_index=chunk_index,
                metadata={**metadata, "strategy": "fixed_size"}
            ))
            
            chunk_index += 1
            start += self.chunk_size - self.chunk_overlap
        
        logger.debug(f"Fixed-size chunking created {len(chunks)} chunks from {text_length} chars")
        return chunks


class RecursiveChunking(ChunkingStrategy):
    """
    Recursive character splitting that respects natural boundaries
    
    Uses hierarchy of separators to split at natural boundaries:
    1. Double newlines (paragraphs)
    2. Single newlines (sentences in some formats)
    3. Periods (sentence boundaries)
    4. Spaces (word boundaries)
    5. Characters (as last resort)
    
    Pros:
    - Respects natural text structure
    - Better semantic coherence
    - Configurable separator hierarchy
    
    Cons:
    - Variable chunk sizes
    - May miss document-specific structure
    - Slightly slower than fixed-size
    """
    
    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50, 
                 separators: Optional[List[str]] = None):
        super().__init__(chunk_size, chunk_overlap)
        
        # Default separators in order of preference
        if separators is None:
            separators = [
                "\n\n",  # Paragraph breaks
                "\n",    # Line breaks
                ". ",    # Sentence boundaries
                " ",     # Word boundaries
                "",      # Character level (last resort)
            ]
        
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=separators,
            is_separator_regex=False
        )
    
    def chunk_text(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> List[Chunk]:
        if metadata is None:
            metadata = {}
        
        # Use LangChain's splitter
        text_chunks = self.splitter.split_text(text)
        
        # Convert to our Chunk objects with position tracking
        chunks = []
        current_pos = 0
        
        for i, chunk_text in enumerate(text_chunks):
            # Find chunk position in original text
            start_char = text.find(chunk_text, current_pos)
            if start_char == -1:
                # Chunk not found exactly (maybe due to whitespace normalization)
                start_char = current_pos
            end_char = start_char + len(chunk_text)
            
            chunks.append(Chunk(
                text=chunk_text,
                start_char=start_char,
                end_char=end_char,
                chunk_index=i,
                metadata={**metadata, "strategy": "recursive"}
            ))
            
            current_pos = end_char
        
        logger.debug(f"Recursive chunking created {len(chunks)} chunks")
        return chunks


class DocumentStructureChunking(ChunkingStrategy):
    """
    Splits based on document structure (headers, sections)
    
    Detects markdown-style headers and section boundaries to create
    semantically meaningful chunks that respect document hierarchy.
    
    Pros:
    - Preserves logical document structure
    - Chunks are semantically complete sections
    - Excellent for documentation, handbooks, policies
    
    Cons:
    - Only works well with structured documents
    - Variable chunk sizes (some sections may be very large)
    - Requires document format conventions
    """
    
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 100,
                 max_section_size: Optional[int] = None):
        super().__init__(chunk_size, chunk_overlap)
        self.max_section_size = max_section_size or (chunk_size * 3)
        
        # Patterns for detecting structure
        self.header_patterns = [
            (r'^#{1,6}\s+(.+)$', 'markdown_header'),  # # Header
            (r'^Section\s+\d+[:\.]?\s*(.+)$', 'numbered_section'),  # Section 1: Title
            (r'^[A-Z\s]{3,}:?\s*$', 'all_caps_header'),  # ALL CAPS HEADER
            (r'^[IVX]+\.\s+(.+)$', 'roman_numeral'),  # I. Header
            (r'^\d+\.\s+(.+)$', 'numbered_header'),  # 1. Header
        ]
    
    def _find_headers(self, text: str) -> List[Tuple[int, int, str, str]]:
        """Find all headers in text, return (start, end, title, type)"""
        headers = []
        
        for line_start, line in enumerate(text.split('\n')):
            for pattern, header_type in self.header_patterns:
                match = re.match(pattern, line.strip(), re.MULTILINE | re.IGNORECASE)
                if match:
                    # Calculate character position
                    char_pos = text[:text.find(line)].count('\n')
                    title = match.group(1) if match.groups() else line.strip()
                    headers.append((
                        char_pos,
                        char_pos + len(line),
                        title.strip(),
                        header_type
                    ))
                    break
        
        return sorted(headers, key=lambda x: x[0])
    
    def chunk_text(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> List[Chunk]:
        if metadata is None:
            metadata = {}
        
        # Find all structural headers
        headers = self._find_headers(text)
        
        if not headers:
            # No structure found, fall back to recursive chunking
            logger.warning("No document structure found, falling back to recursive chunking")
            fallback = RecursiveChunking(self.chunk_size, self.chunk_overlap)
            return fallback.chunk_text(text, metadata)
        
        chunks = []
        chunk_index = 0
        
        # Create chunks based on sections
        for i, (start, end, title, header_type) in enumerate(headers):
            # Determine section boundaries
            section_start = start
            if i < len(headers) - 1:
                section_end = headers[i + 1][0]
            else:
                section_end = len(text)
            
            section_text = text[section_start:section_end].strip()
            
            # Skip empty sections
            if not section_text or len(section_text) < 10:
                continue
            
            # If section is too large, split it further
            if len(section_text) > self.max_section_size:
                # Use recursive splitting for large sections
                subsplitter = RecursiveChunking(self.chunk_size, self.chunk_overlap)
                subchunks = subsplitter.chunk_text(section_text)
                
                for subchunk in subchunks:
                    chunks.append(Chunk(
                        text=subchunk.text,
                        start_char=section_start + subchunk.start_char,
                        end_char=section_start + subchunk.end_char,
                        chunk_index=chunk_index,
                        metadata={
                            **metadata,
                            "strategy": "document_structure",
                            "section_title": title,
                            "header_type": header_type,
                            "subsection": subchunk.chunk_index
                        }
                    ))
                    chunk_index += 1
            else:
                # Section fits in one chunk
                chunks.append(Chunk(
                    text=section_text,
                    start_char=section_start,
                    end_char=section_end,
                    chunk_index=chunk_index,
                    metadata={
                        **metadata,
                        "strategy": "document_structure",
                        "section_title": title,
                        "header_type": header_type
                    }
                ))
                chunk_index += 1
        
        logger.debug(f"Document structure chunking created {len(chunks)} chunks from {len(headers)} sections")
        return chunks


class SemanticChunking(ChunkingStrategy):
    """
    Experimental: Splits based on semantic similarity
    
    Groups sentences that are semantically similar together.
    Requires embeddings, so more expensive than other strategies.
    
    Note: This is a simplified version. Production implementation
    would use sentence embeddings and similarity thresholds.
    
    Pros:
    - Chunks are semantically coherent
    - Excellent for question-answering
    - Adapts to content
    
    Cons:
    - Expensive (requires embeddings)
    - Slower processing
    - Variable chunk sizes
    - Requires careful tuning
    """
    
    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50,
                 similarity_threshold: float = 0.7):
        super().__init__(chunk_size, chunk_overlap)
        self.similarity_threshold = similarity_threshold
    
    def _split_sentences(self, text: str) -> List[str]:
        """Simple sentence splitter"""
        # Basic sentence splitting (production would use spaCy or NLTK)
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def chunk_text(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> List[Chunk]:
        if metadata is None:
            metadata = {}
        
        # For now, fall back to recursive chunking
        # Real semantic chunking would require embeddings
        logger.warning("Semantic chunking not fully implemented, using recursive chunking")
        fallback = RecursiveChunking(self.chunk_size, self.chunk_overlap)
        chunks = fallback.chunk_text(text, metadata)
        
        # Update metadata to indicate this would be semantic
        for chunk in chunks:
            chunk.metadata["strategy"] = "semantic_fallback"
        
        return chunks


def compare_chunking_strategies(
    text: str,
    strategies: Optional[List[ChunkingStrategy]] = None
) -> Dict[str, List[Chunk]]:
    """
    Compare multiple chunking strategies on the same text
    
    Returns dictionary with strategy name as key and chunks as value
    """
    if strategies is None:
        # Default comparison set
        strategies = [
            FixedSizeChunking(chunk_size=500, chunk_overlap=50),
            RecursiveChunking(chunk_size=500, chunk_overlap=50),
            DocumentStructureChunking(chunk_size=1000, chunk_overlap=100),
        ]
    
    results = {}
    
    for strategy in strategies:
        strategy_name = strategy.__class__.__name__
        chunks = strategy.chunk_text(text)
        results[strategy_name] = chunks
        
        # Log statistics
        chunk_sizes = [len(c.text) for c in chunks]
        avg_size = sum(chunk_sizes) / len(chunk_sizes) if chunk_sizes else 0
        min_size = min(chunk_sizes) if chunk_sizes else 0
        max_size = max(chunk_sizes) if chunk_sizes else 0
        
        logger.info(f"{strategy_name}: {len(chunks)} chunks, "
                   f"avg={avg_size:.0f}, min={min_size}, max={max_size}")
    
    return results


def chunk_document(
    document_text: str,
    document_type: str,
    strategy: Optional[ChunkingStrategy] = None
) -> List[Chunk]:
    """
    Chunk a document using appropriate strategy based on type
    
    Args:
        document_text: The full document text
        document_type: Type hint (handbook, receipt, work_log, compliance)
        strategy: Optional explicit strategy (otherwise auto-selected)
    
    Returns:
        List of chunks with appropriate metadata
    """
    metadata = {"document_type": document_type}
    
    # Auto-select strategy if not provided
    if strategy is None:
        if document_type in ("handbook", "compliance", "policy"):
            # Structured documents benefit from structure-aware chunking
            strategy = DocumentStructureChunking(chunk_size=1000, chunk_overlap=100)
        elif document_type == "receipt":
            # Receipts are short, use simple chunking
            strategy = FixedSizeChunking(chunk_size=300, chunk_overlap=30)
        elif document_type == "work_log":
            # Work logs benefit from recursive splitting
            strategy = RecursiveChunking(chunk_size=600, chunk_overlap=60)
        else:
            # Default to recursive
            strategy = RecursiveChunking(chunk_size=500, chunk_overlap=50)
    
    logger.info(f"Chunking {document_type} document ({len(document_text)} chars) "
                f"using {strategy.__class__.__name__}")
    
    return strategy.chunk_text(document_text, metadata)


if __name__ == "__main__":
    # Quick test with sample text
    from src.services.mock_documents import COMPANY_HANDBOOK
    
    print("Testing chunking strategies on Company Handbook...")
    print(f"Document length: {len(COMPANY_HANDBOOK)} characters\n")
    
    # Test each strategy
    results = compare_chunking_strategies(COMPANY_HANDBOOK)
    
    # Visualize first strategy
    for strategy_name, chunks in results.items():
        print(f"\n{strategy_name}:")
        print(f"  Total chunks: {len(chunks)}")
        if chunks:
            print(f"  First chunk: {chunks[0].text[:100]}...")
            print(f"  Last chunk: {chunks[-1].text[:100]}...")
