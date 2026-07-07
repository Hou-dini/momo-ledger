import hashlib
import io
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

import app.core.database as db
from app.services.scoring import calculate_merchant_metrics


def generate_lender_pdf(merchant_id: str) -> bytes:
    merchant = db.get_merchant(merchant_id)
    if not merchant:
        raise ValueError("Merchant not found")

    metrics = calculate_merchant_metrics(merchant_id)
    txns = db.get_merchant_transactions(merchant_id)

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40,
    )
    doc.title = "MoMo Ledger Credit Verification Report"
    doc.author = "MoMo Ledger AI Platform"
    doc.subject = f"Merchant Credit Verification - ID: {merchant_id}"

    story = []
    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=22,
        leading=26,
        textColor=colors.HexColor("#0F172A"),
    )

    subtitle_style = ParagraphStyle(
        "DocSubTitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#64748B"),
    )

    section_heading = ParagraphStyle(
        "SectionHeading",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#1E293B"),
        spaceAfter=6,
    )

    body_style = ParagraphStyle(
        "Body",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#334155"),
    )

    bold_body_style = ParagraphStyle(
        "BoldBody", parent=body_style, fontName="Helvetica-Bold"
    )

    right_body_style = ParagraphStyle(
        "RightBody",
        parent=body_style,
        alignment=2,  # Right aligned
    )

    right_bold_body_style = ParagraphStyle(
        "RightBoldBody",
        parent=bold_body_style,
        alignment=2,  # Right aligned
    )

    header_style = ParagraphStyle(
        "Header", parent=bold_body_style, textColor=colors.white
    )
    header_right_style = ParagraphStyle(
        "HeaderRight", parent=right_bold_body_style, textColor=colors.white
    )

    # 1. Header (Title & Meta)
    story.append(Paragraph("🇬🇭 MoMo Ledger: Credit Verification Report", title_style))
    story.append(Spacer(1, 4))
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    report_id = hashlib.md5(merchant_id.encode("utf-8")).hexdigest()[:8].upper()
    story.append(
        Paragraph(
            f"Generated on: {current_time} | Report ID: MOM-{report_id}",
            subtitle_style,
        )
    )
    story.append(Spacer(1, 12))

    # 2. Business Profile Card
    story.append(Paragraph("Business Profile", section_heading))
    profile_data = [
        [
            Paragraph("Business Name:", bold_body_style),
            Paragraph(merchant.get("business_name", ""), body_style),
            Paragraph("Owner Name:", bold_body_style),
            Paragraph(merchant.get("owner_name", ""), body_style),
        ],
        [
            Paragraph("Phone Number:", bold_body_style),
            Paragraph(merchant.get("phone", ""), body_style),
            Paragraph("Merchant ID:", bold_body_style),
            Paragraph(merchant_id, body_style),
        ],
    ]
    profile_table = Table(profile_data, colWidths=[100, 165, 100, 165])
    profile_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    story.append(profile_table)
    story.append(Spacer(1, 15))

    # 3. Credit Assessment & Readiness Indicator
    story.append(Paragraph("Credit Readiness Assessment", section_heading))

    ind = metrics.get("indicator", "RED")
    color_map = {
        "GREEN": colors.HexColor("#10B981"),
        "AMBER": colors.HexColor("#F59E0B"),
        "RED": colors.HexColor("#EF4444"),
    }
    ind_color = color_map.get(ind, colors.HexColor("#EF4444"))

    assessment_data = [
        [
            Paragraph("Credit Readiness Level:", bold_body_style),
            Paragraph(metrics.get("readiness_level", "Low"), bold_body_style),
            Paragraph("Risk Assessment:", bold_body_style),
            Paragraph(
                f"<font color='{ind_color.hexval()}'><b>{ind}</b></font>",
                body_style,
            ),
        ],
        [
            Paragraph("Financial Credit Score:", bold_body_style),
            Paragraph(f"<b>{metrics.get('credit_score', 0)} / 100</b>", body_style),
            Paragraph("Assessment Remarks:", bold_body_style),
            Paragraph(metrics.get("assessment_details", ""), body_style),
        ],
    ]

    assessment_table = Table(assessment_data, colWidths=[120, 120, 110, 180])
    assessment_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    story.append(assessment_table)
    story.append(Spacer(1, 15))

    # 4. Financial KPI Highlights
    story.append(Paragraph("Financial Summary (P&L Proxy)", section_heading))
    kpi_data = [
        [
            Paragraph("Metric", header_style),
            Paragraph("Value (GHS)", header_right_style),
            Paragraph("Description", header_style),
        ],
        [
            Paragraph("Total Inflows (Revenue)", body_style),
            Paragraph(f"{metrics['revenue']:,.2f}", right_body_style),
            Paragraph("Total deposits into the MoMo account.", body_style),
        ],
        [
            Paragraph("Total Outflows (Expenses)", body_style),
            Paragraph(f"{metrics['expenses']:,.2f}", right_body_style),
            Paragraph("Total payments/withdrawals from account.", body_style),
        ],
        [
            Paragraph("Net Cash Flow (Profit)", body_style),
            Paragraph(f"{metrics['profit']:,.2f}", right_body_style),
            Paragraph("Net profit proxy from cash velocity.", body_style),
        ],
        [
            Paragraph("Average Balance Proxy", body_style),
            Paragraph(f"{metrics['average_balance']:,.2f}", right_body_style),
            Paragraph("18% of total inflows proxy.", body_style),
        ],
    ]
    kpi_table = Table(kpi_data, colWidths=[150, 100, 280])
    kpi_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F172A")),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                (
                    "ROWBACKGROUNDS",
                    (0, 1),
                    (-1, -1),
                    [colors.white, colors.HexColor("#F8FAFC")],
                ),
            ]
        )
    )
    story.append(kpi_table)
    story.append(Spacer(1, 15))

    # 5. Ledger Statement
    story.append(Paragraph("Categorized Business Ledger", section_heading))
    ledger_headers = [
        Paragraph("Date", header_style),
        Paragraph("Category", header_style),
        Paragraph("Counterparty (Anonymized)", header_style),
        Paragraph("Type", header_style),
        Paragraph("Amount (GHS)", header_right_style),
    ]
    ledger_rows = [ledger_headers]
    for t in txns:
        ledger_rows.append(
            [
                Paragraph(t.get("timestamp", ""), body_style),
                Paragraph(t.get("category", "other").capitalize(), body_style),
                Paragraph(t.get("counterparty", "Unknown"), body_style),
                Paragraph(t.get("direction", "outflow").capitalize(), body_style),
                Paragraph(f"{t.get('amount', 0.0):,.2f}", right_body_style),
            ]
        )

    ledger_table = Table(ledger_rows, colWidths=[70, 70, 220, 70, 100])
    ledger_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E293B")),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                (
                    "ROWBACKGROUNDS",
                    (0, 1),
                    (-1, -1),
                    [colors.white, colors.HexColor("#F8FAFC")],
                ),
            ]
        )
    )
    story.append(ledger_table)

    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
