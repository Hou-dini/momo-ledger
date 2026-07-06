import io
import os
import shutil
import uuid
from datetime import datetime

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from google.adk.artifacts import InMemoryArtifactService
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

import app.core.database as db
from app.agents.coordinator import root_agent
from app.services.pdf_generator import generate_lender_pdf
from app.services.scoring import calculate_merchant_metrics

app = FastAPI(title="MoMo Ledger API")

# Enable CORS for Next.js frontend calls
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

session_service = InMemorySessionService()
artifact_service = InMemoryArtifactService()

UPLOAD_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads"
)
os.makedirs(UPLOAD_DIR, exist_ok=True)


@app.post("/upload")
async def upload_statement(
    merchant_id: str = Form(...),
    business_name: str = Form(...),
    owner_name: str = Form(...),
    phone: str = Form(...),
    statement_text: str = Form(None),
    file: UploadFile = File(None),
    files: list[UploadFile] = File(None),
):
    """Ingests statement raw text or multiple uploaded documents (PDFs/Screenshots),
    creates a merchant profile, and executes the ADK agent workflow.
    """
    # 1. Upsert merchant record
    db.save_merchant(merchant_id, business_name, owner_name, phone)

    all_files = []
    if file and file.filename:
        all_files.append(file)
    if files:
        for f in files:
            if f.filename:
                all_files.append(f)

    user_payloads = []

    for f in all_files:
        file_ext = os.path.splitext(f.filename or "")[1].lower()
        if file_ext not in [".png", ".jpg", ".jpeg", ".pdf", ".txt"]:
            raise HTTPException(
                status_code=400, detail=f"Unsupported file format for {f.filename}."
            )

        # Save file to upload directory
        file_id = str(uuid.uuid4())
        local_path = os.path.join(UPLOAD_DIR, f"{file_id}{file_ext}")
        with open(local_path, "wb") as buffer:
            shutil.copyfileobj(f.file, buffer)

        if file_ext in [".png", ".jpg", ".jpeg"]:
            user_payloads.append(
                f"Extract and analyze the MoMo screenshot located at: {local_path}"
            )
        elif file_ext == ".pdf":
            user_payloads.append(
                f"Extract and analyze the MoMo PDF statement located at: {local_path}"
            )
        elif file_ext == ".txt":
            with open(local_path, encoding="utf-8") as file_read:
                user_payloads.append(file_read.read())

    # Build user payload
    if user_payloads:
        user_payload = "\n\n".join(user_payloads)
    else:
        user_payload = ""

    # Append manual statement text if provided alongside the files
    if statement_text:
        if user_payload:
            user_payload += f"\n\nAlso parse and combine these manual transaction alerts:\n{statement_text}"
        else:
            user_payload = statement_text

    if not user_payload:
        raise HTTPException(
            status_code=400,
            detail="No files or manual statement text logs were provided.",
        )

    try:
        # Create ADK runner session
        session = await session_service.create_session(
            user_id=merchant_id, app_name="app"
        )
        runner = Runner(
            agent=root_agent,
            session_service=session_service,
            artifact_service=artifact_service,
            app_name="app",
        )

        message = types.Content(
            role="user", parts=[types.Part.from_text(text=user_payload)]
        )

        # Run single-agent pipeline asynchronously to completion
        events = []
        async for event in runner.run_async(
            new_message=message, user_id=merchant_id, session_id=session.id
        ):
            events.append(event)

        # Retrieve parsed states
        session_obj = await session_service.get_session(
            app_name="app", user_id=merchant_id, session_id=session.id
        )
        if not session_obj:
            raise HTTPException(
                status_code=500, detail="Session not found after execution."
            )
        state = session_obj.state
        parsed_txns = state.get(
            "categorized_transactions", state.get("parsed_transactions", [])
        )
        credit_metrics = state.get("credit_metrics", {})

        # 2. Persist parsed transactions
        valid_categories = {
            "sales",
            "inventory",
            "utilities",
            "logistics",
            "salaries",
            "taxes",
            "other",
        }
        for txn in parsed_txns:
            cat = txn.get("category", "other").lower()
            if cat not in valid_categories:
                cat = "other"
            db.save_transaction(
                merchant_id=merchant_id,
                timestamp=txn.get("date", datetime.now().strftime("%Y-%m-%d")),
                amount=txn.get("amount", 0.0),
                direction="inflow" if txn.get("type") == "deposit" else "outflow",
                counterparty=txn.get("counterparty", "Unknown"),
                category=cat,
                confidence=txn.get("confidence", 1.0),
            )

        # 3. Persist summary & credit results
        if credit_metrics:
            revenue = credit_metrics.get("total_inflow", 0.0)
            expenses = credit_metrics.get("total_outflow", 0.0)
            profit = credit_metrics.get("net_cash_flow", 0.0)

            # Simple derived credit score model (consistency/volume weighted)
            score = 30
            if credit_metrics.get("indicator") == "GREEN":
                score = 85
            elif credit_metrics.get("indicator") == "AMBER":
                score = 60

            db.save_financial_summary(
                merchant_id=merchant_id,
                revenue=revenue,
                expenses=expenses,
                profit=profit,
                cash_flow=profit,
                average_balance=credit_metrics.get("average_balance", 0.0),
                credit_score=score,
            )

            db.save_credit_profile(
                merchant_id=merchant_id,
                credit_score=score,
                readiness_level=credit_metrics.get("credit_readiness_level", "Low"),
                indicator=credit_metrics.get("indicator", "RED"),
                assessment_details=credit_metrics.get("assessment_details", ""),
            )

        return {
            "status": "success",
            "transaction_count": len(parsed_txns),
            "metrics": credit_metrics,
            "session_id": session.id,
        }
    except Exception as e:
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Agent processing failed: {e!s}")


