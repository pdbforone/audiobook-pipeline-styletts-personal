"""
TTS Text Normalization Module

Normalizes "TTS-unfriendly" text patterns before synthesis to prevent:
- Duration mismatches from OOD (Out-Of-Distribution) symbols
- G2P alignment failures from currency, percentages, abbreviations
- Unpredictable pausing from em-dashes and ellipses

Based on Gemini Deep Research findings:
"Raw text is the primary enemy of stable TTS. Normalize TTS-unfriendly patterns
before they reach the engine."

Reference: TTS_VALIDATION_RESEARCH_FINDINGS.md
"""

import logging
import re
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Try to import num2words for number expansion
NUM2WORDS_AVAILABLE = False
try:
    from num2words import num2words
    NUM2WORDS_AVAILABLE = True
    logger.debug("✅ num2words available for number expansion")
except ImportError:
    logger.warning("⚠️  num2words not installed - using basic number expansion")


# ---------------------------------------------------------------------------
# Currency and Symbol Expansion
# ---------------------------------------------------------------------------

CURRENCY_SYMBOLS = {
    "$": "dollars",
    "€": "euros",
    "£": "pounds",
    "¥": "yen",
    "₹": "rupees",
    "₽": "rubles",
    "₿": "bitcoin",
}

CURRENCY_PATTERN = re.compile(
    r'([€£¥₹₽₿$])(\d+(?:,\d{3})*(?:\.\d{1,2})?)'
)

PERCENT_PATTERN = re.compile(r'(\d+(?:\.\d+)?)\s*%')


def expand_currency(text: str) -> str:
    """
    Expand currency symbols to words.

    Examples:
        "$100" -> "one hundred dollars"
        "€50.99" -> "fifty euros and ninety-nine cents"
        "$1,000,000" -> "one million dollars"
    """
    def replace_currency(match):
        symbol = match.group(1)
        amount_str = match.group(2).replace(",", "")

        currency_name = CURRENCY_SYMBOLS.get(symbol, "units")

        try:
            amount = float(amount_str)
            if amount == int(amount):
                # Whole number
                if NUM2WORDS_AVAILABLE:
                    amount_words = num2words(int(amount))
                else:
                    amount_words = _basic_number_to_words(int(amount))
                return f"{amount_words} {currency_name}"
            else:
                # Has cents/decimal
                dollars = int(amount)
                cents = int(round((amount - dollars) * 100))

                if NUM2WORDS_AVAILABLE:
                    dollar_words = num2words(dollars)
                    cent_words = num2words(cents)
                else:
                    dollar_words = _basic_number_to_words(dollars)
                    cent_words = _basic_number_to_words(cents)

                if symbol == "$":
                    return f"{dollar_words} dollars and {cent_words} cents"
                elif symbol == "€":
                    return f"{dollar_words} euros and {cent_words} cents"
                elif symbol == "£":
                    return f"{dollar_words} pounds and {cent_words} pence"
                else:
                    return f"{dollar_words} point {cent_words} {currency_name}"
        except (ValueError, TypeError):
            return match.group(0)  # Return original if parsing fails

    return CURRENCY_PATTERN.sub(replace_currency, text)


def expand_percentages(text: str) -> str:
    """
    Expand percentage symbols to words.

    Examples:
        "25%" -> "twenty-five percent"
        "3.14%" -> "three point one four percent"
    """
    def replace_percent(match):
        number_str = match.group(1)
        try:
            number = float(number_str)
            if number == int(number):
                if NUM2WORDS_AVAILABLE:
                    number_words = num2words(int(number))
                else:
                    number_words = _basic_number_to_words(int(number))
            else:
                # Decimal percentage
                parts = number_str.split(".")
                whole = int(parts[0])
                decimal = parts[1]

                if NUM2WORDS_AVAILABLE:
                    whole_words = num2words(whole)
                    decimal_words = " ".join(num2words(int(d)) for d in decimal)
                else:
                    whole_words = _basic_number_to_words(whole)
                    decimal_words = " ".join(_basic_number_to_words(int(d)) for d in decimal)

                number_words = f"{whole_words} point {decimal_words}"

            return f"{number_words} percent"
        except (ValueError, TypeError):
            return match.group(0)

    return PERCENT_PATTERN.sub(replace_percent, text)


