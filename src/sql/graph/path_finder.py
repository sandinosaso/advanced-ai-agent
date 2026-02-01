"""
Efficient join path finder using Dijkstra's algorithm.

This module provides utilities to find shortest join paths between tables
in the join graph. It uses graph algorithms instead of exhaustive search.
"""

import heapq
import logging
from collections import defaultdict, deque
from typing import Dict, List, Optional, Tuple, Set

logger = logging.getLogger(__name__)


class JoinPathFinder:
    """
    Efficient path finder for join graph using Dijkstra's algorithm.
    
    Instead of finding ALL paths between ALL pairs (exponential), this:
    1. Uses Dijkstra to find SHORTEST paths
    2. Computes paths on-demand for selected tables
    3. Caches results for performance
    """
    
    def __init__(self, relationships: List[Dict], confidence_threshold: float = 0.7):
        """
        Initialize path finder with relationships.
        
        Args:
            relationships: List of relationship dicts from join graph
            confidence_threshold: Minimum confidence to include a relationship
        """
        self.relationships = relationships
        self.confidence_threshold = confidence_threshold
        self._graph = self._build_graph()
        self._cache: Dict[Tuple[str, str], Optional[List[Dict]]] = {}
        
        logger.info(f"Initialized JoinPathFinder with {len(self._graph)} nodes")
    
    def _build_graph(self) -> Dict[str, List[Tuple[str, Dict]]]:
        """
        Build adjacency list from relationships.
        
        Returns:
            Dict mapping table -> [(neighbor_table, relationship_dict), ...]
        """
        graph = defaultdict(list)
        
        for rel in self.relationships:
            confidence = float(rel.get("confidence", 0))
            if confidence < self.confidence_threshold:
                continue
            
            from_table = rel["from_table"]
            to_table = rel["to_table"]
            
            # Add bidirectional edges (joins work both ways)
            graph[from_table].append((to_table, rel))
            graph[to_table].append((from_table, rel))
        
        return dict(graph)
    
    def find_shortest_path(
        self, 
        start: str, 
        end: str, 
        max_hops: int = 4
    ) -> Optional[List[Dict]]:
        """
        Find shortest path between two tables using Dijkstra's algorithm.
        
        Args:
            start: Starting table name
            end: Target table name
            max_hops: Maximum number of hops (default: 4)
            
        Returns:
            List of relationship dicts representing the path, or None if no path exists
        """
        # Check cache
        cache_key = (start, end)
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        # Same table - no path needed
        if start == end:
            self._cache[cache_key] = []
            return []
        
        # Check if tables exist in graph
        if start not in self._graph or end not in self._graph:
            self._cache[cache_key] = None
            return None
        
        # Dijkstra's algorithm
        # Priority queue: (distance, tie_breaker, current_table, path_so_far)
        # Use tie_breaker to avoid dict comparison issues
        tie_breaker = 0
        pq = [(0, tie_breaker, start, [])]
        visited: Set[str] = set()
        
        while pq:
            distance, _, current, path = heapq.heappop(pq)
            
            # Skip if we've visited this node with a shorter path
            if current in visited:
                continue
            
            visited.add(current)
            
            # Found target
            if current == end:
                self._cache[cache_key] = path
                return path
            
            # Stop if we've exceeded max hops
            if distance >= max_hops:
                continue
            
            # Explore neighbors
            for neighbor, rel in self._graph.get(current, []):
                if neighbor in visited:
                    continue
                
                # Weight: prefer higher confidence, shorter paths
                # Confidence 1.0 = weight 0, lower confidence = higher weight
                weight = 1.0 - float(rel.get("confidence", 0.5))
                
                new_distance = distance + 1 + weight
                new_path = path + [rel]
                tie_breaker += 1
                
                heapq.heappush(pq, (new_distance, tie_breaker, neighbor, new_path))
        
        # No path found
        self._cache[cache_key] = None
        return None
    
    def find_paths_between_tables(
        self, 
        tables: List[str], 
        max_hops: int = 4
    ) -> Dict[Tuple[str, str], List[Dict]]:
        """
        Find shortest paths between all pairs of selected tables.
        
        Args:
            tables: List of table names
            max_hops: Maximum number of hops
            
        Returns:
            Dict mapping (from_table, to_table) -> path (list of relationships)
        """
        paths = {}
        
        # Find paths between all pairs
        for i, start in enumerate(tables):
            for end in tables[i+1:]:
                path = self.find_shortest_path(start, end, max_hops)
                if path is not None:
                    paths[(start, end)] = path
                    # Also cache reverse direction
                    paths[(end, start)] = self._reverse_path(path)
        
        return paths
    
    def _reverse_path(self, path: List[Dict]) -> List[Dict]:
        """
        Reverse a path (swap from/to for each relationship).
        
        Args:
            path: List of relationship dicts
            
        Returns:
            Reversed path with swapped from/to
        """
        reversed_path = []
        for rel in reversed(path):
            reversed_rel = rel.copy()
            reversed_rel["from_table"], reversed_rel["to_table"] = (
                reversed_rel["to_table"], 
                reversed_rel["from_table"]
            )
            reversed_rel["from_column"], reversed_rel["to_column"] = (
                reversed_rel["to_column"], 
                reversed_rel["from_column"]
            )
            reversed_path.append(reversed_rel)
        return reversed_path
    
    def expand_relationships(
        self, 
        tables: List[str], 
        direct_relationships: List[Dict],
        max_hops: int = 4
    ) -> List[Dict]:
        """
        Expand direct relationships to include transitive paths.
        
        This takes the direct relationships and adds shortest paths
        between tables that aren't directly connected.
        
        Args:
            tables: Selected tables
            direct_relationships: Direct relationships between selected tables
            max_hops: Maximum hops for transitive paths
            
        Returns:
            Expanded list of relationships (direct + transitive paths flattened)
        """
        # Start with direct relationships
        expanded = list(direct_relationships)
        
        # Find paths between all table pairs
        paths = self.find_paths_between_tables(tables, max_hops)
        
        # Add relationships from transitive paths
        for (start, end), path in paths.items():
            # Skip if already have direct relationship
            has_direct = any(
                (r["from_table"] == start and r["to_table"] == end) or
                (r["from_table"] == end and r["to_table"] == start)
                for r in direct_relationships
            )
            
            if not has_direct and path:
                # Add all relationships in the path
                expanded.extend(path)
        
        # Deduplicate (keep first occurrence)
        seen = set()
        unique_rels = []
        for rel in expanded:
            key = (
                rel["from_table"],
                rel["from_column"],
                rel["to_table"],
                rel["to_column"]
            )
            if key not in seen:
                seen.add(key)
                unique_rels.append(rel)
        
        return unique_rels
    
    def get_path_description(self, path: List[Dict]) -> str:
        """
        Convert a path to a human-readable description.
        
        Args:
            path: List of relationship dicts
            
        Returns:
            String description of the join path
        """
        if not path:
            return "Direct relationship (same table or no joins needed)"
        
        parts = []
        for i, rel in enumerate(path):
            parts.append(
                f"{rel['from_table']}.{rel['from_column']} = "
                f"{rel['to_table']}.{rel['to_column']} "
                f"({rel.get('cardinality', 'unknown')}, "
                f"conf: {rel.get('confidence', 0):.2f})"
            )
        
        return " → ".join(parts)
