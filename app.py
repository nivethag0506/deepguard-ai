from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import numpy as np
import tensorflow as tf
import os

app = FastAPI(title="DeepGuard Insurance Fraud API")

# Allow the frontend to communicate with the backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins (for local testing)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Define the expected JSON payload from the frontend
class ClaimData(BaseModel):
    claimant_age: int
    policy_age: int
    claim_amount: float
    past_claims: int
    severity: str
    police_report: int

# Attempt to load the trained model
MODEL_PATH = "fraud_model.keras"

try:
    if os.path.exists(MODEL_PATH):
        model = tf.keras.models.load_model(MODEL_PATH)
        print("Neural Network loaded successfully!")
    else:
        model = None
        print(f"Warning: {MODEL_PATH} not found. API will return mock predictions.")
except Exception as e:
    model = None
    print(f"Error loading model: {e}. Returning mock predictions.")

@app.post("/predict")
async def predict_fraud(claim: ClaimData):
    # 1. Fallback trigger if model is absent
    if model is None:
        # We can pass status='mock' so the frontend knows to gracefully drop into its mock logic!
        return {"risk_score": 0.0, "status": "mock", "message": "Model file missing."}

    # 2. Preprocess the incoming JSON feature exactly the way we trained on Colab!
    # Convert string severity to integer index.
    severity_map = {"Minor": 0, "Moderate": 1, "Major": 2, "Total Loss": 3}
    encoded_severity = severity_map.get(claim.severity, 1)

    # Convert to Numpy Array (You must adjust this size/order to match your exact Colab X_train columns!)
    # This is a sample array matching the 6 frontend input fields.
    input_features = np.array([[
        claim.claimant_age,
        claim.policy_age,
        claim.claim_amount,
        claim.past_claims,
        encoded_severity,
        claim.police_report
    ]])

    # 3. Model Inference Execution!
    try:
        prediction = model.predict(input_features)
        
        # Example: assuming output is shape (1, 1) with sigmoid activation giving a probability 0.0 - 1.0
        probability = float(prediction[0][0])
        score = round(probability * 100, 2)

        return {"risk_score": score, "status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
