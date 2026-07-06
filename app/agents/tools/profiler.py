from google.adk.tools.tool_context import ToolContext


def assess_credit_readiness(tool_context: ToolContext) -> dict:
    """Performs financial analysis and credit-readiness checks on categorized transactions.
    Calculates net cash flow, business expense ratios, and evaluates credit readiness metrics.

    Args:
        tool_context: The ADK tool execution context containing session state.

    Returns:
        A dictionary containing financial metrics and credit-readiness status.
    """
    categorized = tool_context.state.get("categorized_transactions")
    totals = tool_context.state.get("category_totals")

    if not categorized or not totals:
        return {
            "status": "error",
            "message": "No categorized transactions found. Run categorize_momo_transactions first.",
        }

    total_inflow = 0.0
    total_outflow = 0.0

    for txn in categorized:
        amount = txn.get("amount", 0.0)
        txn_type = txn.get("type", "other")
        if txn_type == "deposit":
            total_inflow += amount
        elif txn_type == "withdrawal":
            total_outflow += amount

    net_cash_flow = total_inflow - total_outflow
    expense_ratio = (total_outflow / total_inflow) if total_inflow > 0 else 1.0

    # Credit readiness rules
    if len(categorized) < 3:
        readiness = "Low (Insufficient transaction history)"
        color_code = "RED"
        details = "The business has too few recorded transactions to establish a stable cash flow profile."
    elif total_inflow == 0:
        readiness = "Low (No business revenues recorded)"
        color_code = "RED"
        details = "No inflows or customer sales were detected in the transactions."
    elif net_cash_flow < 0:
        readiness = "Medium-Low (Negative net cash flow)"
        color_code = "ORANGE"
        details = "The business expenses exceed monthly revenues, indicating cash flow deficits."
    elif expense_ratio > 0.85:
        readiness = "Medium (High expense ratio)"
        color_code = "YELLOW"
        details = "Revenues are healthy, but expenses exhaust over 85% of inflows, leaving low debt servicing capacity."
    else:
        readiness = "High (Strong cash flow & low expense ratio)"
        color_code = "GREEN"
        details = "Excellent cash flow velocity, positive net margins, and controlled expenses. Highly ready for credit financing."

    metrics = {
        "total_inflow": round(total_inflow, 2),
        "total_outflow": round(total_outflow, 2),
        "net_cash_flow": round(net_cash_flow, 2),
        "expense_ratio_pct": round(expense_ratio * 100, 2),
        "transaction_count": len(categorized),
        "credit_readiness_level": readiness,
        "indicator": color_code,
        "assessment_details": details,
    }

    # Store metrics in session state
    tool_context.state["credit_metrics"] = metrics

    return {"status": "success", "metrics": metrics}
