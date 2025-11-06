#!/usr/bin/env python3
"""
CONSENSUS VOTING EXTRACTOR - Advanced Self-Correction

Goes beyond multi-pass by:
1. Extracting page-by-page with multiple methods
2. Comparing results for each page
3. Using consensus voting when methods disagree
4. Identifying and re-extracting problematic pages
5. OCR fallback for unreadable pages

This is the "work harder and check your work" approach.
"""
import logging
from pathlib import Path
from typing import Dict, List, Tuple
from difflib import SequenceMatcher
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ConsensusExtractor:
    """
    Page-by-page extraction with consensus voting.
    """
    
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.page_count = 0
        self.page_results = {}  # {page_num: {method: text}}
        
    def get_page_count(self) -> int:
        """Get total number of pages in PDF."""
        try:
            import pymupdf as fitz
            doc = fitz.open(self.file_path)
            count = len(doc)
            doc.close()
            return count
        except Exception as e:
            logger.error(f"Could not get page count: {e}")
            return 0
    
    def extract_page_with_method(self, page_num: int, method: str) -> str:
        """Extract a single page using specified method."""
        try:
            if method == "pypdf":
                from pypdf import PdfReader
                reader = PdfReader(self.file_path)
                if page_num < len(reader.pages):
                    return reader.pages[page_num].extract_text() or ""
            
            elif method == "pdfplumber":
                import pdfplumber
                with pdfplumber.open(self.file_path) as pdf:
                    if page_num < len(pdf.pages):
                        return pdf.pages[page_num].extract_text() or ""
            
            elif method == "pymupdf":
                import pymupdf as fitz
                doc = fitz.open(self.file_path)
                if page_num < len(doc):
                    text = doc[page_num].get_text()
                    doc.close()
                    return text or ""
                doc.close()
        
        except Exception as e:
            logger.debug(f"Method {method} failed on page {page_num}: {e}")
        
        return ""
    
    def score_page_text(self, text: str) -> float:
        """
        Quick quality score for a single page.
        Returns 0.0 (worst) to 1.0 (best)
        """
        if not text or len(text) < 10:
            return 0.0
        
        score = 1.0
        
        # Check for encoding errors
        if '�' in text:
            score -= 0.5
        
        # Check alphabetic ratio
        alpha_ratio = sum(1 for c in text if c.isalpha()) / len(text)
        if alpha_ratio < 0.5:
            score -= 0.3
        
        # Check for common words
        text_lower = text.lower()
        common_found = sum(1 for w in ['the', 'and', 'of', 'to', 'a'] if f' {w} ' in text_lower)
        if common_found < 2:
            score -= 0.2
        
        return max(0.0, score)
    
    def choose_best_page_text(self, page_num: int, extractions: Dict[str, str]) -> Tuple[str, str, float]:
        """
        Choose the best extraction for a single page.
        Returns (best_text, method_used, confidence)
        """
        scored = {}
        for method, text in extractions.items():
            if text:
                scored[method] = (text, self.score_page_text(text))
        
        if not scored:
            return "", "none", 0.0
        
        # Find best by score
        best_method = max(scored.keys(), key=lambda k: scored[k][1])
        best_text, best_score = scored[best_method]
        
        # Check agreement between methods
        if len(scored) >= 2:
            methods = list(scored.keys())
            text1 = scored[methods[0]][0]
            text2 = scored[methods[1]][0]
            similarity = SequenceMatcher(None, text1[:500], text2[:500]).ratio()
            confidence = best_score * similarity
        else:
            confidence = best_score
        
        return best_text, best_method, confidence
    
    def extract_with_consensus(self, methods: List[str] = None, 
                              min_confidence: float = 0.7,
                              progress_callback=None) -> Tuple[str, Dict]:
        """
        Extract PDF page-by-page with consensus voting.
        
        Args:
            methods: List of methods to try (default: all available)
            min_confidence: Minimum confidence to accept page
            progress_callback: Function to call with progress updates
        
        Returns:
            (full_text, metadata)
        """
        if methods is None:
            methods = ["pypdf", "pdfplumber", "pymupdf"]
        
        self.page_count = self.get_page_count()
        if self.page_count == 0:
            return "", {"status": "failed", "error": "Could not read PDF"}
        
        logger.info(f"\n{'='*80}")
        logger.info(f"CONSENSUS EXTRACTION: {Path(self.file_path).name}")
        logger.info(f"Pages: {self.page_count} | Methods: {', '.join(methods)}")
        logger.info(f"{'='*80}\n")
        
        full_text = []
        page_metadata = []
        low_confidence_pages = []
        failed_pages = []
        
        # Extract each page with all methods
        for page_num in range(self.page_count):
            if progress_callback:
                progress_callback(page_num, self.page_count)
            
            # Try all methods on this page
            page_extractions = {}
            for method in methods:
                text = self.extract_page_with_method(page_num, method)
                if text:
                    page_extractions[method] = text
            
            # Choose best extraction for this page
            best_text, best_method, confidence = self.choose_best_page_text(page_num, page_extractions)
            
            if confidence < 0.3:
                failed_pages.append(page_num)
                logger.warning(f"  Page {page_num+1}: FAILED (confidence: {confidence:.2f})")
            elif confidence < min_confidence:
                low_confidence_pages.append(page_num)
                logger.info(f"  Page {page_num+1}: LOW (confidence: {confidence:.2f}) via {best_method}")
            else:
                logger.debug(f"  Page {page_num+1}: OK (confidence: {confidence:.2f}) via {best_method}")
            
            full_text.append(best_text)
            page_metadata.append({
                "page": page_num,
                "method": best_method,
                "confidence": confidence,
                "length": len(best_text),
                "methods_tried": list(page_extractions.keys())
            })
            
            # Progress indicator every 10 pages
            if (page_num + 1) % 10 == 0:
                logger.info(f"  Processed {page_num + 1}/{self.page_count} pages...")
        
        # Join all pages
        final_text = "\n\n".join(full_text)
        
        # Calculate overall confidence
        if page_metadata:
            avg_confidence = sum(p["confidence"] for p in page_metadata) / len(page_metadata)
        else:
            avg_confidence = 0.0
        
        # Determine status
        if len(failed_pages) > self.page_count * 0.1:  # More than 10% failed
            status = "failed"
        elif low_confidence_pages or failed_pages:
            status = "partial_success"
        else:
            status = "success"
        
        # Report
        logger.info(f"\n{'='*80}")
        logger.info(f"EXTRACTION COMPLETE")
        logger.info(f"{'='*80}")
        logger.info(f"Status: {status}")
        logger.info(f"Average confidence: {avg_confidence:.2%}")
        logger.info(f"Total length: {len(final_text):,} characters")
        logger.info(f"Pages processed: {len(page_metadata)}/{self.page_count}")
        
        if low_confidence_pages:
            logger.warning(f"Low confidence pages: {len(low_confidence_pages)}")
            logger.warning(f"  Pages: {', '.join(str(p+1) for p in low_confidence_pages[:10])}")
        
        if failed_pages:
            logger.error(f"Failed pages: {len(failed_pages)}")
            logger.error(f"  Pages: {', '.join(str(p+1) for p in failed_pages[:10])}")
        
        metadata = {
            "status": status,
            "confidence": avg_confidence,
            "page_count": self.page_count,
            "methods_used": methods,
            "low_confidence_pages": low_confidence_pages,
            "failed_pages": failed_pages,
            "page_metadata": page_metadata,
            "total_length": len(final_text)
        }
        
        return final_text, metadata
    
    def extract_failed_pages_with_ocr(self, failed_pages: List[int]) -> Dict[int, str]:
        """
        Re-extract failed pages using OCR.
        Last resort for unreadable pages.
        """
        logger.info(f"\n{'='*80}")
        logger.info(f"OCR FALLBACK for {len(failed_pages)} failed pages")
        logger.info(f"{'='*80}\n")
        
        ocr_results = {}
        
        try:
            import easyocr
            import pymupdf as fitz
            from PIL import Image
            import io
            
            reader = easyocr.Reader(['en'], gpu=False)
            doc = fitz.open(self.file_path)
            
            for page_num in failed_pages:
                logger.info(f"  OCR processing page {page_num+1}...")
                try:
                    page = doc[page_num]
                    pix = page.get_pixmap(dpi=300)  # High DPI for better OCR
                    img_bytes = pix.tobytes("png")
                    img = Image.open(io.BytesIO(img_bytes))
                    
                    result = reader.readtext(img)
                    text = "\n".join([detection[1] for detection in result])
                    
                    if text:
                        ocr_results[page_num] = text
                        logger.info(f"    ✓ Extracted {len(text)} chars")
                    else:
                        logger.warning(f"    ⚠️  No text found")
                
                except Exception as e:
                    logger.error(f"    ❌ OCR failed: {e}")
            
            doc.close()
            
        except ImportError:
            logger.error("EasyOCR not available - install with: pip install easyocr")
        except Exception as e:
            logger.error(f"OCR processing failed: {e}")
        
        return ocr_results


