"""
OCR Module for Fund Daily
Improved fund screenshot recognition with robust parsing
"""

import re
import logging
from typing import List, Dict, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class OcrResult:
    """OCR parsing result"""
    code: str
    amount: float
    name: str = ""
    confidence: float = 0.0
    method: str = ""


class FundOcrParser:
    """OCR parser for fund screenshots"""
    
    CODE_PATTERN = re.compile(r'\b([012356]\d{5})\b')
    
    def __init__(self):
        self.results: List[OcrResult] = []
    
    def _extract_amount(self, text: str) -> Optional[float]:
        """Extract amount from text - must NOT be a 6-digit fund code"""
        # First, identify any fund codes in the text so we can exclude them
        fund_codes_in_text = set(self.CODE_PATTERN.findall(text))
        
        patterns = [
            # With currency symbol (high confidence)
            (r'[￥¥]\s*([1-9]\d{0,2}(?:,\d{3})*(?:\.\d{1,2})?)', 1.0),
            # With unit
            (r'([1-9]\d{0,2}(?:,\d{3})*(?:\.\d{1,2})?)\s*(?:元|块)', 0.95),
            # Large amounts with comma (like 10,000 or 1,234,567)
            (r'([1-9]\d{1,3}(?:,\d{3})+(?:\.\d{1,2})?)', 0.9),
        ]
        
        # Only use simple number pattern as last resort, and exclude fund codes
        simple_pattern = r'\b([1-9]\d{2,7})\b'
        
        best_amount = None
        
        # First try specific patterns
        for pattern, base_conf in patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                try:
                    # Clean and convert
                    amount = float(match.replace(',', '').replace('￥', '').replace('¥', '').strip())
                    
                    # Must be in valid range
                    if 100 <= amount <= 10000000:
                        # Skip if it looks like a fund code
                        str_amount = str(int(amount))
                        if len(str_amount) == 6 and str_amount in fund_codes_in_text:
                            continue
                        
                        best_amount = amount
                        break
                except (ValueError, AttributeError):
                    continue
            if best_amount:
                break
        
        # If no specific pattern matched, try simple pattern but exclude fund codes
        if not best_amount:
            matches = re.findall(simple_pattern, text)
            for match in matches:
                try:
                    amount = float(match)
                    if 100 <= amount <= 10000000:
                        # Exclude if it matches a fund code in the text
                        if match in fund_codes_in_text:
                            continue
                        best_amount = amount
                        break
                except:
                    continue
        
        return best_amount
    
    def parse(self, ocr_text: str) -> List[OcrResult]:
        """Parse OCR text and extract fund data"""
        self.results = []
        
        if not ocr_text or len(ocr_text.strip()) < 10:
            return []
        
        lines = [l.strip() for l in ocr_text.split('\n') if l.strip()]
        
        # Method 1: Same line - code and amount on same line
        for line in lines:
            codes = self.CODE_PATTERN.findall(line)
            amount = self._extract_amount(line)
            
            if codes and amount:
                for code in codes:
                    self.results.append(OcrResult(
                        code=code,
                        amount=amount,
                        confidence=0.9,
                        method="same_line"
                    ))
        
        # Method 2: Consecutive lines - code on one line, amount on next
        for i in range(len(lines) - 1):
            line1, line2 = lines[i], lines[i + 1]
            
            codes1 = self.CODE_PATTERN.findall(line1)
            codes2 = self.CODE_PATTERN.findall(line2)
            amount1 = self._extract_amount(line1)
            amount2 = self._extract_amount(line2)
            
            # Code on line1, amount on line2
            if codes1 and amount2:
                for code in codes1:
                    self.results.append(OcrResult(
                        code=code,
                        amount=amount2,
                        confidence=0.85,
                        method="consecutive"
                    ))
            
            # Code on line2, amount on line1
            if codes2 and amount1:
                for code in codes2:
                    self.results.append(OcrResult(
                        code=code,
                        amount=amount1,
                        confidence=0.85,
                        method="consecutive"
                    ))
        
        # Method 3: Context search - find amount near code within N lines
        for i, line in enumerate(lines):
            codes = self.CODE_PATTERN.findall(line)
            if not codes:
                continue
            
            # Search nearby (within 2 lines) for amounts
            amount = None
            for j in range(max(0, i-2), min(len(lines), i+3)):
                if j == i:
                    continue
                amt = self._extract_amount(lines[j])
                if amt:
                    amount = amt
                    break
            
            if amount and not any(r.code in codes for r in self.results):
                for code in codes:
                    self.results.append(OcrResult(
                        code=code,
                        amount=amount,
                        confidence=0.7,
                        method="context"
                    ))
        
        return self._deduplicate()
    
    def _deduplicate(self) -> List[OcrResult]:
        """Remove duplicates"""
        seen = {}
        for r in self.results:
            if r.code not in seen or r.confidence > seen[r.code].confidence:
                seen[r.code] = r
        return list(seen.values())


def validate_fund_code(code: str) -> bool:
    """Validate fund code"""
    if not re.match(r'^\d{6}$', code):
        return False
    return int(code[0]) in [0, 1, 2, 3, 5, 6]


def parse_ocr_result(ocr_text: str) -> Dict:
    """Main entry point"""
    parser = FundOcrParser()
    results = parser.parse(ocr_text)
    
    funds = []
    for r in results:
        if validate_fund_code(r.code):
            funds.append({
                'code': r.code,
                'amount': r.amount,
                'name': r.name,
                'confidence': r.confidence,
                'source': r.method
            })
    
    return {
        'success': True,
        'funds': funds,
        'count': len(funds),
        'message': f'识别到 {len(funds)} 个基金'
    }
