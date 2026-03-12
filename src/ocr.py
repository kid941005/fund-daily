"""
OCR Module for Fund Daily
Improved fund screenshot recognition with robust parsing
Supports both EasyOCR and rule-based parsing
"""

import re
import logging
from typing import List, Dict, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Try to import EasyOCR
try:
    import easyocr
    EASYOCR_AVAILABLE = True
except ImportError:
    EASYOCR_AVAILABLE = False
    logger.warning("EasyOCR not available, using rule-based parsing only")


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
        
        # Only use simple number pattern as last resort, but exclude fund codes
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
                except (ValueError, AttributeError):
                    continue
        
        return best_amount
    
    def _extract_all_amounts(self, text: str) -> List[float]:
        """Extract all potential amounts from text"""
        amounts = []
        # Match numbers with comma: 1,234.56 or 1,234
        # Also match standalone integers >= 50
        patterns = [
            r'([1-9]\d{0,2}(?:,\d{3})+(?:\.\d{1,2})?)',  # 1,234.56
            r'([1-9]\d{2,6}(?:\.\d{1,2})?)',  # 1234.56 (no comma)
            r'\b([1-9]\d{2,4})\b',  # 1234 (integer 100-99999)
        ]
        for pattern in patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                try:
                    amount = float(match.replace(',', ''))
                    if amount >= 50:  # Minimum 50 yuan
                        amounts.append(amount)
                except (ValueError, AttributeError):
                    continue
        return amounts
    
    def parse(self, ocr_text: str) -> List[OcrResult]:
        """Parse OCR text and extract fund data"""
        self.results = []
        
        if not ocr_text or len(ocr_text.strip()) < 10:
            return []
        
        lines = [l.strip() for l in ocr_text.split('\n') if l.strip()]
        
        # Improved parsing: Group by vertical position (rows)
        # The screenshot has: code line above, name+amount line below
        code_pattern = self.CODE_PATTERN
        
        # For each line, find codes
        codes_by_line = {}
        amounts_by_line = {}
        
        for i, line in enumerate(lines):
            codes = code_pattern.findall(line)
            if codes:
                codes_by_line[i] = codes
            
            # Find amounts using improved method
            amounts = self._extract_all_amounts(line)
            if amounts:
                amounts_by_line[i] = max(amounts)
        
        # Match codes with amounts from nearby lines (within 5 lines)
        for code_line_idx, codes in codes_by_line.items():
            # Look for amounts in the next few lines
            for look_ahead in range(1, 6):
                amount_line_idx = code_line_idx + look_ahead
                if amount_line_idx in amounts_by_line:
                    for code in codes:
                        self.results.append(OcrResult(
                            code=code,
                            amount=amounts_by_line[amount_line_idx],
                            confidence=0.9,
                            method="row_match"
                        ))
                    break
        
        # Backup: Same line parsing
        for line in lines:
            codes = code_pattern.findall(line)
            amount = self._extract_amount(line)
            
            if codes and amount:
                for code in codes:
                    if not any(r.code == code for r in self.results):
                        self.results.append(OcrResult(
                            code=code,
                            amount=amount,
                            confidence=0.8,
                            method="same_line"
                        ))
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


# EasyOCR reader instance (lazy initialization)
_easyocr_reader = None


def _get_easyocr_reader():
    """Get or create EasyOCR reader"""
    global _easyocr_reader
    if _easyocr_reader is None and EASYOCR_AVAILABLE:
        try:
            _easyocr_reader = easyocr.Reader(['ch_sim', 'en'], gpu=False)
            logger.info("EasyOCR reader initialized successfully")
        except Exception as e:
            logger.warning(f"Failed to initialize EasyOCR: {e}")
            return None
    return _easyocr_reader


def parse_image_easyocr(image_path: str) -> Dict:
    """
    Parse fund screenshot using EasyOCR
    
    Args:
        image_path: Path to the image file
        
    Returns:
        dict: Parsed fund data
    """
    from PIL import Image, ImageEnhance
    import numpy as np
    
    if not EASYOCR_AVAILABLE:
        return {
            'success': False,
            'error': 'EasyOCR not available',
            'funds': [],
            'message': '请安装 easyocr: pip install easyocr'
        }
    
    reader = _get_easyocr_reader()
    if reader is None:
        return {
            'success': False,
            'error': 'Failed to initialize EasyOCR',
            'funds': [],
            'message': 'EasyOCR 初始化失败'
        }
    
    try:
        # Load image using PIL
        img = Image.open(image_path)
        
        # Image preprocessing for better OCR
        # Convert to grayscale
        if img.mode != 'L':
            img = img.convert('L')
        
        # Enhance contrast
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.5)  # Increase contrast by 50%
        
        # Convert to numpy array
        img_array = np.array(img)
        
        # Run OCR on preprocessed image
        results = reader.readtext(img_array)
        
        # Combine all text
        ocr_text = ""
        for bbox, text, conf in results:
            if conf > 0.3:  # Filter low confidence
                ocr_text += text + "\n"
        
        logger.info(f"EasyOCR extracted {len(results)} text regions")
        
        # Parse using rule-based parser
        return parse_ocr_result(ocr_text)
        
    except Exception as e:
        logger.error(f"EasyOCR error: {e}")
        return {
            'success': False,
            'error': str(e),
            'funds': [],
            'message': f'EasyOCR 处理失败: {str(e)}'
        }


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
