"""
LlamaPreValidator - Pre-synthesis text analysis agent.

Scans chunk text BEFORE TTS synthesis to proactively detect:
- Abbreviations and acronyms that TTS engines struggle with
- Complex numbers and financial notation
- TTS-hostile punctuation (em-dashes, nested quotes, ellipses)
- Repetitive patterns in source text
- Long sentences likely to cause truncation

Returns structured recommendations for preprocessing or rewriting.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from .llama_base import LlamaAgent
from .llama_pronunciation_assistant import LlamaPronunciationAssistant

logger = logging.getLogger(__name__)

# Try to import num2words for number expansion
try:
    from num2words import num2words
    NUM2WORDS_AVAILABLE = True
except ImportError:
    NUM2WORDS_AVAILABLE = False
    logger.debug("num2words not installed - number expansion will use fallback")

# Common abbreviations that cause TTS issues
COMMON_ABBREVIATIONS = {
    # Titles
    r"\bMr\b\.?": "Mister",
    r"\bMrs\b\.?": "Missus",
    r"\bDr\b\.?": "Doctor",
    r"\bProf\b\.?": "Professor",
    r"\bSt\b\.": "Saint",
    r"\bGen\b\.?": "General",
    r"\bSgt\b\.?": "Sergeant",
    r"\bLt\b\.?": "Lieutenant",
    r"\bCapt\b\.?": "Captain",
    r"\bCol\b\.?": "Colonel",
    # Common abbreviations
    r"\betc\b\.?": "et cetera",
    r"\be\.g\b\.?": "for example",
    r"\bi\.e\b\.?": "that is",
    r"\bvs\b\.?": "versus",
    r"\bw/": "with",
    r"\bw/o\b": "without",
    r"\b&\b": "and",
}

# Regex patterns for detection
PATTERNS = {
    # All-caps acronyms (2-6 letters)
    "acronym": re.compile(r"\b[A-Z]{2,6}\b"),
    # Mixed case abbreviations (e.g., "PhD", "MBA")
    "mixed_abbrev": re.compile(r"\b[A-Z][a-z]*[A-Z]+[a-z]*\b"),
    # Currency with numbers
    "currency": re.compile(r"[$€£¥]\s*[\d,]+(?:\.\d+)?[MBKmbk]?\b"),
    # Percentages
    "percentage": re.compile(r"\d+(?:\.\d+)?\s*%"),
    # Complex numbers (with decimals, commas, units)
    "complex_number": re.compile(r"\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+\.\d+[MBKmbk]?"),
    # Fiscal/quarter notation (Q1, FY2024)
    "fiscal": re.compile(r"\b(?:Q[1-4]|FY\d{2,4}|H[12])\b", re.IGNORECASE),
    # Date formats that TTS struggles with
    "date_format": re.compile(r"\b\d{1,2}/\d{1,2}/\d{2,4}\b|\b\d{4}-\d{2}-\d{2}\b"),
    # Em-dashes and problematic punctuation
    "em_dash": re.compile(r"—|--"),
    # Ellipses
    "ellipsis": re.compile(r"\.{3,}|…"),
    # Nested quotes
    "nested_quotes": re.compile(r"[\"'][^\"']*[\"'][^\"']*[\"']"),
    # Very long sentences (>200 chars without period)
    "long_sentence": re.compile(r"[^.!?]{200,}"),
    # Repeated words (immediate)
    "word_repeat": re.compile(r"\b(\w+)\s+\1\b", re.IGNORECASE),
}


class LlamaPreValidator(LlamaAgent):
    """
    Pre-synthesis text validator that identifies TTS-hostile patterns.

    Runs BEFORE TTS synthesis to catch issues proactively, reducing
    retry cycles and improving first-run success rates.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Compile abbreviation patterns
        self._abbrev_patterns = [
            (re.compile(pattern, re.IGNORECASE), replacement)
            for pattern, replacement in COMMON_ABBREVIATIONS.items()
        ]

    def validate_for_tts(
        self,
        text: str,
        check_with_llm: bool = True,
        max_issues: int = 10,
    ) -> Dict[str, Any]:
        """
        Validate text for TTS synthesis and identify potential issues.

        Args:
            text: The chunk text to validate
            check_with_llm: Whether to use LLM for deeper analysis
            max_issues: Maximum number of issues to return

        Returns:
            dict with keys:
                - valid: bool - True if text is TTS-ready
                - issues: List[dict] - Detected issues with type, match, suggestion
                - needs_rewrite: bool - True if rewriting is recommended
                - confidence: float - Confidence in the analysis
                - suggested_text: Optional[str] - LLM-suggested rewrite if needed
        """
        issues = []

        # Run pattern-based detection
        issues.extend(self._detect_acronyms(text))
        issues.extend(self._detect_numbers(text))
        issues.extend(self._detect_punctuation(text))
        issues.extend(self._detect_structure(text))
        issues.extend(self._detect_repetition(text))
        issues.extend(self._detect_abbreviations(text))

        # Limit issues
        issues = issues[:max_issues]

        # Calculate severity
        high_severity = sum(1 for i in issues if i.get("severity") == "high")
        medium_severity = sum(1 for i in issues if i.get("severity") == "medium")

        # Determine if rewrite is needed
        needs_rewrite = high_severity >= 2 or (high_severity >= 1 and medium_severity >= 2)

        result = {
            "valid": len(issues) == 0,
            "issues": issues,
            "needs_rewrite": needs_rewrite,
            "confidence": 0.9 if not check_with_llm else 0.0,
            "suggested_text": None,
            "issue_summary": self._summarize_issues(issues),
        }

        # If we have significant issues and LLM is available, get a suggested fix
        if needs_rewrite and check_with_llm:
            llm_result = self._get_llm_suggestions(text, issues)
            result["suggested_text"] = llm_result.get("suggested_text")
            result["confidence"] = llm_result.get("confidence", 0.0)
            result["llm_notes"] = llm_result.get("notes")

        return result

    def _detect_acronyms(self, text: str) -> List[Dict[str, Any]]:
        """Detect acronyms that may be spelled out by TTS."""
        issues = []

        # Known safe acronyms that TTS handles well
        safe_acronyms = {"OK", "TV", "US", "UK", "EU", "UN", "AM", "PM", "AD", "BC"}

        for match in PATTERNS["acronym"].finditer(text):
            acronym = match.group()
            if acronym not in safe_acronyms:
                issues.append({
                    "type": "acronym",
                    "match": acronym,
                    "position": match.start(),
                    "suggestion": f"Expand '{acronym}' to full form",
                    "severity": "high" if len(acronym) >= 3 else "medium",
                })

        return issues

    def _detect_numbers(self, text: str) -> List[Dict[str, Any]]:
        """Detect complex number formats."""
        issues = []

        for pattern_name in ["currency", "percentage", "complex_number", "fiscal", "date_format"]:
            for match in PATTERNS[pattern_name].finditer(text):
                issues.append({
                    "type": pattern_name,
                    "match": match.group(),
                    "position": match.start(),
                    "suggestion": f"Convert to spoken form: '{match.group()}'",
                    "severity": "high" if pattern_name in ["fiscal", "currency"] else "medium",
                })

        return issues

    def _detect_punctuation(self, text: str) -> List[Dict[str, Any]]:
        """Detect problematic punctuation."""
        issues = []

        for pattern_name in ["em_dash", "ellipsis", "nested_quotes"]:
            for match in PATTERNS[pattern_name].finditer(text):
                issues.append({
                    "type": pattern_name,
                    "match": match.group(),
                    "position": match.start(),
                    "suggestion": f"Simplify punctuation: '{match.group()}'",
                    "severity": "medium",
                })

        return issues

    def _detect_structure(self, text: str) -> List[Dict[str, Any]]:
        """Detect structural issues (long sentences, etc.)."""
        issues = []

        for match in PATTERNS["long_sentence"].finditer(text):
            segment = match.group()[:50] + "..."
            issues.append({
                "type": "long_sentence",
                "match": segment,
                "position": match.start(),
                "length": len(match.group()),
                "suggestion": "Break into shorter sentences",
                "severity": "high",
            })

        return issues

    def _detect_repetition(self, text: str) -> List[Dict[str, Any]]:
        """Detect repetitive patterns in source text."""
        issues = []

        # Immediate word repetition
        for match in PATTERNS["word_repeat"].finditer(text):
            issues.append({
                "type": "word_repeat",
                "match": match.group(),
                "position": match.start(),
                "suggestion": f"Remove repeated word: '{match.group(1)}'",
                "severity": "low",
            })

        # N-gram repetition (phrases repeated 3+ times)
        words = text.lower().split()
        if len(words) >= 10:
            for n in range(4, 8):  # Check 4-7 word phrases
                if len(words) < n * 2:
                    continue
                ngrams = [" ".join(words[i:i+n]) for i in range(len(words) - n + 1)]
                seen = {}
                for i, ngram in enumerate(ngrams):
                    if ngram in seen:
                        seen[ngram].append(i)
                    else:
                        seen[ngram] = [i]

                for ngram, positions in seen.items():
                    if len(positions) >= 3:
                        issues.append({
                            "type": "phrase_repeat",
                            "match": ngram,
                            "count": len(positions),
                            "suggestion": f"Phrase repeated {len(positions)} times",
                            "severity": "high",
                        })
                        break  # Only report first major repetition

        return issues

    def _detect_abbreviations(self, text: str) -> List[Dict[str, Any]]:
        """Detect common abbreviations."""
        issues = []

        for pattern, expansion in self._abbrev_patterns:
            for match in pattern.finditer(text):
                issues.append({
                    "type": "abbreviation",
                    "match": match.group(),
                    "position": match.start(),
                    "expansion": expansion,
                    "suggestion": f"Expand '{match.group()}' to '{expansion}'",
                    "severity": "low",
                })

        return issues

    def _summarize_issues(self, issues: List[Dict[str, Any]]) -> str:
        """Create a human-readable summary of issues."""
        if not issues:
            return "No TTS issues detected"

        type_counts = {}
        for issue in issues:
            issue_type = issue["type"]
            type_counts[issue_type] = type_counts.get(issue_type, 0) + 1

        parts = [f"{count} {issue_type}" for issue_type, count in type_counts.items()]
        return f"Found: {', '.join(parts)}"

    def _get_llm_suggestions(
        self,
        text: str,
        issues: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Use LLM to suggest text improvements."""
        fallback = {
            "suggested_text": None,
            "confidence": 0.0,
            "notes": "LLM unavailable",
        }

        # Format issues for prompt
        issue_summary = "\n".join([
            f"- {i['type']}: '{i['match']}' - {i['suggestion']}"
            for i in issues[:5]  # Limit to top 5
        ])

        prompt = (
            "You are preprocessing text for TTS (text-to-speech) synthesis.\n\n"
            "**Original Text:**\n"
            f"{text}\n\n"
            "**Detected Issues:**\n"
            f"{issue_summary}\n\n"
            "**Your Task:**\n"
            "Rewrite the text to be TTS-friendly:\n"
            "1. Expand ALL abbreviations and acronyms to full words\n"
            "2. Convert numbers, percentages, and currency to spoken form\n"
            "3. Replace em-dashes with commas or periods\n"
            "4. Remove or simplify ellipses\n"
            "5. Break very long sentences into shorter ones\n"
            "6. Preserve the original meaning completely\n\n"
            "Respond with JSON:\n"
            "{\n"
            '  "suggested_text": "The rewritten text...",\n'
            '  "notes": "What you changed and why",\n'
            '  "confidence": 0.0-1.0\n'
            "}"
        )

        try:
            response = self.query_json(prompt, max_tokens=600, temperature=0.2)
        except Exception as exc:
            logger.warning("LlamaPreValidator LLM query failed: %s", exc)
            fallback["notes"] = f"LLM error: {exc}"
            return fallback

        if not isinstance(response, dict) or response.get("error"):
            note = response.get("error") if isinstance(response, dict) else "Invalid response"
            fallback["notes"] = note
            return fallback

        suggested = response.get("suggested_text")
        if not suggested:
            fallback["notes"] = "LLM returned no suggestion"
            return fallback

        try:
            confidence = float(response.get("confidence", 0.0))
        except (TypeError, ValueError):
            confidence = 0.5

        return {
            "suggested_text": str(suggested),
            "confidence": max(0.0, min(1.0, confidence)),
            "notes": str(response.get("notes", "")),
        }

    def quick_check(self, text: str) -> Tuple[bool, List[str]]:
        """
        Fast pattern-only check without LLM (for batch pre-filtering).

        Returns:
            Tuple of (is_clean, list of issue types found)
        """
        issue_types = set()

        for pattern_name, pattern in PATTERNS.items():
            if pattern.search(text):
                issue_types.add(pattern_name)

        # Check for acronyms (more expensive)
        if PATTERNS["acronym"].search(text):
            safe = {"OK", "TV", "US", "UK", "EU", "UN", "AM", "PM", "AD", "BC"}
            acronyms = PATTERNS["acronym"].findall(text)
            if any(a not in safe for a in acronyms):
                issue_types.add("acronym")

        return len(issue_types) == 0, list(issue_types)

    def auto_expand_abbreviations(self, text: str) -> str:
        """
        Automatically expand common abbreviations without LLM.

        This is a fast preprocessing step that can be applied before TTS.
        """
        result = text
        for pattern, expansion in self._abbrev_patterns:
            result = pattern.sub(expansion, result)
        return result

    def expand_numbers(self, text: str, language: str = "en") -> str:
        """
        Convert numbers to their spoken word forms for TTS.

        Post-Coqui Era Fix: Neural TTS models often misread digits (e.g., "1995"
        as "one nine nine five" instead of "nineteen ninety-five"). Using num2words
        ensures correct pronunciation.

        Args:
            text: Text containing numbers
            language: Language code for num2words

        Returns:
            Text with numbers converted to words
        """
        result = text

        # Handle years (1800-2099) - special spoken form
        def convert_year(match):
            year = int(match.group())
            if NUM2WORDS_AVAILABLE:
                try:
                    return num2words(year, to='year', lang=language)
                except Exception:
                    pass
            # Fallback for years
            if 1000 <= year <= 1099:
                return f"{year // 100} hundred {num2words(year % 100) if NUM2WORDS_AVAILABLE else year % 100}"
            elif 1100 <= year <= 1999:
                first = year // 100
                second = year % 100
                if NUM2WORDS_AVAILABLE:
                    try:
                        return f"{num2words(first, lang=language)} {num2words(second, lang=language) if second else 'hundred'}"
                    except Exception:
                        pass
                return str(year)
            elif 2000 <= year <= 2009:
                return f"two thousand {num2words(year - 2000, lang=language) if NUM2WORDS_AVAILABLE and year > 2000 else ''}"
            elif 2010 <= year <= 2099:
                if NUM2WORDS_AVAILABLE:
                    try:
                        return f"twenty {num2words(year - 2000, lang=language)}"
                    except Exception:
                        pass
            return str(year)

        result = re.sub(r'\b(1[89]\d{2}|20\d{2})\b', convert_year, result)

        # Handle ordinals (1st, 2nd, 3rd, 4th, etc.)
        def convert_ordinal(match):
            num = int(match.group(1))
            if NUM2WORDS_AVAILABLE:
                try:
                    return num2words(num, to='ordinal', lang=language)
                except Exception:
                    pass
            # Simple fallback
            ordinals = {1: "first", 2: "second", 3: "third", 4: "fourth", 5: "fifth",
                       6: "sixth", 7: "seventh", 8: "eighth", 9: "ninth", 10: "tenth"}
            return ordinals.get(num, f"{num}th")

        result = re.sub(r'\b(\d+)(?:st|nd|rd|th)\b', convert_ordinal, result)

        # Handle currency amounts
        def convert_currency(match):
            symbol = match.group(1)
            amount = match.group(2).replace(',', '')
            multiplier = match.group(3) or ''

            currency_names = {'$': 'dollars', '£': 'pounds', '€': 'euros', '¥': 'yen'}
            currency = currency_names.get(symbol, 'dollars')

            try:
                value = float(amount)
            except ValueError:
                return match.group()

            # Handle multipliers
            if multiplier.upper() == 'M':
                value *= 1_000_000
            elif multiplier.upper() == 'B':
                value *= 1_000_000_000
            elif multiplier.upper() == 'K':
                value *= 1_000

            if NUM2WORDS_AVAILABLE:
                try:
                    if value >= 1_000_000_000:
                        return f"{num2words(value / 1_000_000_000, lang=language)} billion {currency}"
                    elif value >= 1_000_000:
                        return f"{num2words(value / 1_000_000, lang=language)} million {currency}"
                    else:
                        return f"{num2words(int(value), lang=language)} {currency}"
                except Exception:
                    pass

            return match.group()

        result = re.sub(r'([$€£¥])\s*([\d,]+(?:\.\d+)?)\s*([MBKmbk])?', convert_currency, result)

        # Handle percentages
        def convert_percentage(match):
            num = match.group(1)
            try:
                value = float(num)
                if NUM2WORDS_AVAILABLE:
                    if value == int(value):
                        return f"{num2words(int(value), lang=language)} percent"
                    else:
                        return f"{num2words(value, lang=language)} percent"
                return f"{num} percent"
            except (ValueError, Exception):
                return match.group()

        result = re.sub(r'(\d+(?:\.\d+)?)\s*%', convert_percentage, result)

        # Handle remaining standalone numbers (cardinals)
        def convert_cardinal(match):
            num_str = match.group().replace(',', '')
            try:
                value = int(num_str)
                if NUM2WORDS_AVAILABLE:
                    return num2words(value, lang=language)
                # Fallback for small numbers
                if value <= 20:
                    small = ['zero', 'one', 'two', 'three', 'four', 'five', 'six',
                            'seven', 'eight', 'nine', 'ten', 'eleven', 'twelve',
                            'thirteen', 'fourteen', 'fifteen', 'sixteen', 'seventeen',
                            'eighteen', 'nineteen', 'twenty']
                    return small[value]
                return num_str
            except (ValueError, Exception):
                return match.group()

        # Only convert standalone numbers (not parts of larger patterns already handled)
        result = re.sub(r'\b\d{1,3}(?:,\d{3})*\b', convert_cardinal, result)

        return result

    def normalize_punctuation(self, text: str) -> str:
        """
        Normalize TTS-hostile punctuation to friendly alternatives.

        Post-Coqui Era Fix: XTTS struggles with em-dashes, semicolons, and complex
        punctuation, causing long pauses or hallucinations.

        Returns:
            Text with normalized punctuation
        """
        result = text

        # Em-dash → comma (preserves pause without confusion)
        result = re.sub(r'\s*[—–]\s*', ', ', result)
        result = re.sub(r'\s*--\s*', ', ', result)

        # Semicolon → period (stronger boundary)
        result = result.replace(';', '.')

        # Ellipsis → single period
        result = re.sub(r'\.{2,}', '.', result)
        result = result.replace('…', '.')

        # Multiple exclamation/question → single
        result = re.sub(r'([!?]){2,}', r'\1', result)

        # Smart quotes → straight quotes
        result = result.replace('"', '"').replace('"', '"')
        result = result.replace(''', "'").replace(''', "'")

        # Remove parenthetical asides (optional - can be aggressive)
        # result = re.sub(r'\([^)]{1,50}\)', '', result)

        # Clean up multiple spaces
        result = re.sub(r'\s+', ' ', result)

        return result.strip()

    def preprocess_for_tts(
        self,
        text: str,
        expand_abbreviations: bool = True,
        expand_numbers: bool = True,
        normalize_punctuation: bool = True,
        check_pronunciation: bool = True,
    ) -> str:
        """
        Apply all TTS preprocessing in recommended order.

        This is the main entry point for automatic text preprocessing
        before TTS synthesis.

        Args:
            text: Raw text to preprocess
            expand_abbreviations: Whether to expand abbreviations
            expand_numbers: Whether to convert numbers to words
            normalize_punctuation: Whether to normalize punctuation
            check_pronunciation: Whether to check for and generate pronunciations

        Returns:
            TTS-ready text
        """
        result = text

        if check_pronunciation:
            pronunciation_assistant = LlamaPronunciationAssistant()
            pronunciation_assistant.process_text(result)

        if expand_abbreviations:
            result = self.auto_expand_abbreviations(result)

        if expand_numbers:
            result = self.expand_numbers(result)

        if normalize_punctuation:
            result = self.normalize_punctuation(result)

        return result
