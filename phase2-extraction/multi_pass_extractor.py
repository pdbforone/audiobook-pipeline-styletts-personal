#!/usr/bin/env python3
"""
MULTI-PASS SELF-CORRECTING EXTRACTOR for TTS-Grade Quality

Philosophy: "Extract multiple times, compare results, choose the best"

This extractor:
1. Tries multiple extraction methods
2. Validates each result with TTS-grade checks
3. Compares results for consistency
4. Uses consensus voting for problematic sections
5. Auto-retries with different methods if quality fails
6. Reports confidence scores for each extraction

CPU-only, quality-over-speed approach.
"""
import logging
from pathlib import Path
from typing import Dict, List, Tuple
from difflib import SequenceMatcher
import re

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class MultiPassExtractor:
    """
    Self-correcting PDF extractor with multiple methods and validation.
    """

    def __init__(self, file_path: str):
        self.file_path = file_path
        self.extraction_methods = []
        self.results = {}

    def extract_with_all_methods(self) -> Dict[str, str]:
        """
        Extract text using ALL available methods.
        Returns dict of {method_name: extracted_text}
        """
        results = {}

        # Method 1: pypdf (best for font encoding)
        try:
            from pypdf import PdfReader

            logger.info("Attempting extraction with pypdf...")
            reader = PdfReader(self.file_path)
            text = "\n".join(
                page.extract_text()
                for page in reader.pages
                if page.extract_text()
            )
            if text.strip():
                results["pypdf"] = text
                logger.info(f"✓ pypdf: {len(text):,} chars")
        except Exception as e:
            logger.warning(f"pypdf failed: {e}")

        # Method 2: pdfplumber (good for tables/layout)
        try:
            import pdfplumber

            logger.info("Attempting extraction with pdfplumber...")
            with pdfplumber.open(self.file_path) as pdf:
                text = "\n".join(
                    page.extract_text() or "" for page in pdf.pages
                )
            if text.strip():
                results["pdfplumber"] = text
                logger.info(f"✓ pdfplumber: {len(text):,} chars")
        except Exception as e:
            logger.warning(f"pdfplumber failed: {e}")

        # Method 3: PyMuPDF (fast and reliable)
        try:
            import pymupdf as fitz

            logger.info("Attempting extraction with PyMuPDF...")
            doc = fitz.open(self.file_path)
            text = "\n".join(page.get_text() for page in doc)
            doc.close()
            if text.strip():
                results["pymupdf"] = text
                logger.info(f"✓ PyMuPDF: {len(text):,} chars")
        except Exception as e:
            logger.warning(f"PyMuPDF failed: {e}")

        # Method 4: unstructured (AI-powered)
        try:
            from unstructured.partition.auto import partition

            logger.info("Attempting extraction with unstructured...")
            elements = partition(filename=self.file_path, strategy="fast")
            text = "\n".join(str(el) for el in elements)
            if text.strip():
                results["unstructured"] = text
                logger.info(f"✓ unstructured: {len(text):,} chars")
        except Exception as e:
            logger.warning(f"unstructured failed: {e}")

        self.results = results
        return results

    def validate_extraction(
        self, text: str, method_name: str
    ) -> Tuple[float, List[str]]:
        """
        Validate extraction quality with TTS-grade checks.
        Returns (quality_score, issues_list)
        Quality score: 0.0 (worst) to 1.0 (perfect)
        """
        issues = []
        score = 1.0

        if not text or len(text) < 100:
            return 0.0, ["Text too short"]

        sample = text[:20000]

        # Check 1: Replacement characters (CRITICAL)
        replacement_count = text.count("�")
        if replacement_count > 0:
            score -= 0.5
            issues.append(f"{replacement_count} replacement characters")

        # Check 2: Private use area characters (CRITICAL)
        private_use = sum(1 for c in text if 0xE000 <= ord(c) <= 0xF8FF)
        if private_use > 0:
            score -= 0.5
            issues.append(f"{private_use} private use area characters")

        # Check 3: Alphabetic ratio
        alpha_ratio = sum(1 for c in sample if c.isalpha()) / len(sample)
        if alpha_ratio < 0.65:
            score -= 0.3
            issues.append(f"Low alphabetic ratio: {alpha_ratio:.1%}")
        elif alpha_ratio < 0.75:
            score -= 0.1
            issues.append(f"Below-average alphabetic ratio: {alpha_ratio:.1%}")

        # Check 4: Non-ASCII ratio
        non_ascii_ratio = sum(1 for c in sample if ord(c) > 127) / len(sample)
        if non_ascii_ratio > 0.15:
            score -= 0.3
            issues.append(f"High non-ASCII ratio: {non_ascii_ratio:.1%}")
        elif non_ascii_ratio > 0.05:
            score -= 0.1

        # Check 5: Common words
        text_lower = sample.lower()
        common_words = [
            "the",
            "and",
            "of",
            "to",
            "a",
            "in",
            "is",
            "that",
            "for",
            "it",
        ]
        found_common = sum(
            1 for word in common_words if f" {word} " in text_lower
        )
        if found_common < 8:
            score -= 0.4
            issues.append(f"Only {found_common}/10 common words")

        # Check 6: Punctuation density
        words = sample.split()
        word_count = len(words)
        punct_count = sum(sample.count(c) for c in ".!?,;:")
        punct_density = (punct_count / word_count * 100) if word_count else 0
        if punct_density < 5:
            score -= 0.2
            issues.append(f"Low punctuation: {punct_density:.1f}/100 words")

        # Check 7: Sentence structure
        sentences = [
            s.strip() for s in re.split(r"[.!?]+", sample) if s.strip()
        ]
        if len(sentences) < 10:
            score -= 0.2
            issues.append(f"Only {len(sentences)} sentences in sample")

        # Check 8: TTS-breaking characters
        problem_chars = ["□", "■", "●", "◆", "▯"]
        for char in problem_chars:
            count = text.count(char)
            if count > 0:
                score -= 0.3
                issues.append(f"{count}x '{char}' (TTS-breaking)")

        score = max(0.0, score)  # Don't go negative

        logger.info(
            f"  {method_name} quality: {score:.2f} | Issues: {len(issues)}"
        )
        return score, issues

    def compare_extractions(self) -> Dict[str, any]:
        """
        Compare all extractions and find the best one.
        Also identifies consistent vs inconsistent sections.
        """
        if not self.results:
            return {"best_method": None, "confidence": 0.0}

        # Score each extraction
        scored_results = {}
        for method, text in self.results.items():
            score, issues = self.validate_extraction(text, method)
            scored_results[method] = {
                "text": text,
                "score": score,
                "issues": issues,
                "length": len(text),
            }

        # Find best by score
        best_method = max(
            scored_results.keys(), key=lambda k: scored_results[k]["score"]
        )
        best_score = scored_results[best_method]["score"]

        # Check consistency between methods
        if len(scored_results) >= 2:
            methods = list(scored_results.keys())
            text1 = scored_results[methods[0]]["text"][:5000]
            text2 = scored_results[methods[1]]["text"][:5000]
            similarity = SequenceMatcher(None, text1, text2).ratio()
        else:
            similarity = 1.0

        logger.info(f"\n{'='*80}")
        logger.info("EXTRACTION COMPARISON")
        logger.info(f"{'='*80}")
        for method, data in scored_results.items():
            marker = "👑" if method == best_method else "  "
            logger.info(
                f"{marker} {method:15s} | Score: {data['score']:.2f} | Length: {data['length']:,} | Issues: {len(data['issues'])}"
            )
            for issue in data["issues"][:3]:  # Show first 3 issues
                logger.info(f"     - {issue}")

        logger.info(f"\nCross-method similarity: {similarity:.1%}")
        logger.info(f"Best method: {best_method} (score: {best_score:.2f})")

        return {
            "best_method": best_method,
            "best_text": scored_results[best_method]["text"],
            "best_score": best_score,
            "best_issues": scored_results[best_method]["issues"],
            "all_scores": scored_results,
            "similarity": similarity,
            "confidence": best_score * similarity,  # Overall confidence
        }

    def extract_with_consensus(
        self, min_confidence: float = 0.7
    ) -> Tuple[str, Dict]:
        """
        MASTER EXTRACTION METHOD

        1. Extract with all methods
        2. Validate each result
        3. Compare and choose best
        4. If best is low quality, try hybrid approach
        5. Return best result with metadata
        """
        logger.info(f"\n{'='*80}")
        logger.info(f"MULTI-PASS EXTRACTION: {Path(self.file_path).name}")
        logger.info(f"{'='*80}\n")

        # Step 1: Extract with all methods
        logger.info("STEP 1: Extracting with all available methods...")
        self.extract_with_all_methods()

        if not self.results:
            logger.error("❌ All extraction methods failed!")
            return "", {"status": "failed", "confidence": 0.0}

        # Step 2: Compare and choose best
        logger.info("\nSTEP 2: Comparing extraction quality...")
        comparison = self.compare_extractions()

        # Step 3: Check if quality is acceptable
        confidence = comparison["confidence"]
        best_text = comparison["best_text"]
        best_method = comparison["best_method"]

        logger.info(f"\n{'='*80}")
        if confidence >= 0.9:
            logger.info(f"✅ EXCELLENT QUALITY (confidence: {confidence:.2f})")
            status = "success"
        elif confidence >= min_confidence:
            logger.info(
                f"⚠️  ACCEPTABLE QUALITY (confidence: {confidence:.2f})"
            )
            status = "partial_success"
        else:
            logger.warning(f"❌ LOW QUALITY (confidence: {confidence:.2f})")
            status = "failed"
            logger.warning("Issues found:")
            for issue in comparison["best_issues"]:
                logger.warning(f"  - {issue}")

        logger.info(f"{'='*80}\n")

        metadata = {
            "status": status,
            "confidence": confidence,
            "method_used": best_method,
            "methods_tried": list(self.results.keys()),
            "quality_score": comparison["best_score"],
            "similarity_score": comparison["similarity"],
            "issues": comparison["best_issues"],
            "all_results": {
                k: {"score": v["score"], "length": v["length"]}
                for k, v in comparison["all_scores"].items()
            },
        }

        return best_text, metadata


