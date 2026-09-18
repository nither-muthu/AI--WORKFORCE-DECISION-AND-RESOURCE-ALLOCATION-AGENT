from typing import Optional
from fastapi import APIRouter, HTTPException
from backend.app.schemas.schemas import MLPredictRequest, MLPredictResponse, MLTrainRequest, MLBatchTestRequest
from ml.predict import predict_pair, predict_batch, get_model, set_model_cache
from ml.train_model import train_and_save_models

router = APIRouter(prefix="/api/ml", tags=["Machine Learning"])


@router.post("/predict", response_model=MLPredictResponse)
def predict_endpoint(req: MLPredictRequest):
    """
    Predict completion time and suitability score for an employee-task pair using Random Forest.
    """
    try:
        res = predict_pair(req.employee, req.task)
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ML Prediction failed: {str(e)}")


@router.post("/test-batch")
def test_batch_endpoint(req: MLBatchTestRequest):
    """
    Test and rank multiple employees against a user-provided task in real time.
    """
    try:
        results = predict_batch(req.employees, [req.task])
        # Sort by suitability score descending
        results.sort(key=lambda x: x["suitability_score"], reverse=True)
        return {
            "task": req.task,
            "total_candidates": len(req.employees),
            "rankings": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Batch test failed: {str(e)}")


@router.post("/train")
def train_model_endpoint(req: Optional[MLTrainRequest] = None):
    """
    Trigger training of the Random Forest model with user-provided parameters and custom records.
    """
    try:
        kwargs = {}
        if req:
            if req.num_samples is not None:
                kwargs["num_samples"] = req.num_samples
            if req.noise_level is not None:
                kwargs["noise_level"] = req.noise_level
            if req.skill_weight is not None:
                kwargs["skill_weight"] = req.skill_weight
            if req.workload_weight is not None:
                kwargs["workload_weight"] = req.workload_weight
            if req.experience_weight is not None:
                kwargs["experience_weight"] = req.experience_weight
            if req.custom_records:
                kwargs["custom_data"] = req.custom_records

        model_bundle = train_and_save_models(**kwargs)
        set_model_cache(model_bundle)
        importances = dict(zip(model_bundle["feature_cols"], model_bundle["rf_suitability"].feature_importances_))

        return {
            "status": "SUCCESS",
            "message": "Random Forest model successfully trained and loaded in real-time with user input.",
            "metrics": model_bundle.get("metrics", {}),
            "features": model_bundle.get("feature_cols", []),
            "feature_importances": importances,
            "user_config": model_bundle.get("user_config", {})
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Training failed: {str(e)}")


@router.get("/status")
def get_ml_status():
    """
    Retrieve model metadata, feature importances, and evaluation metrics.
    """
    try:
        model_bundle = get_model()
        metrics = model_bundle.get("metrics", {})
        feature_cols = model_bundle.get("feature_cols", [])
        importances = dict(zip(feature_cols, model_bundle["rf_suitability"].feature_importances_))
        return {
            "status": "LOADED",
            "model_type": "RandomForestRegressor (Dual Head: Time + Suitability)",
            "metrics": metrics,
            "features": feature_cols,
            "feature_importances": importances,
            "user_config": model_bundle.get("user_config", {})
        }
    except Exception as e:
        return {
            "status": "NOT_LOADED",
            "error": str(e)
        }
