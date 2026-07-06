import re

from google.adk.tools.tool_context import ToolContext


def parse_momo_statement(statement_text: str, tool_context: ToolContext) -> dict:
    """Parses raw copy-pasted Mobile Money SMS transaction alerts or raw statement text.
    Extracts transaction date, type (deposit, withdrawal, transfer, payment), amount, counterparty, and transaction ID.

    Args:
        statement_text: The raw text of the Mobile Money statements or SMS transaction logs.

    Returns:
        A dictionary containing a list of parsed transactions and status metadata.
    """
    if not statement_text or not statement_text.strip():
        return {"status": "error", "message": "Input statement text is empty."}

    # Normalize whitespace
    normalized_text = re.sub(r"\s+", " ", statement_text)

    # Standard patterns for MTN MoMo and Telecel Cash in Ghana
    # Example: "Received GHS 150.00 from Kwame Mensah on 2026-06-29 14:20:00. Transaction ID: 987654321."
    # Example: "You have paid GHS 50.00 to ECG Prepaid. Transaction ID: 11223344. Current balance..."
    # Example: "Cash Out GHS 200.00 to agent Mom's Shop. Transaction ID: 88990011."

    transactions = []

    # Extract alerts by matching each transaction block ending with a transaction ID
    alerts = re.findall(
        r"(.*?(?:Transaction ID:|txn:|ID:)\s*\d+)", normalized_text, flags=re.IGNORECASE
    )

    for alert in alerts:
        alert = alert.strip()

        txn = {}

        # 1. Extract Transaction ID
        txn_id_match = re.search(
            r"(?:Transaction ID:|txn:|ID:)\s*(\d+)", alert, re.IGNORECASE
        )
        if txn_id_match:
            txn["transaction_id"] = txn_id_match.group(1)
        else:
            continue  # Skip if no transaction ID (protect against malformed entries)

        # 2. Extract Amount
        amount_match = re.search(
            r"(?:GHS|GHC|Ghs)\s*(-?[\d,]+\.\d{2})", alert, re.IGNORECASE
        )
        if amount_match:
            # Strip commas and cast to absolute float
            amount_str = amount_match.group(1).replace(",", "")
            txn["amount"] = abs(float(amount_str))
        else:
            txn["amount"] = 0.0

        # 3. Determine Type and Counterparty
        # Check for Received/Cash In
        if re.search(
            r"(?:Received|Cash In|deposited|From|transfer from)", alert, re.IGNORECASE
        ):
            txn["type"] = "deposit"
            # Try to extract sender
            sender_match = re.search(
                r"(?:from|From)\s+([A-Za-z0-9\s\-]+?)\s+(?:on|Transaction|Current|\.)",
                alert,
            )
            txn["counterparty"] = (
                sender_match.group(1).strip() if sender_match else "Unknown Sender"
            )
        # Check for Paid/Cash Out
        elif re.search(
            r"(?:paid|sent|Cash Out|transfer to|payment to)", alert, re.IGNORECASE
        ):
            txn["type"] = "withdrawal"
            # Try to extract recipient
            recipient_match = re.search(
                r"(?:to|To)\s+([A-Za-z0-9\s\-]+?)\s+(?:on|Transaction|Current|\.)",
                alert,
            )
            txn["counterparty"] = (
                recipient_match.group(1).strip()
                if recipient_match
                else "Unknown Recipient"
            )
        else:
            txn["type"] = "other"
            txn["counterparty"] = "Unknown"

        # 4. Extract Date
        date_match = re.search(r"(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2}:\d{2})?", alert)
        if date_match:
            txn["date"] = date_match.group(1)
            if date_match.group(2):
                txn["time"] = date_match.group(2)
        else:
            txn["date"] = "Unknown"

        transactions.append(txn)

    # Anonymization step (PII protection - recommended by STRIDE threat model)
    # Anonymize phone numbers if present in transaction logs
    for t in transactions:
        t["counterparty"] = re.sub(
            r"\b0\d{9}\b|\b233\d{9}\b", "[ANONYMIZED_PHONE]", str(t["counterparty"])
        )

    # Store in session state for downstream skills (append and deduplicate)
    existing_txns = tool_context.state.get("parsed_transactions", [])
    seen_ids = {t["transaction_id"] for t in existing_txns if "transaction_id" in t}

    new_txns = []
    for t in transactions:
        if t.get("transaction_id") not in seen_ids:
            new_txns.append(t)
            seen_ids.add(t["transaction_id"])

    combined_txns = existing_txns + new_txns
    tool_context.state["parsed_transactions"] = combined_txns

    return {
        "status": "success",
        "count": len(combined_txns),
        "transactions": combined_txns,
    }
