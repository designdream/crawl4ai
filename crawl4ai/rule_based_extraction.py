"""
Rule-based extraction strategy for Crawl4AI that avoids hallucinations.

This module provides extraction strategies based on traditional NLP techniques
rather than generative AI, focusing on deterministic extraction with high confidence.
"""

import re
import json
from typing import List, Dict, Any, Tuple, Optional
from bs4 import BeautifulSoup
from collections import defaultdict

# Import required base classes and utilities
from .extraction_strategy import ExtractionStrategy
from .utils import sanitize_html, normalize_text

# Optional: Try to import spaCy for more advanced NLP capabilities
try:
    import spacy
    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False

class RuleBasedExtractionStrategy(ExtractionStrategy):
    """
    Extract text using rule-based patterns without relying on generative AI.
    
    This strategy uses regex patterns, keyword matching, and contextual rules
    to extract factual information without hallucinations.
    """
    
    def __init__(
        self, 
        patterns: List[Dict] = None,
        confidence_threshold: float = 0.7,
        extract_entities: bool = True,
        extract_relations: bool = True,
        include_context: bool = True,
        context_window: int = 100,
        **kwargs
    ):
        """
        Initialize the rule-based extraction strategy.
        
        Args:
            patterns: List of extraction patterns (regex or keyword-based)
            confidence_threshold: Minimum confidence score to include extractions
            extract_entities: Whether to extract named entities
            extract_relations: Whether to extract relationships between entities
            include_context: Whether to include surrounding context with extractions
            context_window: Number of characters to include as context
            **kwargs: Additional arguments passed to parent ExtractionStrategy
        """
        super().__init__(input_format="html", **kwargs)
        self.patterns = patterns or []
        self.confidence_threshold = confidence_threshold
        self.extract_entities = extract_entities
        self.extract_relations = extract_relations
        self.include_context = include_context
        self.context_window = context_window
        self.verbose = kwargs.get("verbose", False)
        
        # Initialize spaCy if available
        self.nlp = None
        if SPACY_AVAILABLE and self.extract_entities:
            try:
                self.nlp = spacy.load("en_core_web_sm")
                if self.verbose:
                    print("[INFO] Loaded spaCy model for entity extraction")
            except Exception as e:
                if self.verbose:
                    print(f"[WARNING] Failed to load spaCy model: {e}")

    def extract(self, url: str, html: str, *q, **kwargs) -> List[Dict[str, Any]]:
        """
        Extract meaningful blocks using rule-based approaches.
        
        Args:
            url: The URL of the webpage
            html: The HTML content of the webpage
            
        Returns:
            List of extraction results with confidence scores
        """
        # Clean and parse HTML
        clean_html = sanitize_html(html)
        soup = BeautifulSoup(clean_html, "html.parser")
        
        # Extract plain text from HTML
        text = soup.get_text(separator=" ", strip=True)
        normalized_text = normalize_text(text)
        
        results = []
        
        # 1. Apply regex pattern matching
        pattern_matches = self._apply_patterns(normalized_text)
        for match in pattern_matches:
            if match["confidence"] >= self.confidence_threshold:
                results.append(match)
        
        # 2. Apply entity extraction if enabled
        if self.extract_entities and self.nlp:
            entity_results = self._extract_entities(normalized_text)
            for entity in entity_results:
                if entity["confidence"] >= self.confidence_threshold:
                    results.append(entity)
        
        # 3. Apply relation extraction if enabled
        if self.extract_relations and len(results) > 1:
            relation_results = self._extract_relations(results, normalized_text)
            for relation in relation_results:
                if relation["confidence"] >= self.confidence_threshold:
                    results.append(relation)
        
        # Add source verification
        results = self._add_verification(results, normalized_text)
        
        # Remove duplicates and sort by confidence
        unique_results = self._deduplicate_results(results)
        sorted_results = sorted(unique_results, key=lambda x: x.get("confidence", 0), reverse=True)
        
        # Add metadata
        for result in sorted_results:
            result["url"] = url
            result["extraction_method"] = "rule_based"
            
        return sorted_results
    
    def _apply_patterns(self, text: str) -> List[Dict[str, Any]]:
        """Apply regex and keyword patterns to extract information."""
        results = []
        
        # Apply custom patterns if provided
        if self.patterns:
            for pattern_dict in self.patterns:
                pattern = pattern_dict.get("pattern", "")
                pattern_type = pattern_dict.get("type", "regex")
                name = pattern_dict.get("name", "custom_pattern")
                
                if pattern_type == "regex":
                    try:
                        matches = re.finditer(pattern, text)
                        for match in matches:
                            # Get the matched text
                            match_text = match.group(0)
                            
                            # Calculate confidence based on specificity
                            confidence = self._calculate_confidence(match_text, pattern)
                            
                            # Get context if requested
                            context = self._get_context(text, match.start(), match.end()) if self.include_context else ""
                            
                            results.append({
                                "type": name,
                                "value": match_text,
                                "confidence": confidence,
                                "context": context,
                                "groups": {k: v for k, v in match.groupdict().items()},
                                "span": (match.start(), match.end())
                            })
                    except re.error as e:
                        if self.verbose:
                            print(f"[ERROR] Invalid regex pattern '{pattern}': {e}")
                
                elif pattern_type == "keyword":
                    keyword_matches = self._find_keyword_matches(text, pattern)
                    for start, end in keyword_matches:
                        match_text = text[start:end]
                        confidence = self._calculate_confidence(match_text, pattern)
                        context = self._get_context(text, start, end) if self.include_context else ""
                        
                        results.append({
                            "type": name,
                            "value": match_text,
                            "confidence": confidence,
                            "context": context,
                            "span": (start, end)
                        })
        
        # Apply common regulatory patterns if no custom patterns
        if not self.patterns:
            results.extend(self._apply_default_patterns(text))
            
        return results
    
    def _apply_default_patterns(self, text: str) -> List[Dict[str, Any]]:
        """Apply default patterns for regulatory information."""
        results = []
        
        # Pattern for CE hours
        ce_hours_pattern = r"(\d+)\s*(?:hours?|hrs?|credit\s*hours?|CE\s*hours?|contact\s*hours?|CEUs?)"
        matches = re.finditer(ce_hours_pattern, text, re.IGNORECASE)
        for match in matches:
            hours = match.group(1)
            match_text = match.group(0)
            context = self._get_context(text, match.start(), match.end()) if self.include_context else ""
            
            results.append({
                "type": "ce_hours",
                "value": hours,
                "raw_match": match_text,
                "confidence": 0.85,  # High confidence for numeric hour matches
                "context": context,
                "span": (match.start(), match.end())
            })
        
        # Pattern for renewal periods
        renewal_pattern = r"(?:renewal|license renewal|renew).{0,30}(?:every|each)\s+(\d+)\s*(years?|months?)"
        matches = re.finditer(renewal_pattern, text, re.IGNORECASE)
        for match in matches:
            period_value = match.group(1)
            period_unit = match.group(2)
            match_text = match.group(0)
            context = self._get_context(text, match.start(), match.end()) if self.include_context else ""
            
            results.append({
                "type": "renewal_period",
                "value": f"{period_value} {period_unit}",
                "raw_match": match_text,
                "confidence": 0.8,
                "context": context,
                "span": (match.start(), match.end())
            })
            
        # Pattern for specialized CE requirements
        specialized_pattern = r"(\d+)\s*(?:hours?|credits?).{0,50}(?:in|of|for)\s+([a-zA-Z\s]{3,50})"
        matches = re.finditer(specialized_pattern, text, re.IGNORECASE)
        for match in matches:
            hours = match.group(1)
            topic = match.group(2).strip()
            match_text = match.group(0)
            context = self._get_context(text, match.start(), match.end()) if self.include_context else ""
            
            results.append({
                "type": "specialized_requirement",
                "hours": hours,
                "topic": topic,
                "raw_match": match_text,
                "confidence": 0.75,
                "context": context,
                "span": (match.start(), match.end())
            })
            
        return results
    
    def _find_keyword_matches(self, text: str, keyword: str) -> List[Tuple[int, int]]:
        """Find all occurrences of a keyword in text."""
        matches = []
        start = 0
        keyword_lower = keyword.lower()
        text_lower = text.lower()
        
        while True:
            start = text_lower.find(keyword_lower, start)
            if start == -1:
                break
            end = start + len(keyword)
            matches.append((start, end))
            start = end
            
        return matches
    
    def _extract_entities(self, text: str) -> List[Dict[str, Any]]:
        """Extract named entities using spaCy."""
        results = []
        
        if not self.nlp:
            return results
            
        doc = self.nlp(text)
        
        # Process each entity
        for ent in doc.ents:
            # Filter out less relevant entity types
            if ent.label_ in ["DATE", "TIME", "CARDINAL", "ORDINAL", "MONEY", "PERCENT", "QUANTITY"]:
                confidence = 0.75
            else:
                confidence = 0.6
                
            context = self._get_context(text, ent.start_char, ent.end_char) if self.include_context else ""
            
            results.append({
                "type": "entity",
                "entity_type": ent.label_,
                "value": ent.text,
                "confidence": confidence,
                "context": context,
                "span": (ent.start_char, ent.end_char)
            })
            
        return results
    
    def _extract_relations(self, entities: List[Dict], text: str) -> List[Dict[str, Any]]:
        """Extract relationships between entities based on proximity and patterns."""
        results = []
        
        # Simple approach: relate entities that are close to each other
        sorted_entities = sorted(entities, key=lambda x: x.get("span", (0, 0))[0])
        
        for i in range(len(sorted_entities) - 1):
            entity1 = sorted_entities[i]
            entity2 = sorted_entities[i + 1]
            
            # Check if entities are close enough
            _, end1 = entity1.get("span", (0, 0))
            start2, _ = entity2.get("span", (0, 0))
            
            if start2 - end1 <= 50:  # Arbitrary threshold of 50 chars
                between_text = text[end1:start2]
                
                # Look for relation indicators in between text
                relation_indicators = ["of", "for", "in", "requires", "must have"]
                for indicator in relation_indicators:
                    if indicator in between_text.lower():
                        # Create relation
                        relation_text = text[entity1.get("span", (0, 0))[0]:entity2.get("span", (0, 0))[1]]
                        
                        results.append({
                            "type": "relation",
                            "entity1": entity1.get("value"),
                            "entity1_type": entity1.get("type"),
                            "entity2": entity2.get("value"),
                            "entity2_type": entity2.get("type"),
                            "relation": indicator,
                            "text": relation_text,
                            "confidence": 0.65,  # Lower confidence for inferred relations
                            "span": (entity1.get("span", (0, 0))[0], entity2.get("span", (0, 0))[1])
                        })
                        
                        break
        
        return results
        
    def _add_verification(self, results: List[Dict], text: str) -> List[Dict]:
        """Add verification scores based on textual evidence."""
        verified_results = []
        
        for result in results:
            # Initialize verification score based on confidence
            verification_score = result.get("confidence", 0.5)
            
            # Check if the extraction has strong textual evidence
            value = result.get("value", "")
            if isinstance(value, str) and len(value) > 0:
                # Stronger verification for numeric values with clear units
                if re.match(r"^\d+\s*[a-zA-Z]+$", value):
                    verification_score += 0.2
                    
                # Check if value appears multiple times
                occurrences = text.lower().count(value.lower())
                if occurrences > 1:
                    verification_score += min(0.1 * occurrences, 0.2)
                    
                # Higher verification for patterns with named capture groups
                if "groups" in result and result["groups"]:
                    verification_score += 0.1
            
            # Cap verification score at 1.0
            verification_score = min(1.0, verification_score)
            
            # Add verification to result
            result["verification_score"] = verification_score
            result["verified"] = verification_score >= self.confidence_threshold
            
            verified_results.append(result)
            
        return verified_results
    
    def _get_context(self, text: str, start: int, end: int) -> str:
        """Get surrounding context for an extraction."""
        context_start = max(0, start - self.context_window)
        context_end = min(len(text), end + self.context_window)
        
        # Get before and after context
        before = text[context_start:start]
        after = text[end:context_end]
        
        # Clean up context
        before = before.strip()
        after = after.strip()
        
        return f"{before} [EXTRACTION] {after}"
    
    def _calculate_confidence(self, match_text: str, pattern: str) -> float:
        """Calculate confidence score for a match."""
        base_confidence = 0.7
        
        # Adjust confidence based on match characteristics
        if re.search(r"\d+", match_text):
            # Numeric matches often more reliable
            base_confidence += 0.1
            
        # Adjust for specificity of pattern
        pattern_complexity = len(re.findall(r'[()[\]{}|+*?]', pattern)) if isinstance(pattern, str) else 0
        base_confidence += min(0.01 * pattern_complexity, 0.1)
        
        # Adjust for match length (longer matches generally more specific)
        base_confidence += min(0.01 * len(match_text), 0.1)
        
        # Cap at 0.95 (we can never be 100% confident without verification)
        return min(0.95, base_confidence)
    
    def _deduplicate_results(self, results: List[Dict]) -> List[Dict]:
        """Remove duplicate extractions."""
        seen_values = set()
        unique_results = []
        
        for result in results:
            # Create a unique key based on type and value
            value = result.get("value", "")
            result_type = result.get("type", "")
            key = f"{result_type}:{value}"
            
            if key not in seen_values:
                seen_values.add(key)
                unique_results.append(result)
            else:
                # If duplicate exists, keep the one with higher confidence
                for i, existing in enumerate(unique_results):
                    existing_type = existing.get("type", "")
                    existing_value = existing.get("value", "")
                    
                    if f"{existing_type}:{existing_value}" == key:
                        if result.get("confidence", 0) > existing.get("confidence", 0):
                            unique_results[i] = result
                        break
        
        return unique_results


