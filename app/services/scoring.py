import app.core.database as db


def calculate_merchant_metrics(merchant_id: str) -> dict:
    """Calculates ledger metrics dynamically from all transactions in SQLite database."""
    txns = db.get_merchant_transactions(merchant_id)

    if not txns:
        return {
            "revenue": 0.0,
            "expenses": 0.0,
            "profit": 0.0,
            "cash_flow": 0.0,
            "average_balance": 0.0,
            "credit_score": 0,
            "readiness_level": "Low",
            "indicator": "RED",
            "assessment_details": "No transaction history available. Please upload a Mobile Money statement or paste logs to generate your credit readiness profile.",
        }

    total_inflow = 0.0
    total_outflow = 0.0

    for t in txns:
        amt = float(t.get("amount", 0.0))
        if t.get("direction") == "inflow":
            total_inflow += amt
        else:
            total_outflow += amt

    net_cash_flow = total_inflow - total_outflow
    avg_balance = total_inflow * 0.18  # proxy average balance as 18% of total inflows

    expense_ratio = 0.0
    if total_inflow > 0:
        expense_ratio = (total_outflow / total_inflow) * 100

    # Derive credit score dynamically
    score = 45
    if total_inflow > 1000:
        score += 15
    if total_inflow > 3000:
        score += 15
    if net_cash_flow > 0:
        score += 15
    if expense_ratio < 45:
        score += 15
    if len(txns) >= 8:
        score += 10

    score = min(100, max(0, score))

    if score >= 75:
        level = "High"
        indicator = "GREEN"
        details = f"Strong cash flow velocity (Inflow: GHS {total_inflow:.2f}), healthy net margin, and robust transaction frequency ({len(txns)} transactions). Ready for commercial lending."
    elif score >= 50:
        level = "Medium"
        indicator = "AMBER"
        details = f"Moderate transaction consistency. Net margin is positive but expense ratio is at {expense_ratio:.1f}%. Recommended to increase sales consistency before applying."
    else:
        level = "Low"
        indicator = "RED"
        details = f"High risk due to low transaction frequency or narrow net margins (Net Profit: GHS {net_cash_flow:.2f}). Focus on building regular business sales deposits."

    return {
        "revenue": total_inflow,
        "expenses": total_outflow,
        "profit": net_cash_flow,
        "cash_flow": net_cash_flow,
        "average_balance": avg_balance,
        "credit_score": score,
        "readiness_level": level,
        "indicator": indicator,
        "assessment_details": details,
    }