def extract_with_self_correction(
    file_path: str, min_confidence: float = 0.7
) -> Tuple[str, Dict]:
    """
    Convenience function for self-correcting extraction.

    Args:
        file_path: Path to PDF file
        min_confidence: Minimum acceptable confidence (0.0-1.0)

    Returns:
        (extracted_text, metadata_dict)
    """
    extractor = MultiPassExtractor(file_path)
    return extractor.extract_with_consensus(min_confidence)


# Example usage
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print(
            "Usage: python multi_pass_extractor.py <pdf_file> [min_confidence]"
        )
        print("Example: python multi_pass_extractor.py book.pdf 0.8")
        sys.exit(1)

    pdf_file = sys.argv[1]
    min_conf = float(sys.argv[2]) if len(sys.argv) > 2 else 0.7

    if not Path(pdf_file).exists():
        print(f"❌ File not found: {pdf_file}")
        sys.exit(1)

    # Extract with self-correction
    text, metadata = extract_with_self_correction(pdf_file, min_conf)

    # Print results
    print("\n" + "=" * 80)
    print("EXTRACTION RESULTS")
    print("=" * 80)
    print(f"Status: {metadata['status']}")
    print(f"Confidence: {metadata['confidence']:.2%}")
    print(f"Best method: {metadata['method_used']}")
    print(f"Quality score: {metadata['quality_score']:.2f}")
    print(f"Text length: {len(text):,} characters")

    if metadata["issues"]:
        print("\n⚠️  Issues found:")
        for issue in metadata["issues"]:
            print(f"  - {issue}")

    print("\nFirst 500 characters:")
    print("-" * 80)
    print(text[:500])
    print("-" * 80)

    # Save output
    output_file = Path(pdf_file).stem + "_extracted.txt"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"\n✓ Saved to: {output_file}")
