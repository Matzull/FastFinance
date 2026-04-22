"""Tests for Telegram OCR module."""

from datetime import date
from decimal import Decimal

from patrimonio.telegram.ocr import ReceiptData, ReceiptExtractor


class TestReceiptData:
    """Tests for the ReceiptData dataclass."""

    def test_empty_receipt_data(self):
        data = ReceiptData()
        assert data.total is None
        assert data.date is None
        assert data.merchant is None
        assert data.description is None
        assert data.raw_text is None
        assert data.confidence == 0.0

    def test_full_receipt_data(self):
        data = ReceiptData(
            total=Decimal("25.50"),
            date=date(2024, 1, 15),
            merchant="Supermercado ABC",
            description="Compra semanal",
            raw_text="original text",
            confidence=0.9,
        )
        assert data.total == Decimal("25.50")
        assert data.date == date(2024, 1, 15)
        assert data.merchant == "Supermercado ABC"
        assert data.description == "Compra semanal"
        assert data.confidence == 0.9


class TestReceiptExtractor:
    """Tests for receipt extractor."""

    def test_extractor_without_openai(self):
        extractor = ReceiptExtractor(openai_api_key=None)
        assert extractor.openai_client is None

    def test_parse_text_with_total_pattern_1(self):
        extractor = ReceiptExtractor()
        text = """
        SUPERMERCADO ABC
        Fecha: 15/01/2024
        
        Leche 1L         2.50
        Pan              1.20
        
        TOTAL: 3.70
        """
        data = extractor._parse_receipt_text(text)
        assert data.total == Decimal("3.70")
        assert data.confidence >= 0.5

    def test_parse_text_with_total_pattern_2(self):
        extractor = ReceiptExtractor()
        text = """
        TIENDA XYZ
        
        Artículo A    10.00€
        
        A PAGAR: 10.00
        """
        data = extractor._parse_receipt_text(text)
        assert data.total == Decimal("10.00")

    def test_parse_text_with_dd_mm_yyyy_date(self):
        extractor = ReceiptExtractor()
        text = """
        COMERCIO
        15/03/2024
        TOTAL: 5.00
        """
        data = extractor._parse_receipt_text(text)
        assert data.date == date(2024, 3, 15)

    def test_parse_text_with_dd_mm_yy_date(self):
        extractor = ReceiptExtractor()
        text = """
        COMERCIO
        15-03-24
        TOTAL: 5.00
        """
        data = extractor._parse_receipt_text(text)
        assert data.date == date(2024, 3, 15)

    def test_parse_text_merchant(self):
        extractor = ReceiptExtractor()
        text = """RESTAURANTE LA MARINA
        Mesa 5
        TOTAL: 45.00
        """
        data = extractor._parse_receipt_text(text)
        assert "RESTAURANTE LA MARINA" in data.merchant

    def test_parse_text_without_total(self):
        extractor = ReceiptExtractor()
        text = "Text without amount"
        data = extractor._parse_receipt_text(text)
        assert data.total is None
        assert data.confidence == 0.5

    def test_parse_text_total_with_decimal_comma(self):
        extractor = ReceiptExtractor()
        text = "TOTAL: 15,99€"
        data = extractor._parse_receipt_text(text)
        assert data.total == Decimal("15.99")

    def test_extract_without_engines(self):
        extractor = ReceiptExtractor(openai_api_key=None)
        import patrimonio.telegram.ocr as ocr_module

        original = ocr_module.PADDLEOCR_AVAILABLE
        ocr_module.PADDLEOCR_AVAILABLE = False

        try:
            data = extractor.extract(b"fake image data")
            assert data.confidence == 0.0
            assert "No OCR engine available" in data.description
        finally:
            ocr_module.PADDLEOCR_AVAILABLE = original


class TestReceiptExtractorPaddleOCR:
    """Tests for PaddleOCR extraction (requires PaddleOCR installation)."""

    def test_extract_with_paddleocr_without_installation(self):
        import patrimonio.telegram.ocr as ocr_module

        original = ocr_module.PADDLEOCR_AVAILABLE
        ocr_module.PADDLEOCR_AVAILABLE = False

        try:
            extractor = ReceiptExtractor()
            data = extractor.extract_with_paddleocr(b"fake image")
            assert data.confidence == 0.0
            assert "PaddleOCR is not installed" in data.description
        finally:
            ocr_module.PADDLEOCR_AVAILABLE = original


class TestReceiptExtractorOpenAI:
    """Tests for OpenAI extraction."""

    def test_extract_with_openai_not_configured(self):
        extractor = ReceiptExtractor(openai_api_key=None)
        data = extractor.extract_with_openai(b"fake image")
        assert data.confidence == 0.0
        assert "OpenAI is not configured" in data.description
