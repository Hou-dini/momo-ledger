import pytest
import os
from unittest.mock import MagicMock, patch
from google.adk.tools import ToolContext

from app.parser import parse_momo_statement
from app.vision_parser import extract_momo_from_image
from app.profiler import assess_credit_readiness

class TestMoMoLedgerSecurity:
    """Security boundary and validation test suite for MoMo Ledger."""

    def test_parser_tool_rejects_empty_input(self):
        """Boundary: Input validation — empty strings must be rejected cleanly."""
        mock_context = MagicMock(spec=ToolContext)
        mock_context.state = {}
        
        result = parse_momo_statement("", mock_context)
        assert result["status"] == "error"
        assert "empty" in result["message"].lower()

    def test_parser_tool_anonymizes_phone_numbers(self):
        """Boundary: PII Leakage — counterparty phone numbers must be redacted."""
        mock_context = MagicMock(spec=ToolContext)
        mock_context.state = {}
        
        statement = "Received GHS 100.00 from 0541234567 on 2026-06-28 10:00:00. Transaction ID: 12345."
        result = parse_momo_statement(statement, mock_context)
        
        assert result["status"] == "success"
        assert result["count"] == 1
        assert result["transactions"][0]["counterparty"] == "[ANONYMIZED_PHONE]"

    def test_parser_tool_anonymizes_international_phone_numbers(self):
        """Boundary: PII Leakage — country code prefix phone numbers must be redacted."""
        mock_context = MagicMock(spec=ToolContext)
        mock_context.state = {}
        
        statement = "Received GHS 100.00 from 233541234567 on 2026-06-28 10:00:00. Transaction ID: 12345."
        result = parse_momo_statement(statement, mock_context)
        
        assert result["status"] == "success"
        assert result["transactions"][0]["counterparty"] == "[ANONYMIZED_PHONE]"

    def test_parser_tool_coerces_absolute_amount(self):
        """Boundary: Input validation — negative amount text is corrected to positive values."""
        mock_context = MagicMock(spec=ToolContext)
        mock_context.state = {}
        
        # Test formatting where amount might accidentally have a negative sign
        statement = "You have paid GHS -150.00 to Restock-Co. Transaction ID: 1002."
        result = parse_momo_statement(statement, mock_context)
        
        assert result["status"] == "success"
        # Since parse_momo_statement has abs(float(amount_str)) it coerces to positive
        assert result["transactions"][0]["amount"] == 150.00

    def test_vision_parser_rejects_empty_path(self):
        """Boundary: Vision Input — empty path is rejected."""
        mock_context = MagicMock(spec=ToolContext)
        mock_context.state = {}
        
        result = extract_momo_from_image("", mock_context)
        assert result["status"] == "error"
        assert "empty" in result["message"].lower()

    def test_vision_parser_rejects_missing_file(self):
        """Boundary: Vision Input — missing files are rejected."""
        mock_context = MagicMock(spec=ToolContext)
        mock_context.state = {}
        
        result = extract_momo_from_image("missing_screenshot.png", mock_context)
        assert result["status"] == "error"
        assert "not found" in result["message"].lower()

    def test_vision_parser_rejects_unsupported_format(self):
        """Boundary: Vision Input — unsupported mime/extensions are rejected."""
        mock_context = MagicMock(spec=ToolContext)
        mock_context.state = {}
        
        # Create a dummy text file to ensure it exists
        temp_file = "temp_exploit.exe"
        with open(temp_file, "w") as f:
            f.write("malicious payload")
            
        try:
            result = extract_momo_from_image(temp_file, mock_context)
            assert result["status"] == "error"
            assert "unsupported" in result["message"].lower()
        finally:
            if os.path.exists(temp_file):
                os.remove(temp_file)
