import os
import re

from google.adk.tools import ToolContext
from google.genai import Client, types


def extract_momo_from_image(image_path: str, tool_context: ToolContext) -> dict:
    """Extracts raw Mobile Money (MoMo) transaction details from an uploaded screenshot image.
    Uses Gemini's multimodal vision features to perform text extraction and structure reconstruction.

    Args:
        image_path: Absolute local path to the transaction screenshot (PNG/JPEG).

    Returns:
        A dictionary containing parsed transaction listings and status flags.
    """
    if not image_path or not image_path.strip():
        return {"status": "error", "message": "Image path is empty."}

    if not os.path.exists(image_path):
        return {"status": "error", "message": f"Image file not found at: {image_path}"}

    # Ensure it has a valid image extension to mitigate arbitrary file execution
    if not re.search(r"\.(png|jpe?g)$", image_path, re.IGNORECASE):
        return {
            "status": "error",
            "message": "Unsupported file format. Only PNG, JPG, and JPEG are supported.",
        }

    try:
        # Initialize GenAI Client (respecting existing Vertex/Cloud environment settings)
        client = Client()

        with open(image_path, "rb") as f:
            image_bytes = f.read()

        prompt = """
        You are a Mobile Money (MoMo) OCR and statement extraction agent.
        Analyze this screenshot image containing MTN Mobile Money or other teleco transaction details.
        Extract every transaction and list them one by one in text format.
        For each transaction, reconstruct the standard SMS text alert format.

        CRITICAL PRIVACY INSTRUCTION:
        For security and privacy, you must redact personal customer names and personal phone numbers from the counterparty fields.
        - Replace any personal phone number with "[REDACTED_PHONE]".
        - Replace any personal name with "[REDACTED_NAME]".
        - Leave registered commercial/utility entities (like "ECG Prepaid", "TELECEL", "MTN", "GRA", "Bolt") unredacted.

        Example SMS formats:
        - "Received GHS 150.00 from [REDACTED_NAME] on 2026-06-29 14:20:00. Transaction ID: 987654321."
        - "You have paid GHS 50.00 to ECG Prepaid. Transaction ID: 11223344."
        - "Cash Out GHS 200.00 to agent [REDACTED_NAME]. Transaction ID: 88990011."

        Output only the SMS alerts, separated by newlines. Do not output markdown code blocks, intro text, or conversational text.
        """

        # Call multimodal generation
        response = client.models.generate_content(
            model="gemini-3.5-flash",
            contents=[
                types.Part.from_bytes(data=image_bytes, mime_type="image/png"),
                prompt,
            ],
        )

        extracted_text = response.text
        if not extracted_text or not extracted_text.strip():
            return {
                "status": "error",
                "message": "No transaction text could be extracted from the screenshot.",
            }

        # Delegate the actual parsing, state storage, and anonymization to the existing parse_momo_statement tool
        from app.parser import parse_momo_statement

        return parse_momo_statement(
            statement_text=extracted_text, tool_context=tool_context
        )

    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to process screenshot image: {e!s}",
        }