def extract_with_consensus(file_path: str, 
                           methods: List[str] = None,
                           min_confidence: float = 0.7,
                           use_ocr_fallback: bool = True) -> Tuple[str, Dict]:
    """
    Convenience function for consensus extraction.
    """
    extractor = ConsensusExtractor(file_path)
    text, metadata = extractor.extract_with_consensus(methods, min_confidence)
    
    # Try OCR on failed pages if requested
    if use_ocr_fallback and metadata["failed_pages"]:
        logger.info("\nAttempting OCR fallback for failed pages...")
        ocr_text = extractor.extract_failed_pages_with_ocr(metadata["failed_pages"])
        
        if ocr_text:
            # Splice in OCR results
            pages = text.split("\n\n")
            for page_num, ocr_page_text in ocr_text.items():
                if page_num < len(pages):
                    pages[page_num] = ocr_page_text
            
            text = "\n\n".join(pages)
            metadata["ocr_pages_recovered"] = list(ocr_text.keys())
            metadata["status"] = "partial_success"  # Upgrade from failed
    
    return text, metadata


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python consensus_extractor.py <pdf_file> [min_confidence]")
        sys.exit(1)
    
    pdf_file = sys.argv[1]
    min_conf = float(sys.argv[2]) if len(sys.argv) > 2 else 0.7
    
    if not Path(pdf_file).exists():
        print(f"❌ File not found: {pdf_file}")
        sys.exit(1)
    
    # Extract with consensus
    text, metadata = extract_with_consensus(pdf_file, min_confidence=min_conf)
    
    # Save output
    output_file = Path(pdf_file).stem + "_consensus.txt"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(text)
    
    print(f"\n✓ Saved to: {output_file}")
    print(f"Status: {metadata['status']}")
    print(f"Confidence: {metadata['confidence']:.1%}")
