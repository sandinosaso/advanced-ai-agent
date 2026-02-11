"""
Domain term extraction from natural language questions

Two-phase extraction:
1. Pass 1: Extract atomic signals (LLM-based)
2. Pass 2: Compute compound eligibility (deterministic)
"""

from __future__ import annotations

import json
from typing import List, Dict, Any
from pathlib import Path

from src.utils.logging import logger
from src.llm.client import create_llm
from src.llm.response_utils import extract_text_from_response
from src.config.settings import settings


class DomainTermExtractor:
    """
    Extracts domain-specific business terms from natural language questions.
    
    Uses a two-phase approach:
    1. Atomic signal detection (LLM)
    2. Compound term eligibility (deterministic rules)
    """
    
    # Words that must appear in the question for question/form compound terms to be eligible
    EXPLICIT_QUESTION_WORDS = ("question", "questions", "answer", "answers", "form", "checklist")
    # Registry terms that require at least one of EXPLICIT_QUESTION_WORDS (negative gate)
    QUESTION_FORM_TERMS = ("inspection_questions", "inspection_questions_and_answers", "safety_questions", "service_questions")
    
    def __init__(self, registry: Dict[str, Any]):
        """
        Initialize extractor with domain registry.
        
        Args:
            registry: Domain registry dictionary
        """
        self.registry = registry
        self.llm = None  # Lazy initialization
    
    def _get_llm(self):
        """Lazy initialization of LLM for term extraction"""
        if self.llm is None:
            self.llm = create_llm(temperature=0, max_completion_tokens=settings.max_output_tokens)
        return self.llm
    
    @staticmethod
    def _term_to_phrase(term: str) -> str:
        """Convert registry term key to a short phrase for examples (e.g. action_item -> 'action items')."""
        return term.replace("_", " ").strip()
    
    def _get_atomic_extraction_prompt(self, question: str) -> str:
        """
        Build Pass 1 prompt: atomic signal detection only.
        NEGATIVE RULE first, then atomic rules, then examples (Fix 4 — instruction hierarchy).
        """
        terms = self.registry.get("terms", {})
        known_terms = list(terms.keys())
        # Include both atomic terms (no underscore) and their aliases
        atomic_terms = [t for t in known_terms if "_" not in t]
        # Also collect aliases from compound terms (those with underscores)
        for term_key, term_data in terms.items():
            if "_" in term_key and "aliases" in term_data:
                atomic_terms.extend(term_data["aliases"])
        # Deduplicate and limit to 20 for prompt brevity
        atomic_terms = list(dict.fromkeys(atomic_terms))[:20]
        
        negative_rule = f"""
NEGATIVE RULE (STRICT) — This rule OVERRIDES all other heuristics.
If the question does NOT explicitly mention any of: "question", "questions", "answer", "answers", "form", "checklist"
THEN do NOT return: inspection_questions, safety_questions, service_questions, inspection_questions_and_answers.
Only return single-concept (atomic) signals in this step; compound terms are handled later.
"""
        atomic_rules = """
RULES for atomic signal detection:
- Identify ONLY ATOMIC (single-concept) signals. Ignore compound terms entirely.
- Do NOT infer missing concepts. Only extract terms that are explicitly mentioned in plain language.
- If "question", "answer", "form", or "checklist" is NOT present, do NOT infer inspection/safety/service internals.
- You may return signals that are not in the known list (e.g. "inspection" as an internal signal).
- Return a JSON array of strings. No markdown, no explanation.
"""
        examples = "Examples: \"Find crane inspections\" → [\"crane\", \"inspection\"]. \"Show questions for that inspection\" → [\"inspection\", \"question\"]. \"Payroll report\" → [\"payroll\"]."
        return f"""From the question below, identify ONLY ATOMIC (single-concept) signals.
{negative_rule}
{atomic_rules}
Known atomic-style terms (for reference): {', '.join(atomic_terms) if atomic_terms else 'none'}

Question: {question}

{examples}
Return ONLY a JSON array of strings, e.g. ["crane", "inspection"]."""
    
    def extract_atomic_signals(self, question: str) -> List[str]:
        """
        Pass 1: Extract only atomic (single-concept) signals from the question.
        No compound terms, no inference. May return signals not in the registry (e.g. "inspection").
        """
        if not settings.domain_extraction_enabled:
            return []
        known_terms = list(self.registry.get("terms", {}).keys())
        if not known_terms:
            return []
        prompt = self._get_atomic_extraction_prompt(question)
        try:
            llm = self._get_llm()
            logger.debug(f"Atomic extraction prompt: {prompt[:500]}...")
            response = llm.invoke(prompt)
            
            raw = extract_text_from_response(response).strip() or "[]"
            if raw.startswith("```"):
                lines = raw.split("\n")
                if len(lines) > 2:
                    raw = "\n".join(lines[1:-1]).strip()
                else:
                    raw = "[]"
            if raw.startswith("["):
                signals = json.loads(raw)
                if not isinstance(signals, list):
                    signals = []
                signals = [str(s).strip() for s in signals if s]
                logger.info(f"Atomic signals (Pass 1): {signals}")
                return signals
            logger.warning(f"Invalid JSON from atomic extraction: {raw}")
            return []
        except Exception as e:
            logger.error(f"Atomic extraction failed: {e}")
            return []
    
    def compute_final_registry_terms(self, question: str, atomic_signals: List[str]) -> List[str]:
        """
        Pass 2 (deterministic): Given atomic signals and question text, compute final list of registry terms.
        Applies negative gate, requires_explicit_terms, and requires_atomic_signals from registry.
        """
        terms = self.registry.get("terms", {})
        if not terms:
            return []
        question_lower = question.lower()
        atomic_set = {s.lower() for s in atomic_signals}

        # 1) Negative gate: if question has none of the explicit words, exclude all question/form terms
        has_explicit_question_word = any(w in question_lower for w in self.EXPLICIT_QUESTION_WORDS)
        if not has_explicit_question_word:
            final = [t for t in terms if t not in self.QUESTION_FORM_TERMS]
        else:
            final = list(terms.keys())

        # 2) Keep only terms that are eligible: either atomic (in atomic_signals) or compound (passes requires_*)
        result: List[str] = []
        for term in final:
            term_def = terms.get(term, {})
            primary = term_def.get("resolution", {}).get("primary", {})
            requires_explicit = term_def.get("requires_explicit_terms") or primary.get("requires_explicit_terms")
            requires_atomic = term_def.get("requires_atomic_signals") or primary.get("requires_atomic_signals")
            
            # Check for aliases
            aliases = term_def.get("aliases", [])

            if not requires_explicit and not requires_atomic:
                # Atomic-only term: include if it appears in atomic signals or matches an alias
                if any(s.lower() == term.lower() for s in atomic_signals):
                    result.append(term)
                elif aliases and any(s.lower() in [a.lower() for a in aliases] for s in atomic_signals):
                    result.append(term)
                elif aliases and any(a.lower() in question_lower for a in aliases):
                    # Multi-word aliases (e.g. "dynamic attribute"): LLM returns single words;
                    # check if question contains the full alias phrase
                    result.append(term)
                continue

            # Compound term: require explicit words and atomic signals
            if requires_explicit and not any(w in question_lower for w in requires_explicit):
                continue
            if requires_atomic and not all(a.lower() in atomic_set for a in requires_atomic):
                continue
            result.append(term)
        return result
    
    def extract_domain_terms(
        self, question: str, implied_atomic_signals: List[str] | None = None
    ) -> List[str]:
        """
        Extract domain-specific business terms from natural language question.
        Two-phase: Pass 1 atomic signals (LLM), Pass 2 compound eligibility (deterministic).
        Returns only registry term keys that pass both phases.

        When implied_atomic_signals is provided (e.g. from follow-up context), these are
        merged with LLM-extracted signals. This handles terse follow-up questions like
        "Now for that inspections I want all questions and answers" where the LLM may
        return [] but we know from follow-up detection that "inspection" is the context.
        
        Args:
            question: Natural language question
            implied_atomic_signals: Optional signals from follow-up context (e.g. ["inspection"])
            
        Returns:
            List of registry term keys found in the question
        """
        if not settings.domain_extraction_enabled:
            logger.debug("Domain extraction disabled")
            return []
        known_terms = list(self.registry.get("terms", {}).keys())
        if not known_terms:
            logger.debug("No terms in domain registry, skipping extraction")
            return []
        # Pass 1: atomic signals only (may include non-registry e.g. "inspection")
        atomic_signals = self.extract_atomic_signals(question)
        # Merge implied signals from follow-up context when LLM returns empty
        if implied_atomic_signals:
            for s in implied_atomic_signals:
                if s and s.lower() not in {x.lower() for x in atomic_signals}:
                    atomic_signals.append(s)
            logger.info(f"Merged implied atomic signals: {implied_atomic_signals} -> {atomic_signals}")
        # Pass 2: deterministic compound eligibility + negative gate
        valid_terms = self.compute_final_registry_terms(question, atomic_signals)
        logger.info(f"Extracted domain terms (two-phase): {valid_terms}")
        return valid_terms
