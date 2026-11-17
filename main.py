from fastapi import FastAPI, Depends, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse
from auth import get_api_key
from schemas import IngestResponse, EvaluateResponse, AlertResponse
from services.ingest import ingest_csv
from services.evaluate import evaluate_devices
from services.alert import process_outbox
import os

app = FastAPI(
    title="Endpoint Compliance Auditor V2",
    description="A distributed compliance service with Transactional Outbox pattern.",
    version="2.0.0"
)

# --- API Endpoints ---

@app.post("/ingest", response_model=IngestResponse, dependencies=[Depends(get_api_key)])
async def ingest_endpoint(file: UploadFile = File(...)):
    """Upload a CSV file to ingest device inventory."""
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files are allowed")
    
    # Save uploaded file temporarily
    temp_path = f"./data/temp_{file.filename}"
    with open(temp_path, "wb") as buffer:
        buffer.write(await file.read())
    
    try:
        result = ingest_csv(temp_path)
        return result
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

@app.post("/evaluate", response_model=EvaluateResponse, dependencies=[Depends(get_api_key)])
async def evaluate_endpoint():
    """Evaluate devices against policy and queue violations in the Outbox."""
    return evaluate_devices()

@app.post("/alert", response_model=AlertResponse, dependencies=[Depends(get_api_key)])
async def alert_endpoint():
    """Process the Outbox and send alerts to Discord."""
    return process_outbox()

@app.get("/health")
async def health_check():
    """Public endpoint to check if the service is running."""
    return {"status": "healthy"}