def _basic_number_to_words(n: int) -> str:
    """Basic number to words conversion without external dependencies."""
    if n < 0:
        return "negative " + _basic_number_to_words(-n)

    ones = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine",
            "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen",
            "seventeen", "eighteen", "nineteen"]
    tens = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]

    if n < 20:
        return ones[n]
    elif n < 100:
        if n % 10 == 0:
            return tens[n // 10]
        return f"{tens[n // 10]}-{ones[n % 10]}"
    elif n < 1000:
        if n % 100 == 0:
            return f"{ones[n // 100]} hundred"
        return f"{ones[n // 100]} hundred {_basic_number_to_words(n % 100)}"
    elif n < 1000000:
        thousands = n // 1000
        remainder = n % 1000
        if remainder == 0:
            return f"{_basic_number_to_words(thousands)} thousand"
        return f"{_basic_number_to_words(thousands)} thousand {_basic_number_to_words(remainder)}"
    elif n < 1000000000:
        millions = n // 1000000
        remainder = n % 1000000
        if remainder == 0:
            return f"{_basic_number_to_words(millions)} million"
        return f"{_basic_number_to_words(millions)} million {_basic_number_to_words(remainder)}"
    else:
        billions = n // 1000000000
        remainder = n % 1000000000
        if remainder == 0:
            return f"{_basic_number_to_words(billions)} billion"
        return f"{_basic_number_to_words(billions)} billion {_basic_number_to_words(remainder)}"


# ---------------------------------------------------------------------------
# Punctuation Normalization
# ---------------------------------------------------------------------------

def normalize_punctuation(text: str) -> str:
    """
    Normalize problematic punctuation for TTS engines.

    Research finding: Em-dashes (—) and ellipses (...) often cause:
    - Unpredictable pause durations
    - G2P alignment failures
    - Duration mismatches

    Examples:
        "Wait—what?" -> "Wait, what?"
        "Well..." -> "Well."
        "He said—and I quote—" -> "He said, and I quote,"
    """
    # Em-dash to comma (preserves pause intent without confusing G2P)
    text = re.sub(r'—', ', ', text)
    text = re.sub(r'–', ', ', text)  # En-dash too

    # Ellipsis to period (or comma for mid-sentence)
    # Mid-sentence ellipsis (followed by lowercase)
    text = re.sub(r'\.\.\.(?=\s+[a-z])', ',', text)
    # End-of-sentence ellipsis
    text = re.sub(r'\.\.\.', '.', text)
    text = re.sub(r'…', '.', text)  # Unicode ellipsis

    # Multiple exclamation/question marks
    text = re.sub(r'[!]{2,}', '!', text)
    text = re.sub(r'[?]{2,}', '?', text)
    text = re.sub(r'[!?]{2,}', '?!', text)

    # Clean up double spaces from substitutions
    text = re.sub(r'\s{2,}', ' ', text)
    text = re.sub(r'\s+,', ',', text)  # Remove space before comma

    return text


# ---------------------------------------------------------------------------
# Abbreviation Expansion
# ---------------------------------------------------------------------------

# Common abbreviations that cause TTS issues
ABBREVIATIONS = {
    # Titles
    "Dr.": "Doctor",
    "Mr.": "Mister",
    "Mrs.": "Missus",
    "Ms.": "Ms",
    "Prof.": "Professor",
    "Sr.": "Senior",
    "Jr.": "Junior",
    "Rev.": "Reverend",

    # Academic/Professional
    "Ph.D.": "PhD",
    "Ph.D": "PhD",
    "M.D.": "MD",
    "M.D": "MD",
    "B.A.": "BA",
    "B.S.": "BS",
    "M.A.": "MA",
    "M.S.": "MS",
    "J.D.": "JD",
    "Esq.": "Esquire",

    # Common
    "etc.": "et cetera",
    "i.e.": "that is",
    "e.g.": "for example",
    "vs.": "versus",
    "vs": "versus",
    "approx.": "approximately",
    "est.": "established",

    # Time
    "a.m.": "AM",
    "p.m.": "PM",
    "A.M.": "AM",
    "P.M.": "PM",

    # Geographic
    "St.": "Street",  # Context-dependent, may need "Saint"
    "Ave.": "Avenue",
    "Blvd.": "Boulevard",
    "Rd.": "Road",
    "Apt.": "Apartment",
    "Mt.": "Mount",

    # Measurement (keep these short for TTS)
    "ft.": "feet",
    "in.": "inches",
    "lb.": "pounds",
    "lbs.": "pounds",
    "oz.": "ounces",
    "mi.": "miles",
    "yr.": "year",
    "yrs.": "years",
    "mo.": "month",
    "mos.": "months",

    # US States (common abbreviations)
    "U.S.": "US",
    "U.S.A.": "USA",
    "U.K.": "UK",
}

# Context-aware abbreviation patterns
# "St." before a name = "Saint", before a street type = "Street"
SAINT_PATTERN = re.compile(r'\bSt\.\s+([A-Z][a-z]+)(?!\s+(?:Street|Ave|Avenue|Rd|Road|Blvd))')


def expand_abbreviations(text: str, context_aware: bool = True) -> str:
    """
    Expand common abbreviations to full words.

    Args:
        text: Input text
        context_aware: If True, use context to disambiguate (e.g., St. Paul vs St. Main Street)

    Returns:
        Text with abbreviations expanded
    """
    result = text

    # Context-aware: "St." before a name (not street)
    if context_aware:
        result = SAINT_PATTERN.sub(r'Saint \1', result)

    # Direct replacements
    for abbrev, expansion in ABBREVIATIONS.items():
        # Word boundary aware replacement
        pattern = re.compile(re.escape(abbrev) + r'(?=\s|$|[,;:\'")\]])', re.IGNORECASE)
        result = pattern.sub(expansion, result)

    return result


# ---------------------------------------------------------------------------
# Number Normalization
# ---------------------------------------------------------------------------

# Ordinal patterns: 1st, 2nd, 3rd, 4th, etc.
ORDINAL_PATTERN = re.compile(r'\b(\d+)(st|nd|rd|th)\b', re.IGNORECASE)

# Standalone numbers (not part of larger context like dates, times)
STANDALONE_NUMBER_PATTERN = re.compile(r'\b(\d{1,3}(?:,\d{3})*)\b(?![.:]?\d)')


def expand_ordinals(text: str) -> str:
    """
    Expand ordinal numbers to words.

    Examples:
        "1st" -> "first"
        "2nd" -> "second"
        "21st" -> "twenty-first"
    """
    ORDINAL_WORDS = {
        1: "first", 2: "second", 3: "third", 4: "fourth", 5: "fifth",
        6: "sixth", 7: "seventh", 8: "eighth", 9: "ninth", 10: "tenth",
        11: "eleventh", 12: "twelfth", 13: "thirteenth", 14: "fourteenth",
        15: "fifteenth", 16: "sixteenth", 17: "seventeenth", 18: "eighteenth",
        19: "nineteenth", 20: "twentieth", 21: "twenty-first", 22: "twenty-second",
        23: "twenty-third", 30: "thirtieth", 31: "thirty-first",
    }

    def replace_ordinal(match):
        number = int(match.group(1))
        if number in ORDINAL_WORDS:
            return ORDINAL_WORDS[number]
        elif NUM2WORDS_AVAILABLE:
            try:
                return num2words(number, ordinal=True)
            except Exception:
                return match.group(0)
        else:
            return match.group(0)  # Keep original if no good expansion

    return ORDINAL_PATTERN.sub(replace_ordinal, text)


def expand_standalone_numbers(text: str, max_digits: int = 4) -> str:
    """
    Expand standalone numbers to words.

    Only expands numbers that are:
    - Not part of dates, times, or phone numbers
    - Within the specified digit limit

    Args:
        text: Input text
        max_digits: Maximum number of digits to expand (default: 4)

    Examples:
        "There were 100 people" -> "There were one hundred people"
        "In 2024" -> "In 2024" (preserved as likely a year)
    """
    def replace_number(match):
        number_str = match.group(1).replace(",", "")
        if len(number_str) > max_digits:
            return match.group(0)  # Too long, keep original

        try:
            number = int(number_str)
            # Skip years (4-digit numbers starting with 1 or 2)
            if len(number_str) == 4 and number_str[0] in "12":
                return match.group(0)

            if NUM2WORDS_AVAILABLE:
                return num2words(number)
            else:
                return _basic_number_to_words(number)
        except (ValueError, TypeError):
            return match.group(0)

    return STANDALONE_NUMBER_PATTERN.sub(replace_number, text)


# ---------------------------------------------------------------------------
# Main Normalization Function
# ---------------------------------------------------------------------------

def normalize_for_tts(
    text: str,
    expand_currency_symbols: bool = True,
    expand_percentage_symbols: bool = True,
    normalize_punct: bool = True,
    expand_abbrevs: bool = True,
    expand_ordinal_numbers: bool = True,
    expand_numbers: bool = False,  # Conservative default
    context_aware: bool = True,
) -> Tuple[str, Dict[str, int]]:
    """
    Apply full TTS normalization pipeline to text.

    This function prepares text for TTS synthesis by expanding symbols and
    normalizing patterns that commonly cause issues.

    Args:
        text: Input text to normalize
        expand_currency_symbols: Expand $, €, etc. to words
        expand_percentage_symbols: Expand % to "percent"
        normalize_punct: Normalize em-dashes, ellipses
        expand_abbrevs: Expand Dr., Mr., etc.
        expand_ordinal_numbers: Expand 1st, 2nd, etc.
        expand_numbers: Expand standalone numbers (conservative)
        context_aware: Use context for ambiguous cases

    Returns:
        Tuple of (normalized_text, metrics_dict)
    """
    if not text:
        return text, {"changes": 0}

    original = text
    metrics = {
        "currency_expansions": 0,
        "percentage_expansions": 0,
        "punctuation_changes": 0,
        "abbreviation_expansions": 0,
        "ordinal_expansions": 0,
        "number_expansions": 0,
    }

    # Apply normalizations in order
    if expand_currency_symbols:
        before = text
        text = expand_currency(text)
        metrics["currency_expansions"] = len(before) != len(text)

    if expand_percentage_symbols:
        before = text
        text = expand_percentages(text)
        metrics["percentage_expansions"] = len(before) != len(text)

    if normalize_punct:
        before = text
        text = normalize_punctuation(text)
        metrics["punctuation_changes"] = before != text

    if expand_abbrevs:
        before = text
        text = expand_abbreviations(text, context_aware=context_aware)
        metrics["abbreviation_expansions"] = before != text

    if expand_ordinal_numbers:
        before = text
        text = expand_ordinals(text)
        metrics["ordinal_expansions"] = before != text

    if expand_numbers:
        before = text
        text = expand_standalone_numbers(text)
        metrics["number_expansions"] = before != text

    # Calculate total changes
    metrics["changes"] = sum(1 for k, v in metrics.items() if k != "changes" and v)
    metrics["text_changed"] = original != text

    if metrics["text_changed"]:
        logger.debug(
            f"Text normalization applied: {metrics['changes']} change types "
            f"(currency={metrics['currency_expansions']}, "
            f"percent={metrics['percentage_expansions']}, "
            f"punct={metrics['punctuation_changes']}, "
            f"abbrev={metrics['abbreviation_expansions']})"
        )

    return text, metrics


# ---------------------------------------------------------------------------
# Batch Processing
# ---------------------------------------------------------------------------

def normalize_chunks(
    chunks: List[str],
    **kwargs
) -> Tuple[List[str], List[Dict[str, int]]]:
    """
    Normalize a list of text chunks for TTS.

    Args:
        chunks: List of text chunks
        **kwargs: Arguments to pass to normalize_for_tts()

    Returns:
        Tuple of (normalized_chunks, metrics_list)
    """
    normalized = []
    metrics_list = []

    for chunk in chunks:
        norm_text, metrics = normalize_for_tts(chunk, **kwargs)
        normalized.append(norm_text)
        metrics_list.append(metrics)

    total_changed = sum(1 for m in metrics_list if m.get("text_changed"))
    logger.info(
        f"Normalized {len(chunks)} chunks: {total_changed} modified"
    )

    return normalized, metrics_list