class RegulationExtractionStrategy(RuleBasedExtractionStrategy):
    """
    Specialized extraction strategy for healthcare continuing education requirements.
    
    This strategy uses domain-specific patterns and rules to extract structured
    information about CE requirements, renewal periods, and specialized topics.
    """
    
    def __init__(self, **kwargs):
        """Initialize with healthcare regulation specific patterns."""
        patterns = [
            # CE Hours
            {
                "name": "ce_total_hours",
                "type": "regex",
                "pattern": r"(?:required to complete|must complete|need|requires?)\s+(\d+)\s+(?:hours?|contact\s+hours?|continuing\s+education|CE\s+hours?|CEUs?|credits?)"
            },
            # Renewal Period
            {
                "name": "renewal_period",
                "type": "regex",
                "pattern": r"(?:renew|renewal)\s+(?:period|cycle|every|each)\s+(\d+)\s+(years?|months?)"
            },
            # Specialized Topics
            {
                "name": "specialized_topic",
                "type": "regex",
                "pattern": r"(\d+)\s+(?:hours?|credits?).{0,30}(?:in|of|for|related\s+to)\s+([a-zA-Z\s\-]+(?:ethics|safety|law|infection control|substance abuse|pharmacology|medication|emergency|mandatory|required))"
            },
            # Deadlines
            {
                "name": "renewal_deadline",
                "type": "regex",
                "pattern": r"(?:renewal|license).{0,20}(?:deadline|due|expires?|must\s+be\s+completed)\s+(?:by|before|prior\s+to)?\s+([a-zA-Z]+\s+\d{1,2}(?:st|nd|rd|th)?(?:,?\s+\d{4})?)"
            },
            # Exemptions
            {
                "name": "exemption",
                "type": "regex",
                "pattern": r"(?:exempt|exemption|waive|waiver).{0,50}(?:from|for)\s+([a-zA-Z\s\-]+)"
            }
        ]
        
        super().__init__(
            patterns=patterns,
            confidence_threshold=0.7,
            extract_entities=True,
            extract_relations=True,
            include_context=True,
            context_window=150,
            **kwargs
        )
    
    def extract(self, url: str, html: str, *q, **kwargs) -> List[Dict[str, Any]]:
        """
        Extract healthcare regulation information from HTML.
        
        Returns structured data about CE requirements with verification.
        """
        # Get basic extractions using parent method
        results = super().extract(url, html, *q, **kwargs)
        
        # Organize extractions into a structured format
        structured_data = self._structure_regulations(results)
        
        # Return both the structured format and the raw extractions
        return [{
            "url": url,
            "extraction_method": "regulation_extraction",
            "structured_data": structured_data,
            "raw_extractions": results,
            "confidence": self._calculate_overall_confidence(results)
        }]
    
    def _structure_regulations(self, results: List[Dict]) -> Dict[str, Any]:
        """Organize extraction results into structured regulation data."""
        structured = {
            "total_hours": None,
            "renewal_period": None,
            "specialized_requirements": [],
            "deadlines": [],
            "exemptions": [],
            "other_requirements": []
        }
        
        # Process each extraction
        for result in results:
            result_type = result.get("type", "")
            
            if result_type == "ce_total_hours" and structured["total_hours"] is None:
                structured["total_hours"] = {
                    "hours": result.get("value", ""),
                    "context": result.get("context", ""),
                    "confidence": result.get("confidence", 0),
                    "verified": result.get("verified", False)
                }
            
            elif result_type == "renewal_period" and structured["renewal_period"] is None:
                structured["renewal_period"] = {
                    "period": result.get("value", ""),
                    "context": result.get("context", ""),
                    "confidence": result.get("confidence", 0),
                    "verified": result.get("verified", False)
                }
            
            elif result_type == "specialized_topic":
                structured["specialized_requirements"].append({
                    "hours": result.get("hours", result.get("value", "")),
                    "topic": result.get("topic", ""),
                    "context": result.get("context", ""),
                    "confidence": result.get("confidence", 0),
                    "verified": result.get("verified", False)
                })
            
            elif result_type == "renewal_deadline":
                structured["deadlines"].append({
                    "deadline": result.get("value", ""),
                    "context": result.get("context", ""),
                    "confidence": result.get("confidence", 0),
                    "verified": result.get("verified", False)
                })
            
            elif result_type == "exemption":
                structured["exemptions"].append({
                    "exemption": result.get("value", ""),
                    "context": result.get("context", ""),
                    "confidence": result.get("confidence", 0),
                    "verified": result.get("verified", False)
                })
            
            # Add any entity that might be related to regulations
            elif result_type == "entity" and result.get("entity_type") in ["ORG", "LAW", "DATE"]:
                structured["other_requirements"].append({
                    "type": result.get("entity_type", ""),
                    "value": result.get("value", ""),
                    "context": result.get("context", ""),
                    "confidence": result.get("confidence", 0),
                    "verified": result.get("verified", False)
                })
        
        return structured
    
    def _calculate_overall_confidence(self, results: List[Dict]) -> float:
        """Calculate overall confidence score for the extraction."""
        if not results:
            return 0.0
            
        # Weight verified results more heavily
        verified_scores = [r.get("confidence", 0) for r in results if r.get("verified", False)]
        unverified_scores = [r.get("confidence", 0) for r in results if not r.get("verified", False)]
        
        if verified_scores:
            verified_avg = sum(verified_scores) / len(verified_scores)
            weight = 0.8
        else:
            verified_avg = 0
            weight = 0
            
        if unverified_scores:
            unverified_avg = sum(unverified_scores) / len(unverified_scores)
            unverified_weight = 1 - weight
        else:
            unverified_avg = 0
            unverified_weight = 0
            
        overall = (verified_avg * weight) + (unverified_avg * unverified_weight)
        
        # Adjust based on number of extractions (more extractions = more confidence)
        extraction_bonus = min(0.1, 0.01 * len(results))
        
        return min(0.95, overall + extraction_bonus)
