from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os
import uuid
import shutil
from datetime import datetime

from app.agent import root_agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.artifacts import InMemoryArtifactService
from google.genai import types
import app.database as db

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

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.post("/upload")
async def upload_statement(
    merchant_id: str = Form(...),
    business_name: str = Form(...),
    owner_name: str = Form(...),
    phone: str = Form(...),
    statement_text: str = Form(None),
    file: UploadFile = File(None)
):
    """Ingests statement raw text or uploaded documents (PDFs/Screenshots),
    creates a merchant profile, and executes the ADK agent workflow.
    """
    # 1. Upsert merchant record
    db.save_merchant(merchant_id, business_name, owner_name, phone)
    
    user_payload = ""
    image_path = None
    
    if file:
        if not file.filename:
            raise HTTPException(status_code=400, detail="Uploaded file has no filename.")
        file_ext = os.path.splitext(file.filename)[1].lower()
        if file_ext not in [".png", ".jpg", ".jpeg", ".pdf", ".txt"]:
            raise HTTPException(status_code=400, detail="Unsupported file format.")
            
        # Save file to upload directory
        file_id = str(uuid.uuid4())
        local_path = os.path.join(UPLOAD_DIR, f"{file_id}{file_ext}")
        with open(local_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        if file_ext in [".png", ".jpg", ".jpeg"]:
            image_path = local_path
            user_payload = f"Extract and analyze the MoMo screenshot located at: {image_path}"
        else:
            if file_ext == ".txt":
                with open(local_path, "r", encoding="utf-8") as f:
                    user_payload = f.read()
            else:
                user_payload = f"Analyze my statement PDF at path: {local_path}"
    elif statement_text:
        user_payload = statement_text
    else:
        raise HTTPException(status_code=400, detail="No file or text logs provided.")
        
    try:
        # Create ADK runner session
        session = session_service.create_session_sync(user_id=merchant_id, app_name="app")
        runner = Runner(
            agent=root_agent,
            session_service=session_service,
            artifact_service=artifact_service,
            app_name="app"
        )
        
        message = types.Content(
            role="user",
            parts=[types.Part.from_text(text=user_payload)]
        )
        
        # Run single-agent pipeline synchronously to completion
        events = list(runner.run(
            new_message=message,
            user_id=merchant_id,
            session_id=session.id
        ))
        
        # Retrieve parsed states
        session_obj = session_service.get_session_sync(
            app_name="app",
            user_id=merchant_id,
            session_id=session.id
        )
        if not session_obj:
            raise HTTPException(status_code=500, detail="Session not found after execution.")
        state = session_obj.state
        parsed_txns = state.get("categorized_transactions", state.get("parsed_transactions", []))
        credit_metrics = state.get("credit_metrics", {})
        
        # 2. Persist parsed transactions
        valid_categories = {'sales', 'inventory', 'utilities', 'logistics', 'salaries', 'taxes', 'other'}
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
                confidence=txn.get("confidence", 1.0)
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
                credit_score=score
            )
            
            db.save_credit_profile(
                merchant_id=merchant_id,
                credit_score=score,
                readiness_level=credit_metrics.get("credit_readiness_level", "Low"),
                indicator=credit_metrics.get("indicator", "RED"),
                assessment_details=credit_metrics.get("assessment_details", "")
            )
            
        return {
            "status": "success",
            "transaction_count": len(parsed_txns),
            "metrics": credit_metrics,
            "session_id": session.id
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Agent processing failed: {str(e)}")

@app.get("/transactions/{merchant_id}")
async def get_transactions(merchant_id: str):
    """Retrieves all transaction logs mapped to a merchant."""
    txns = db.get_merchant_transactions(merchant_id)
    return {"status": "success", "transactions": txns}

@app.post("/review")
async def review_transaction(transaction_id: str = Form(...), merchant_id: str = Form(...), category: str = Form(...)):
    """Receives manual merchant correction to update categories with triggers logging."""
    success = db.update_transaction_category(transaction_id, merchant_id, category)
    if not success:
        raise HTTPException(status_code=404, detail="Transaction not found.")
    return {"status": "success", "message": "Transaction category updated successfully."}

def calculate_merchant_metrics(merchant_id: str) -> dict:
    """Calculates ledger metrics dynamically from all transactions in SQLite database."""
    txns = db.get_merchant_transactions(merchant_id)
    
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
        "assessment_details": details
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
            "credit_score": metrics["credit_score"]
        }
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
            "assessment_details": metrics["assessment_details"]
        }
    }
