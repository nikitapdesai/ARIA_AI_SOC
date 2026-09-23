# ARIA â€” Alert Ranking \& Intelligence Agent

AI-assisted SOC alert prioritization using deep learning-based network intrusion detection, retrieval-augmented alert correlation, explainable scoring, and continual threat-knowledge learning.

## What this is

ARIA is not a network intrusion classifier alone â€” it's a four-agent pipeline that takes raw network flow classification and turns it into ranked, explained, escalated SOC alerts, mimicking a real security operations triage workflow:

```
Network Flow -> Detection Agent -> Correlation Agent -> Priority-Explainer Agent -> Escalation Agent -> API -> Frontend
```

The agents are served live via a FastAPI backend (`backend/api/`) and viewed through a React frontend (`frontend/`) â€” including a genuinely dynamic "Live Analyze" page that runs a brand-new flow through the whole chain on demand, not just a viewer over pre-computed CSVs.

## Architecture

|Agent|Role|Key technique|
|-|-|-|
|Detection Agent|Classifies network flows into 15 classes (BENIGN + 14 attack types)|Stacked ensemble: MLP + Random Forest + Logistic Regression meta-model|
|Correlation Agent|Groups alerts by source + time, detects multi-stage attack campaigns|Sentence Transformers + FAISS (RAG-style retrieval against a MITRE ATT\&CK-tagged knowledge base)|
|Priority-Explainer Agent|Scores alert urgency, explains the "why"|Weighted priority formula + SHAP feature attribution|
|Escalation Agent|Logs high-risk incidents, grows the knowledge base|Novelty detection via embedding similarity, persistent incident log|

## Setup

```powershell
cd backend
python -m venv venv
.\\\\venv\\\\Scripts\\\\Activate.ps1
pip install -r requirements.txt --break-system-packages
cd ..

cd frontend
npm install
cd ..
```

## Project structure

```
AI_SOC_clean_final/

|-- backend/

|   |-- data/

|   |   |-- raw/                  # original CIC-IDS2017 files

|   |   |-- processed/            # cleaned, combined, standardized data

|   |   |-- model_ready/          # train/test arrays and alert streams

|   |   `-- escalation/           # runtime incident/checkpoint data

|   |-- preprocessing/            # cleaning and feature engineering

|   |-- model/                    # MLP, Random Forest, ensemble training

|   |-- agents/                   # four agents and correlation evaluation

|   |-- utils/                    # alert stream simulator

|   |-- knowledge_base/           # attack campaign patterns

|   |-- api/                      # FastAPI backend

|   `-- run_pipeline.py           # full offline pipeline

|-- results/                      # evaluation reports and metrics

`-- frontend/                     # React + Vite + TypeScript UI

```

Everything Python-related lives under `backend/` -- all commands below assume you've `cd backend` first unless noted otherwise. Internal paths in the code (e.g. `data/model_ready/...`) are relative to `backend/` for that reason.

## Running the full pipeline

Assumes preprocessing and model training have already been run once (see below for first-time setup).

```powershell
cd backend
python run_pipeline.py

# terminal 1, from backend/
uvicorn api.main:app --reload

# terminal 2, from frontend/
npm run dev
```

Open the URL Vite prints (typically http://localhost:5173). The dev server proxies `/api/\\\*` to the FastAPI backend on port 8002.

## First-time setup (data -> trained models -> running app)

Run once, in order, from `backend/`:

```powershell
cd backend
python preprocessing/clean_data.py
python preprocessing/combine_standardise.py
python preprocessing/feature_engineering.py
python model/train_mlp.py
python model/train_random_forest.py
python model/train_ensemble.py
python agents/detection_agent.py    # smoke test
python run_pipeline.py

uvicorn api.main:app --reload                             # terminal 1, from backend/
cd ../frontend \\\&\\\& npm install \\\&\\\& npm run dev               # terminal 2, from frontend/
```

## API

The FastAPI backend (`backend/api/main.py`) wraps all 4 agents as live HTTP endpoints -- see `backend/api/routers/` for the full set: `/api/overview`, `/api/alerts`, `/api/analytics`, `/api/incidents`, `/api/knowledge-base` (including `/search`, a semantic lookup against the FAISS index), and `/api/live/analyze` -- the one genuinely dynamic route, which runs a brand-new (or client-specified) network flow through Detection -> Correlation -> Priority-Explainer -> Escalation on demand and returns the full per-agent trace. `/api/live/stream` exposes the same thing as a server-sent-events feed. Interactive API docs are available at `/docs` once the server is running.

## Known dataset limitations

* This CIC-IDS2017 redistribution excludes Source/Destination IP columns -- `utils/alert_simulator.py` generates a clearly-documented simulated alert stream to demonstrate the Correlation Agent.
* Web Attack - SQL Injection (21 total samples) and Heartbleed (11 total samples) are too data-scarce to classify reliably regardless of technique -- confirmed via a targeted SMOTE experiment (`preprocessing/apply_smote.py`).

## Evaluation summary

See `results/` for full classification reports. Headline result: stacked ensemble chosen over standalone Random Forest for superior confidence calibration (ROC-AUC 0.992 vs 0.982), despite marginally lower macro F1 (0.78 vs 0.82) -- calibrated confidence feeds directly into the Priority-Explainer Agent's scoring formula.
