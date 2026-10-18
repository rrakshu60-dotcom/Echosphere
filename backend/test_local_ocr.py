"""
Unit & Integration Tests for 100% Free, Local On-Device Circular OCR & Auto-Digitizer
Verifies zero external API token requirement, zero rate limits, zero costs:
1. Native PDF text stream extraction (<50ms) via pypdf
2. Image Neural OCR (<1s on CPU) via RapidOCR ONNX Runtime
3. Smart institutional circular structurer (Ref No, Category, Priority, Audience, Dates, Venues)
4. FastAPI endpoint /api/v1/announcements/ocr-document contract
"""

import os
import io
import sys
import base64
import unittest
from PIL import Image, ImageDraw, ImageFont
import reportlab.pdfgen.canvas as canvas
from fastapi.testclient import TestClient

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Force GEMINI_API_KEY to empty string to strictly test 100% free offline execution
os.environ["GEMINI_API_KEY"] = ""

from app.main import app
from app.services.smart_intake_service import SmartIntakeService


class TestLocalCircularOcr(unittest.TestCase):
    """Test suite for 100% Free Local Circular OCR & Auto-Digitizer."""

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def _create_sample_pdf_bytes(self) -> bytes:
        """Generates an in-memory official college circular PDF."""
        buf = io.BytesIO()
        c = canvas.Canvas(buf)
        c.drawString(50, 780, "R.V. COLLEGE OF ENGINEERING - BENGALURU")
        c.drawString(50, 760, "Ref: RVCE/CSE/2026/042")
        c.drawString(50, 740, "Date: 15 October 2026")
        c.drawString(50, 710, "Subject: Midterm Examination Schedule for CSE 3rd Year")
        c.drawString(50, 680, "All 3rd year CSE students are hereby informed that the CIE-2 examinations")
        c.drawString(50, 660, "will commence from 25 October 2026 at 10:00 AM in the Turing Lab.")
        c.drawString(50, 640, "Carrying hall ticket and college ID card is strictly mandatory.")
        c.save()
        buf.seek(0)
        return buf.getvalue()

    def _create_sample_image_bytes(self) -> bytes:
        """Generates an in-memory circular notice image."""
        img = Image.new("RGB", (900, 450), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)

        # Draw notice lines
        lines = [
            "RV COLLEGE OF ENGINEERING - PLACEMENT CELL",
            "Ref: RVCE/PLACEMENT/2026/019",
            "Date: 18 October 2026",
            "Subject: Campus Placement Drive by TechCorp",
            "Eligible candidates: 4th year CSE students",
            "Reporting Venue: Main Auditorium at 9:00 AM",
            "Attendance is mandatory for all registered candidates.",
        ]
        y = 30
        for line in lines:
            draw.text((40, y), line, fill=(0, 0, 0))
            y += 45

        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=95)
        buf.seek(0)
        return buf.getvalue()

    def test_01_pdf_local_extraction_and_structuring(self):
        """Verify native PDF text stream extraction and institutional structuring without any API key."""
        pdf_bytes = self._create_sample_pdf_bytes()
        pdf_b64 = base64.b64encode(pdf_bytes).decode("utf-8")

        result = SmartIntakeService.ocr_document_to_notice(
            file_base64=pdf_b64,
            mime_type="application/pdf",
            filename="cie2_schedule.pdf",
        )

        self.assertIsNotNone(result)
        self.assertIn("title", result)
        self.assertIn("content", result)
        self.assertIn("raw_text", result)

        # Verify extracted reference number
        self.assertIn("RVCE/CSE/2026/042", result.get("reference_number", ""))

        # Verify intelligent category & priority detection
        self.assertEqual(result.get("suggested_category"), "Examination")
        self.assertEqual(result.get("suggested_priority"), "HIGH")

        # Verify audience detection
        self.assertIn(result.get("suggested_audience"), ["CSE Department", "3rd Year Students"])

        # Verify content formatting
        content = result.get("content", "")
        self.assertIn("Turing Lab", content)
        self.assertIn("25 October 2026", content)

    def test_02_image_rapidocr_extraction_and_structuring(self):
        """Verify local neural OCR (RapidOCR) on synthetic circular image without any cloud tokens."""
        img_bytes = self._create_sample_image_bytes()
        img_b64 = base64.b64encode(img_bytes).decode("utf-8")

        result = SmartIntakeService.ocr_document_to_notice(
            file_base64=img_b64,
            mime_type="image/jpeg",
            filename="placement_circular.jpg",
        )

        self.assertIsNotNone(result)
        self.assertIn("title", result)
        self.assertIn("content", result)

        # Category should be Placement
        self.assertEqual(result.get("suggested_category"), "Placement")

        # Audience should detect CSE or 4th Year
        self.assertIn(result.get("suggested_audience"), ["CSE Department", "4th Year Students", "Entire College"])

        # Raw text should contain text extracted by RapidOCR
        raw_text = result.get("raw_text") or ""
        self.assertTrue(len(raw_text) > 20, "RapidOCR should extract text from image")
        self.assertTrue(
            "techcorp" in raw_text.lower() or "placement" in raw_text.lower() or "rvce" in raw_text.lower(),
            f"Expected placement/techcorp keywords in OCR text, got: {raw_text}"
        )

    def test_03_direct_raw_text_intake(self):
        """Verify fast structured circular generation when raw text is supplied directly."""
        raw_text = (
            "CIRCULAR\n"
            "Ref No: RVCE/ADMIN/2026/099\n"
            "Date: 20 October 2026\n"
            "Subject: Annual Sports Day Trials for Badminton and Football\n"
            "Venue: Sports Complex at 4:00 PM\n"
            "Open to all students from 1st year to 4th year.\n"
        )

        result = SmartIntakeService.ocr_document_to_notice(
            file_base64="",
            mime_type="text/plain",
            filename="sports_day.txt",
            raw_text=raw_text,
        )

        self.assertEqual(result.get("suggested_category"), "Sports")
        self.assertIn("RVCE/ADMIN/2026/099", result.get("reference_number", ""))
        self.assertIn("Sports Complex", result.get("content", ""))

    def test_04_fastapi_ocr_document_endpoint(self):
        """Verify FastAPI REST endpoint /api/v1/announcements/ocr-document serialization."""
        pdf_bytes = self._create_sample_pdf_bytes()
        pdf_b64 = base64.b64encode(pdf_bytes).decode("utf-8")

        response = self.client.post(
            "/api/v1/announcements/ocr-document",
            json={
                "file_base64": pdf_b64,
                "mime_type": "application/pdf",
                "filename": "cie2_schedule.pdf",
            },
        )

        self.assertEqual(response.status_code, 200, f"Endpoint error: {response.text}")
        data = response.json()
        self.assertIn("title", data)
        self.assertIn("content", data)
        self.assertIn("suggested_category", data)
        self.assertIn("suggested_priority", data)
        self.assertIn("reference_number", data)
        self.assertEqual(data["suggested_category"], "Examination")
        self.assertIn("RVCE/CSE/2026/042", data["reference_number"])


if __name__ == "__main__":
    unittest.main()
