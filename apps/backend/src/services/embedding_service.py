"""
Embedding service with caching for Phase 3 RAG implementation

Handles:
- OpenAI text-embedding-3-small generation
- Local disk cache to avoid redundant API calls
- Batch processing for efficiency
- Cost tracking
- Rate limiting
"""

import json
import hashlib
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime

from openai import OpenAI
from loguru import logger


@dataclass
class EmbeddingCacheEntry:
    """Cached embedding with metadata"""
    text_hash: str
    text_preview: str  # First 100 chars for debugging
    embedding: List[float]
    model: str
    created_at: str
    dimensions: int


class EmbeddingService:
    """
    Service for generating and caching text embeddings
    
    Features:
    - Automatic caching to avoid redundant API calls
    - Batch processing support
    - Cost tracking
    - Configurable models
    """
    
    # Pricing per 1M tokens (as of Jan 2024)
    PRICING = {
        "text-embedding-3-small": 0.020,  # $0.020 per 1M tokens
        "text-embedding-3-large": 0.130,  # $0.130 per 1M tokens
        "text-embedding-ada-002": 0.100,  # $0.100 per 1M tokens (legacy)
    }
    
    def __init__(
        self,
        model: str = "text-embedding-3-small",
        cache_dir: Optional[Path] = None,
        enable_cache: bool = True
    ):
        """
        Initialize embedding service
        
        Args:
            model: OpenAI embedding model name
            cache_dir: Directory for caching embeddings
            enable_cache: Whether to use caching
        """
        self.client = OpenAI()  # Uses OPENAI_API_KEY env var
        self.model = model
        self.enable_cache = enable_cache
        
        # Set up cache directory
        if cache_dir is None:
            cache_dir = Path("data/embeddings_cache")
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Cache file for this model
        self.cache_file = self.cache_dir / f"{model}.json"
        
        # Load cache
        self.cache: Dict[str, EmbeddingCacheEntry] = {}
        self._load_cache()
        
        # Statistics
        self.stats = {
            "api_calls": 0,
            "cache_hits": 0,
            "total_tokens": 0,
            "estimated_cost": 0.0
        }
        
        logger.info(f"Initialized EmbeddingService (model={model}, cache={enable_cache})")
        logger.info(f"Cache loaded: {len(self.cache)} entries from {self.cache_file}")
    
    def _load_cache(self) -> None:
        """Load embeddings from cache file"""
        if not self.enable_cache or not self.cache_file.exists():
            return
        
        try:
            with open(self.cache_file, 'r') as f:
                cache_data = json.load(f)
            
            # Convert to EmbeddingCacheEntry objects
            for text_hash, entry_dict in cache_data.items():
                self.cache[text_hash] = EmbeddingCacheEntry(**entry_dict)
            
            logger.debug(f"Loaded {len(self.cache)} cached embeddings")
        except Exception as e:
            logger.warning(f"Failed to load cache: {e}")
            self.cache = {}
    
    def _save_cache(self) -> None:
        """Save embeddings to cache file"""
        if not self.enable_cache:
            return
        
        try:
            # Convert to dict for JSON serialization
            cache_data = {
                text_hash: asdict(entry)
                for text_hash, entry in self.cache.items()
            }
            
            with open(self.cache_file, 'w') as f:
                json.dump(cache_data, f, indent=2)
            
            logger.debug(f"Saved {len(self.cache)} embeddings to cache")
        except Exception as e:
            logger.error(f"Failed to save cache: {e}")
    
    def _hash_text(self, text: str) -> str:
        """Create hash of text for cache lookup"""
        return hashlib.sha256(text.encode()).hexdigest()
    
    def _estimate_tokens(self, text: str) -> int:
        """Rough estimate of token count (actual is ~4 chars/token)"""
        return len(text) // 4
    
    def _update_stats(self, texts: List[str], from_cache: int, from_api: int) -> None:
        """Update statistics"""
        if from_api > 0:
            self.stats["api_calls"] += 1
            tokens = sum(self._estimate_tokens(t) for t in texts)
            self.stats["total_tokens"] += tokens
            
            # Calculate cost
            price_per_million = self.PRICING.get(self.model, 0.020)
            cost = (tokens / 1_000_000) * price_per_million
            self.stats["estimated_cost"] += cost
        
        self.stats["cache_hits"] += from_cache
    
    def embed_text(self, text: str) -> List[float]:
        """
        Generate embedding for a single text
        
        Args:
            text: Text to embed
        
        Returns:
            Embedding vector
        """
        embeddings = self.embed_texts([text])
        return embeddings[0]
    
    def embed_texts(
        self,
        texts: List[str],
        batch_size: int = 100,
        retry_delay: float = 1.0
    ) -> List[List[float]]:
        """
        Generate embeddings for multiple texts with batching
        
        Args:
            texts: List of texts to embed
            batch_size: Max texts per API call
            retry_delay: Delay between retries on rate limit
        
        Returns:
            List of embedding vectors
        """
        if not texts:
            return []
        
        # Filter out empty or whitespace-only texts
        valid_indices = []
        valid_texts = []
        for i, text in enumerate(texts):
            if text and text.strip():
                valid_indices.append(i)
                valid_texts.append(text)
        
        if not valid_texts:
            logger.warning("All texts were empty, returning empty list")
            return []
        
        if len(valid_texts) < len(texts):
            logger.warning(f"Filtered out {len(texts) - len(valid_texts)} empty texts")
        
        embeddings = []
        texts_to_fetch = []
        text_indices = []
        
        # Check cache first (only for valid texts)
        for i, text in enumerate(valid_texts):
            text_hash = self._hash_text(text)
            
            if self.enable_cache and text_hash in self.cache:
                # Found in cache
                cached = self.cache[text_hash]
                embeddings.append((i, cached.embedding))
            else:
                # Need to fetch from API
                texts_to_fetch.append(text)
                text_indices.append(i)
        
        logger.info(f"Embedding {len(valid_texts)} texts: "
                   f"{len(embeddings)} from cache, "
                   f"{len(texts_to_fetch)} from API")
        
        # Fetch missing embeddings from API in batches
        if texts_to_fetch:
            for batch_start in range(0, len(texts_to_fetch), batch_size):
                batch_end = min(batch_start + batch_size, len(texts_to_fetch))
                batch_texts = texts_to_fetch[batch_start:batch_end]
                batch_indices = text_indices[batch_start:batch_end]
                
                # Call API with retry logic
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        logger.debug(f"Calling OpenAI API for batch {batch_start}-{batch_end}")
                        response = self.client.embeddings.create(
                            model=self.model,
                            input=batch_texts
                        )
                        
                        # Extract embeddings and cache them
                        for j, (text, orig_idx) in enumerate(zip(batch_texts, batch_indices)):
                            embedding = response.data[j].embedding
                            embeddings.append((orig_idx, embedding))
                            
                            # Cache it
                            if self.enable_cache:
                                text_hash = self._hash_text(text)
                                self.cache[text_hash] = EmbeddingCacheEntry(
                                    text_hash=text_hash,
                                    text_preview=text[:100],
                                    embedding=embedding,
                                    model=self.model,
                                    created_at=datetime.now().isoformat(),
                                    dimensions=len(embedding)
                                )
                        
                        break  # Success, exit retry loop
                        
                    except Exception as e:
                        if "rate_limit" in str(e).lower() and attempt < max_retries - 1:
                            wait_time = retry_delay * (2 ** attempt)  # Exponential backoff
                            logger.warning(f"Rate limit hit, retrying in {wait_time}s...")
                            time.sleep(wait_time)
                        else:
                            logger.error(f"Failed to generate embeddings: {e}")
                            raise
                
                # Small delay between batches to avoid rate limits
                if batch_end < len(texts_to_fetch):
                    time.sleep(0.1)
        
        # Sort embeddings back to original order
        embeddings.sort(key=lambda x: x[0])
        result = [emb for _, emb in embeddings]
        
        # Pad result back to original length with None for filtered texts
        if len(valid_indices) < len(texts):
            full_result = [None] * len(texts)
            for valid_idx, emb in zip(valid_indices, result):
                full_result[valid_idx] = emb
            result = [emb for emb in full_result if emb is not None]
        
        # Update statistics
        self._update_stats(
            valid_texts,
            from_cache=len(valid_texts) - len(texts_to_fetch),
            from_api=len(texts_to_fetch)
        )
        
        # Save cache periodically
        if len(texts_to_fetch) > 0:
            self._save_cache()
        
        return result
    
    def embed_chunks(self, chunks: List[Any]) -> List[Dict[str, Any]]:
        """
        Embed chunks from chunking strategies
        
        Args:
            chunks: List of Chunk objects
        
        Returns:
            List of dicts with chunk data + embeddings
        """
        from src.utils.chunking_strategies import Chunk
        
        # Extract text from chunks
        texts = [chunk.text for chunk in chunks]
        
        # Generate embeddings
        embeddings = self.embed_texts(texts)
        
        # Combine with chunk data
        results = []
        for chunk, embedding in zip(chunks, embeddings):
            results.append({
                "text": chunk.text,
                "embedding": embedding,
                "metadata": chunk.metadata,
                "chunk_index": chunk.chunk_index,
                "start_char": chunk.start_char,
                "end_char": chunk.end_char
            })
        
        logger.info(f"Embedded {len(chunks)} chunks")
        return results
    
    def get_stats(self) -> Dict[str, Any]:
        """Get service statistics"""
        return {
            **self.stats,
            "model": self.model,
            "cache_size": len(self.cache),
            "cache_enabled": self.enable_cache
        }
    
    def print_stats(self) -> None:
        """Print statistics"""
        stats = self.get_stats()
        print("\n" + "="*60)
        print("Embedding Service Statistics")
        print("="*60)
        print(f"Model: {stats['model']}")
        print(f"Cache enabled: {stats['cache_enabled']}")
        print(f"Cache size: {stats['cache_size']} entries")
        print(f"API calls: {stats['api_calls']}")
        print(f"Cache hits: {stats['cache_hits']}")
        print(f"Total tokens: {stats['total_tokens']:,}")
        print(f"Estimated cost: ${stats['estimated_cost']:.4f}")
        print("="*60 + "\n")


if __name__ == "__main__":
    # Quick test
    print("Testing Embedding Service...\n")
    
    service = EmbeddingService(enable_cache=True)
    
    # Test with sample texts
    test_texts = [
        "The HVAC system requires regular maintenance.",
        "Technicians must wear proper safety equipment.",
        "All expenses must be submitted within 30 days.",
        "The HVAC system requires regular maintenance.",  # Duplicate to test cache
    ]
    
    print(f"Embedding {len(test_texts)} texts (including 1 duplicate)...\n")
    
    embeddings = service.embed_texts(test_texts)
    
    print(f"Generated {len(embeddings)} embeddings")
    print(f"Embedding dimensions: {len(embeddings[0])}")
    print(f"First embedding preview: {embeddings[0][:5]}...")
    
    # Verify duplicate was cached
    assert embeddings[0] == embeddings[3], "Duplicate text should have same embedding"
    print("\n✓ Cache working: duplicate text returned same embedding")
    
    service.print_stats()
