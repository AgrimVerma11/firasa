"""Health check endpoint.

Deployment platforms ping this to confirm the service is alive, so it stays
cheap: it just checks the model files are on disk rather than loading them.
"""

from flask import Blueprint, current_app, jsonify

from ml import config

health_bp = Blueprint("health", __name__)

_ARTIFACTS = [
    config.PREPROCESSOR_PATH,
    config.CLUSTERER_PATH,
    config.CLUSTER_SCALER_PATH,
    config.REGRESSOR_PATH,
    config.CLASSIFIER_PATH,
    config.CLASSIFIER_BINARY_PATH,
]


@health_bp.get("/health")
def health():
    """Report real readiness, not just liveness.

    Returns 200 only when the model files are on disk and the pipeline actually
    warmed at startup, so a deploy with a broken or missing artifact fails its
    health check instead of going live and returning 500s on every prediction.
    Deployment platforms and the keep-alive ping treat any non-200 as unhealthy.
    """
    files_present = all(path.exists() for path in _ARTIFACTS)
    models_ready = bool(current_app.config.get("MODELS_READY")) and files_present
    body = {
        "status": "healthy" if models_ready else "degraded",
        "models_loaded": models_ready,
        "datasets_trained_on": config.DATASETS_TRAINED_ON,
        "total_training_records": config.TOTAL_TRAINING_RECORDS,
        "api_version": config.API_VERSION,
    }
    return jsonify(body), 200 if models_ready else 503
