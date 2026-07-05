# Technical System Writeup: MoMo Ledger

This writeup documents the system architecture, mathematical scoring frameworks, database schema designs, and algorithmic details of the MoMo Ledger prototype.

---

## 1. System Architecture

MoMo Ledger is designed as a **single-agent coordinator with tool-based skills** implemented using **Google ADK (Agent Development Kit) 2.0+** and served by a local **FastAPI / SQLite** stack.

```
+-------------------------------------------------------------+
|                      React / Next.js UI                     |
+------------------------------+------------------------------+
                               | (HTTP / JSON / Form-Data)
                               v
+-------------------------------------------------------------+
|                      FastAPI API Server                     |
+------------------------------+------------------------------+
                               |
                               +-----------------------+
                               | (Session State)       | (SQL CRUD)
                               v                       v
+----------------------------------------+     +--------------+
|     ADK 2.0 Agent Coordinator          |     | SQLite DB    |
|       (Runs gemini-3.5-flash)          |     | (momo.db)    |
+---+--------------------------------+---+     +-------+------+
    |                                |                 ^
    | (OCR OCR OCR)                  | (Regex Logs)    |
    v                                v                 | (Audit Sync)
+------------------------+      +--------------------+ |
| extract_momo_from_img  |      | parse_statement    | |
+------------------------+      +--------------------+ |
    |                                |                 |
    +--------------------------------+                 |
                                     v                 |
                        +----------------------------+ |
                        | categorize_transactions    | |
                        +--------------+-------------+ |
                                       |               |
                                       v               |
                        +----------------------------+ |
                        | assess_credit_readiness    | |
                        +--------------+-------------+ |
                                       |               |
                                       v               |
                        +----------------------------+ |
                        | generate_ledger_report     |--+
                        +----------------------------+
```

---

## 2. Embedded Database Schema & Python Audit Triggers

To support rapid, local-first deployment, the prototype uses an embedded **SQLite** instance (`momo.db`) with tables corresponding to the target relational model.

### 2.1 Table Schemas

#### 1. `merchants`
Stores basic MSME profile details:
* `id` (TEXT PRIMARY KEY)
* `business_name` (TEXT NOT NULL)
* `owner_name` (TEXT NOT NULL)
* `phone` (TEXT NOT NULL)
* `created_at` (TEXT DEFAULT CURRENT_TIMESTAMP)

#### 2. `transactions`
Contains the core book ledger items. Employs constraint checks on categories and directions:
* `id` (TEXT PRIMARY KEY)
* `merchant_id` (TEXT FOREIGN KEY)
* `timestamp` (TEXT NOT NULL)
* `amount` (REAL NOT NULL)
* `direction` (TEXT CHECK(direction IN ('inflow', 'outflow')))
* `counterparty` (TEXT NOT NULL)
* `category` (TEXT CHECK(category IN ('sales', 'inventory', 'utilities', 'logistics', 'salaries', 'taxes', 'other')))
* `confidence` (REAL NOT NULL)
* `reviewed_flag` (INTEGER DEFAULT 0)
* `raw_payload` (TEXT)

#### 3. `financial_summaries`
Maintains historical records of cash flow assessments:
* `id` (TEXT PRIMARY KEY)
* `merchant_id` (TEXT FOREIGN KEY)
* `revenue` (REAL NOT NULL)
* `expenses` (REAL NOT NULL)
* `profit` (REAL NOT NULL)
* `cash_flow` (REAL NOT NULL)
* `average_balance` (REAL NOT NULL)
* `credit_score` (INTEGER NOT NULL)
* `calculated_at` (TEXT DEFAULT CURRENT_TIMESTAMP)

#### 4. `credit_profiles`
Maintains lender-ready diagnostic rating alerts:
* `id` (TEXT PRIMARY KEY)
* `merchant_id` (TEXT FOREIGN KEY)
* `credit_score` (INTEGER NOT NULL)
* `readiness_level` (TEXT NOT NULL)
* `indicator` (TEXT CHECK(indicator IN ('RED', 'AMBER', 'GREEN')))
* `assessment_details` (TEXT NOT NULL)
* `created_at` (TEXT DEFAULT CURRENT_TIMESTAMP)

#### 5. `audit_logs`
An immutable log tracking all database modifications (INSERT, UPDATE, DELETE):
* `id` (TEXT PRIMARY KEY)
* `merchant_id` (TEXT)
* `action` (TEXT NOT NULL)
* `table_name` (TEXT NOT NULL)
* `record_id` (TEXT NOT NULL)
* `old_data` (TEXT JSON serialization)
* `new_data` (TEXT JSON serialization)
* `performed_at` (TEXT DEFAULT CURRENT_TIMESTAMP)

