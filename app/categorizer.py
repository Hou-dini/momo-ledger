from google.adk.tools.tool_context import ToolContext

def categorize_momo_transactions(tool_context: ToolContext) -> dict:
    """Categorizes the parsed transactions into standard accounting categories.
    Reads transactions from the session state, evaluates keywords, and tags categories.

    Args:
        tool_context: The ADK tool execution context containing session state.

    Returns:
        A dictionary containing categorized transactions and totals by category.
    """
    transactions = tool_context.state.get("parsed_transactions")
    if not transactions:
        return {"status": "error", "message": "No parsed transactions found. Run parse_momo_statement first."}

    # Standard business keywords for category matching in Ghana
    rules = {
        "sales": [r"payment received", r"customer", r"sales", r"credit", r"momo merchant", r"received from"],
        "inventory": [r"wholesale", r"supplier", r"distributor", r"goods", r"restock", r"purchase from"],
        "logistics": [r"transport", r"fuel", r"delivery", r"cargo", r"bolt", r"yango", r"uber", r"dispatch"],
        "utilities": [r"ecg", r"electricity", r"gwcl", r"water", r"dstv", r"gotv", r"telecel", r"mtn credit", r"internet", r"data bundle"],
        "salaries": [r"salary", r"wages", r"staff", r"allowance", r"employee"],
        "taxes": [r"gra", r"tax", r"revenue authority", r"e-levy", r"levy"],
    }

    categorized = []
    category_totals = {}

    for txn in transactions:
        desc = txn.get("counterparty", "").lower()
        txn_type = txn.get("type", "other")
        amount = txn.get("amount", 0.0)

        # Default fallback category based on transaction flow
        category = "general_inflow" if txn_type == "deposit" else "general_outflow"

        # Apply keyword matching rules
        matched = False
        for cat, keywords in rules.items():
            for kw in keywords:
                if kw in desc or (cat == "sales" and txn_type == "deposit"):
                    # Sales logic matches deposits from unknown customers
                    category = cat
                    matched = True
                    break
            if matched:
                break

        txn_copy = dict(txn)
        txn_copy["category"] = category
        categorized.append(txn_copy)

        # Update totals
        category_totals[category] = category_totals.get(category, 0.0) + amount

    # Store categorized list in state
    tool_context.state["categorized_transactions"] = categorized
    tool_context.state["category_totals"] = category_totals

    return {
        "status": "success",
        "count": len(categorized),
        "category_totals": category_totals,
        "transactions": categorized
    }
