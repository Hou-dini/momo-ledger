# Development Log: MoMo Ledger

This log serves as a chronological record of implementation steps, development sessions, and technical modifications made during the creation of the MoMo Ledger prototype.

---

## Session Log: July 2, 2026

### 1. ADK 2.0 & Gemini 3.5 Flash Migration
* **Goal**: Upgrade the core Agent Development Kit to ADK 2.0+ and migrate model engines to `gemini-3.5-flash`.
* **Changes**:
  * Upgraded dependency constraints to `"google-adk>=2.0.0"` and `"google-adk[eval]>=2.0.0"` in [pyproject.toml](./pyproject.toml).
  * Synced environment using `uv sync --extra eval` to load click, pandas, and nltk packages required by the ADK evaluation runner.
  * Migrated the core orchestrator model in [agent.py](./app/agent.py) and the multimodal engine in [vision_parser.py](./app/vision_parser.py) to target `gemini-3.5-flash`.
  * Set judge parameters in [eval_config.json](./tests/eval/eval_config.json) to use `gemini-3.5-flash` for evaluation runs.

### 2. Local SQLite Database Integration
* **Goal**: Replace Supabase integration with a local-first SQLite instance for MSME privacy and ease of prototyping.
* **Changes**:
  * Scaffolding SQLite schemas for `merchants`, `transactions`, `financial_summaries`, `credit_profiles`, and `audit_logs` in [database.py](./app/database.py).
  * Implemented Python mutation triggers to log all inserts and updates to the `audit_logs` table automatically, mirroring relational trigger designs.
  * Configured dynamic database creation (`momo.db`) on application import inside [__init__.py](./app/__init__.py).

### 3. Screenshot Vision Ingestion & OCR
* **Goal**: Support uploading image files of Mobile Money transaction alerts alongside standard SMS logs.
* **Changes**:
  * Created [vision_parser.py](./app/vision_parser.py) to parse screenshot files (PNG/JPEG/JPG) using Gemini's multimodal capabilities, extracting raw text and passing it directly to the statement parser.
  * Registered `extract_momo_from_image` as an ADK tool capability.

### 4. Stage 3 Routing and Web Dashboard Scaffolding
* **Goal**: Connect backend database handlers to web routes and build a responsive frontend.
* **Changes**:
  * Added `fastapi`, `uvicorn`, and `python-multipart` backend dependencies.
  * Created [routes.py](./app/routes.py) exposing `/upload`, `/transactions/{id}`, `/review`, `/report/{id}`, and `/score/{id}`.
  * Bootstrapped a TypeScript App Router Next.js app inside [frontend/](./frontend/) and implemented a dark-mode theme bookkeeping dashboard in [page.tsx](./frontend/src/app/page.tsx).

---

## Core Troubleshooting Snapshots & Hotfixes

### Pitfall 1: ADK 2.0 Name Matching Exception
* **Issue**: The agent name configuration mismatches the parent import directories, raising class loader errors.
* **Fix**: Aligned the core App name configuration to `app` inside [agent.py](./app/agent.py).

### Pitfall 2: ADK 2.0 Runner ValueError: Artifact Service Not Initialized
* **Issue**: In [routes.py](./app/routes.py), instantiating `Runner` manually caused tools calling `tool_context.save_artifact` to raise a `ValueError` because the default service was not set.
* **Fix**: Imported `InMemoryArtifactService` from `google.adk.artifacts` and passed it into the `Runner` constructor.

### Pitfall 3: Browser CORS Network Blocking
* **Issue**: Combining `allow_origins=["*"]` with `allow_credentials=True` is a standard CORS protocol violation, causing browsers to block API calls.
* **Fix**: Set explicit origins to local Next.js client instances: `allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"]`.

### Pitfall 4: Static Summaries vs. Multi-Statement Aggregation
* **Issue**: The P&L cards and credit scoring indicators on the dashboard failed to update when uploading multiple statements or when correcting categories, as they pulled from a static database entry.
* **Fix**: Rewrote `/report` and `/score` handlers in [routes.py](./app/routes.py) to aggregate metrics dynamically from the live `transactions` table.

---

## Session Log: July 5, 2026

### 1. GitHub Actions CI/CD Scaffolding
* **Goal**: Enable fully automated staging and production deployment of the Cloud Run backend via GitHub Actions.
* **Changes**:
  * Ran `scaffold enhance` to bootstrap workflows for pull request checks (`pr_checks.yaml`), dev/staging deploys (`staging.yaml`), and manual production deployment promotions (`deploy-to-prod.yaml`).
  * Created `Dockerfile` configuring the container runtime for Python slim and compiling the UV workspace.
  * Corrected container startup instruction inside [Dockerfile](./Dockerfile) to run our custom bookkeeping routes `app.routes:app` instead of the default agent playground server.

### 2. Workload Identity Federation (WIF) Scaffolding
* **Goal**: Set up secure, keyless authentication between GitHub Actions and Google Cloud Platform (GCP) using OpenID Connect (OIDC).
* **Changes**:
  * Activated `iamcredentials` API on the project.
  * Created a global pool `github-pool` and OIDC identity provider `github-provider` mapping attributes to `Hou-dini/momo-ledger` repository assertions.
  * Created a deployment service account `momo-ledger-deployer` and bound repository OIDC credentials.
  * Configured IAM roles for Artifact Registry, Cloud Run deployment administration, GCS buckets storage, and Service Account impersonation user bindings.
  * Provisioned Artifact Registry repository `momo-ledger-repo` and staging logs bucket `vibe-coding-intensive-course-staging-logs`.
  * Hardcoded the Workload Provider URIs and account IDs directly in workflow files to allow keyless authentication without requiring manual secret configurations on GitHub.