### 2.2 Python-Based Trigger Replication
To maintain portability on SQLite without writing platform-specific database hooks, the triggers are implemented directly within the Python database layer. The `log_audit()` wrapper serializes the database rows to JSON strings and inserts them into the audit table as part of a single transaction:

```python
def log_audit(conn, merchant_id: str, action: str, table_name: str, record_id: str, old_data: dict = None, new_data: dict = None):
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO audit_logs (id, merchant_id, action, table_name, record_id, old_data, new_data)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (str(uuid.uuid4()), merchant_id, action, table_name, record_id,
          json.dumps(old_data) if old_data else None,
          json.dumps(new_data) if new_data else None))
```

---

## 3. Dynamic Credit Scoring Framework

The score (scale 0–100) is calculated dynamically from ledger transactions using a five-factor consistency model:

$$\text{Credit Score} = \text{Base} + S_{\text{volume}} + S_{\text{consistency}} + S_{\text{margin}} + S_{\text{frequency}}$$

| Metric Factor | Rule Description | Max Points |
| :--- | :--- | :---: |
| **Base Score** | Default base starting rating. | 45 |
| **Transaction Volume** | $+15$ if total inflows $> \text{GHS } 1,000$, $+30$ if $> \text{GHS } 3,000$. | 30 |
| **Cash-Flow Stability** | $+15$ if total inflows exceed total outflows (positive cash flow margin). | 15 |
| **Expense-to-Revenue Ratio** | $+15$ if total operating expenses are less than $45\%$ of total revenues. | 15 |
| **Transaction Frequency** | $+10$ if there are at least 8 transactions overall in the statement lifecycle. | 10 |

### Readiness Diagnostics:
* **GREEN (High Readiness)**: Score $\ge 75$. Indicates positive margins, healthy cash flow buffers, stable business activity, and high lending viability.
* **AMBER (Medium Readiness)**: Score $50 \text{ to } 74$. Positive net cash flow but high operating expenses or low volumes. Recommended to monitor cost controls.
* **RED (Low Readiness)**: Score $< 50$. Insufficient inflows, net deficit, or high default risk.

---

## 4. OCR Multimodal Ingestion Pipeline

When an image statement (screenshot) is uploaded, the system coordinates extraction through a specialized vision parser:

1. **`extract_momo_from_image`** is called with the image path.
2. The image is passed directly to the Gemini 3.5 Flash multimodal model using the system instruction:
   > *"You are an expert OCR and document intelligence engine. Extract all Mobile Money (MoMo) transaction records from the provided screenshot. Return the raw transaction lines exactly as text logs, preserving dates, counterparties, direction, and transaction IDs."*
3. The extracted text is then forwarded directly to the regex parser engine (`parse_momo_statement`) to yield structured dictionary entries, completely bypassing manual OCR templates.

---

## 5. CI/CD & Workload Identity Federation (WIF)

For secure and automated deployment to Google Cloud Run, the system uses a keyless **OIDC-based authentication** pipeline integrated with **GitHub Actions**.

### 5.1 Authentication Flow
Instead of using long-lived JSON keys, GitHub Actions retrieves short-lived access tokens from GCP dynamically during runtime:

```
[GitHub Actions Runner]                     [Google STS Pool]                   [GCP Service Account]
          |                                         |                                     |
          | 1. Request OIDC Token (id-token:write)   |                                     |
          +---------------------------------------->|                                     |
          |                                         |                                     |
          | 2. Validate OIDC assertion claims       |                                     |
          |    (matches Hou-dini/momo-ledger)       |                                     |
          |    and issue Google token               |                                     |
          |<----------------------------------------+                                     |
          |                                                                               |
          | 3. Impersonate using TokenCreator role                                         |
          +------------------------------------------------------------------------------>|
          |                                                                               |
          | 4. Deploy service and push container images                                   |
          |<------------------------------------------------------------------------------+
```

### 5.2 Workload Identity Configuration
* **Identity Pool**: `github-pool` (Scope global)
* **Pool Provider**: `github-provider` (Issuer: `https://token.actions.githubusercontent.com`)
* **Repository Constraints Attribute Mapping**:
  * `google.subject` = `assertion.sub`
  * `attribute.repository` = `assertion.repository`
  * `attribute.repository_owner` = `assertion.repository_owner`
* **Attribute Condition**: `assertion.repository == 'Hou-dini/momo-ledger'` (only allows builds from our specific repository).
* **Impersonation Target**: `momo-ledger-deployer@vibe-coding-intensive-course.iam.gserviceaccount.com` (assigned roles: `roles/run.admin`, `roles/artifactregistry.admin`, `roles/storage.admin`, and `roles/iam.serviceAccountUser`).