@app.get("/transactions/{merchant_id}")
async def get_transactions(merchant_id: str):
    """Retrieves all transaction logs mapped to a merchant."""
    txns = db.get_merchant_transactions(merchant_id)
    return {"status": "success", "transactions": txns}


@app.post("/review")
async def review_transaction(
    transaction_id: str = Form(...),
    merchant_id: str = Form(...),
    category: str = Form(...),
):
    """Receives manual merchant correction to update categories with triggers logging."""
    success = db.update_transaction_category(transaction_id, merchant_id, category)
    if not success:
        raise HTTPException(status_code=404, detail="Transaction not found.")
    return {
        "status": "success",
        "message": "Transaction category updated successfully.",
    }


@app.get("/report/{merchant_id}")
async def get_report(merchant_id: str):
    """Gets latest financial ledger summary computed dynamically from ledger transactions."""
    metrics = calculate_merchant_metrics(merchant_id)
    return {
        "status": "success",
        "summary": {
            "revenue": metrics["revenue"],
            "expenses": metrics["expenses"],
            "profit": metrics["profit"],
            "cash_flow": metrics["cash_flow"],
            "average_balance": metrics["average_balance"],
            "credit_score": metrics["credit_score"],
        },
    }


@app.get("/score/{merchant_id}")
async def get_score(merchant_id: str):
    """Gets latest credit score profile computed dynamically from ledger transactions."""
    metrics = calculate_merchant_metrics(merchant_id)
    return {
        "status": "success",
        "profile": {
            "credit_score": metrics["credit_score"],
            "readiness_level": metrics["readiness_level"],
            "indicator": metrics["indicator"],
            "assessment_details": metrics["assessment_details"],
        },
    }


@app.get("/download-pdf/{merchant_id}")
async def download_pdf_report(merchant_id: str):
    """Generates and returns the beautifully compiled credit report as a PDF download."""
    try:
        pdf_bytes = generate_lender_pdf(merchant_id)
        # Prepare business name for the filename
        merchant = db.get_merchant(merchant_id)
        biz_name = merchant.get("business_name", "merchant") if merchant else "merchant"
        safe_biz_name = (
            "".join(c for c in biz_name if c.isalnum() or c in (" ", "_", "-"))
            .strip()
            .replace(" ", "_")
        )
        filename = f"{safe_biz_name}_credit_report.pdf"

        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to generate PDF: {e!s}")


static_dir = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "static",
)
if os.path.exists(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
