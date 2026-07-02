from google.adk.tools.tool_context import ToolContext
from google.genai import types

async def generate_ledger_report(tool_context: ToolContext) -> dict:
    """Compiles the categorized ledger and credit-readiness assessment into a Markdown report
    and saves it securely as a session artifact.

    Args:
        tool_context: The ADK tool execution context containing session state and artifact methods.

    Returns:
        A dictionary containing the report content and the saved artifact details.
    """
    categorized = tool_context.state.get("categorized_transactions")
    metrics = tool_context.state.get("credit_metrics")

    if not categorized or not metrics:
        return {"status": "error", "message": "Missing transaction or credit analysis metrics."}

    # Generate Markdown Report
    report = []
    report.append("# 🇬🇭 MoMo Ledger: Credit Readiness & Business Statement")
    report.append("")
    report.append("## 📈 Financial Health Summary")
    report.append(f"* **Total Business Inflows (Revenues)**: GHS {metrics['total_inflow']:,.2f}")
    report.append(f"* **Total Business Outflows (Expenses)**: GHS {metrics['total_outflow']:,.2f}")
    report.append(f"* **Net Cash Flow**: GHS {metrics['net_cash_flow']:,.2f}")
    report.append(f"* **Expense-to-Revenues Ratio**: {metrics['expense_ratio_pct']}%")
    report.append(f"* **Transaction Count**: {metrics['transaction_count']}")
    report.append("")
    report.append("## 🛡️ Credit Readiness Profile")
    report.append(f"* **Assessment Level**: **{metrics['credit_readiness_level']}**")
    report.append(f"* **Risk Indicator**: `{metrics['indicator']}`")
    report.append(f"* **Assessment Details**: {metrics['assessment_details']}")
    report.append("")
    report.append("## 📝 Categorized Ledger")
    report.append("| Date | Category | Counterparty | Type | Amount (GHS) |")
    report.append("| :--- | :--- | :--- | :--- | :--- |")
    
    for txn in categorized:
        date = txn.get("date", "Unknown")
        cat = txn.get("category", "General")
        party = txn.get("counterparty", "Unknown")
        t_type = txn.get("type", "Other")
        amount = txn.get("amount", 0.0)
        report.append(f"| {date} | {cat} | {party} | {t_type} | {amount:,.2f} |")

    report_text = "\n".join(report)

    # Save to ADK Artifact Service (session-scoped namespace to maintain user separation)
    report_bytes = report_text.encode("utf-8")
    part = types.Part(inline_data=types.Blob(mime_type="text/markdown", data=report_bytes))
    
    # Save the artifact asynchronously
    version = await tool_context.save_artifact("momo_ledger_report.md", part)

    return {
        "status": "success",
        "artifact_name": "momo_ledger_report.md",
        "version": version,
        "report_summary": report_text
    }
