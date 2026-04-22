"""OCR utilities to extract structured data from receipts."""

import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from io import BytesIO
from typing import Optional

from PIL import Image

# Intentar importar PaddleOCR (OCR local)
try:
    from paddleocr import PaddleOCR

    PADDLEOCR_AVAILABLE = True
except ImportError:
    PADDLEOCR_AVAILABLE = False

# Intentar importar OpenAI para OCR con Vision
try:
    from openai import OpenAI
    import base64

    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


@dataclass
class ReceiptData:
    """Structured data extracted from a receipt."""

    total: Optional[Decimal] = None
    date: Optional[date] = None
    merchant: Optional[str] = None
    description: Optional[str] = None
    raw_text: Optional[str] = None
    confidence: float = 0.0

    def __str__(self) -> str:
        return (
            f"ReceiptData(total={self.total}, date={self.date}, "
            f"merchant={self.merchant}, description={self.description})"
        )


class ReceiptExtractor:
    """Extracts structured receipt information using OCR."""

    def __init__(self, openai_api_key: Optional[str] = None):
        self.openai_api_key = openai_api_key
        self.openai_client = None
        self.paddleocr = None
        self.paddleocr_error = None
        self.paddleocr_initialized = False

        if openai_api_key and OPENAI_AVAILABLE:
            self.openai_client = OpenAI(api_key=openai_api_key)

    def extract_with_paddleocr(self, image_bytes: bytes) -> ReceiptData:
        """Extracts receipt data using local PaddleOCR."""
        if not PADDLEOCR_AVAILABLE:
            return ReceiptData(
                description="PaddleOCR is not installed",
                confidence=0.0,
            )

        self._initialize_paddleocr()
        if self.paddleocr is None:
            error = f": {self.paddleocr_error}" if self.paddleocr_error else ""
            return ReceiptData(
                description=f"PaddleOCR failed to initialize{error}",
                confidence=0.0,
            )

        try:
            import numpy as np

            img = Image.open(BytesIO(image_bytes))
            image_np = np.array(img.convert("RGB"))
            result = self.paddleocr.predict(image_np)
            text = self._text_from_paddle_result(result)
            return self._parse_receipt_text(text)
        except Exception as e:
            return ReceiptData(
                description=f"OCR error: {str(e)}",
                confidence=0.0,
            )

    def extract_with_openai(self, image_bytes: bytes) -> ReceiptData:
        """Extracts receipt data using OpenAI Vision."""
        if not self.openai_client:
            return ReceiptData(
                description="OpenAI is not configured",
                confidence=0.0,
            )

        try:
            # Convertir imagen a base64
            img_base64 = base64.b64encode(image_bytes).decode("utf-8")

            # Detectar tipo de imagen
            img = Image.open(BytesIO(image_bytes))
            image_format = img.format.lower() if img.format else "jpeg"
            media_type = f"image/{image_format}"

            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": """Analyze this receipt and extract the following fields as JSON:
{
    "total": <decimal amount paid>,
    "date": "<date in YYYY-MM-DD format if visible>",
    "merchant": "<merchant/store name>",
    "description": "<brief purchase description, max 50 chars>"
}

If any field cannot be identified, use null.
Return only JSON without extra explanation.""",
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{media_type};base64,{img_base64}"
                                },
                            },
                        ],
                    }
                ],
                max_tokens=300,
            )

            # Parsear respuesta JSON
            answer = response.choices[0].message.content.strip()
            if answer.startswith("```"):
                answer = re.sub(r"^```(?:json)?\n?", "", answer)
                answer = re.sub(r"\n?```$", "", answer)

            import json

            data = json.loads(answer)

            total = None
            if data.get("total") is not None:
                total = Decimal(str(data["total"]))

            parsed_date = None
            if data.get("date"):
                try:
                    parsed_date = date.fromisoformat(data["date"])
                except ValueError:
                    pass

            return ReceiptData(
                total=total,
                date=parsed_date,
                merchant=data.get("merchant"),
                description=data.get("description"),
                confidence=0.9,
            )

        except Exception as e:
            return ReceiptData(
                description=f"OpenAI error: {str(e)}",
                confidence=0.0,
            )

    def extract(self, image_bytes: bytes) -> ReceiptData:
        """Extracts receipt data using the best available method."""
        if PADDLEOCR_AVAILABLE:
            receipt = self.extract_with_paddleocr(image_bytes)
            if receipt.confidence < 0.5 and self.openai_client:
                openai_receipt = self.extract_with_openai(image_bytes)
                if openai_receipt.confidence > receipt.confidence:
                    return openai_receipt
            return receipt

        if self.openai_client:
            return self.extract_with_openai(image_bytes)

        return ReceiptData(
            description="No OCR engine available. Configure OPENAI_API_KEY or install PaddleOCR.",
            confidence=0.0,
        )

    def _text_from_paddle_result(self, result: list) -> str:
        """Converts PaddleOCR output to plain parseable text."""
        lines: list[str] = []
        for block in result or []:
            texts = block.get("rec_texts", []) if isinstance(block, dict) else []
            lines.extend(text for text in texts if text)
        return "\n".join(lines)

    def _initialize_paddleocr(self) -> None:
        """Initializes PaddleOCR once to avoid repeated startup cost."""
        if self.paddleocr_initialized:
            return

        self.paddleocr_initialized = True
        try:
            self.paddleocr = PaddleOCR(
                use_doc_orientation_classify=False,
                use_doc_unwarping=False,
                use_textline_orientation=False,
            )
        except Exception as error:
            self.paddleocr_error = str(error)

    def _parse_receipt_text(self, text: str) -> ReceiptData:
        """Parses OCR text and extracts structured receipt fields."""
        data = ReceiptData(raw_text=text, confidence=0.5)

        total_patterns = [
            r"TOTAL[:\s]*(\d+[.,]\d{2})",
            r"AMOUNT[:\s]*(\d+[.,]\d{2})",
            r"A PAGAR[:\s]*(\d+[.,]\d{2})",
            r"SUMA[:\s]*(\d+[.,]\d{2})",
            r"€\s*(\d+[.,]\d{2})",
            r"(\d+[.,]\d{2})\s*€",
        ]

        for pattern in total_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                total_str = match.group(1).replace(",", ".")
                try:
                    data.total = Decimal(total_str)
                    data.confidence = 0.7
                    break
                except Exception:
                    pass

        date_patterns = [
            r"(\d{2})[/-](\d{2})[/-](\d{4})",
            r"(\d{2})[/-](\d{2})[/-](\d{2})",
        ]

        for pattern in date_patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    day, month, year = match.groups()
                    if len(year) == 2:
                        year = "20" + year
                    data.date = date(int(year), int(month), int(day))
                    break
                except Exception:
                    pass

        lines = [line.strip() for line in text.split("\n") if line.strip()]
        if lines:
            data.merchant = lines[0][:50]

        return data
