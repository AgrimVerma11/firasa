"""The full prediction pipeline.

StudentPredictor loads every saved artifact once and runs all four layers for a
single student: clustering, score regression, risk classification, and the
SHAP-based interventions. The result is two-audience: the raw technical fields
(risk level, probabilities) for the API and for us, plus a reflective,
non-diagnostic wrapper and softer display names for the student-facing app.

The student is described in DS1 terms while the regressor trains on DS3, so the
DS1 inputs are mapped into the DS3 feature space (an approximation, defined in
config).
"""

import logging
from typing import Optional

import joblib
import numpy as np
import pandas as pd

from ml import config
from ml.clustering import StudentProfileClusterer
from ml.explainability import RiskExplainer, get_interventions
from ml.preprocessing import BehavioralPreprocessor, derive_procrastination_level
from ml.regression import add_interaction_features

logger = logging.getLogger(__name__)


def build_regression_features(student_input: dict) -> pd.DataFrame:
    """Map DS1 behavioural inputs into the DS3 regression features.

    Each band or level becomes an approximate DS3-scale number; anything missing
    falls back to a dataset-typical default. Returns a one-row frame with the
    DS3 columns.
    """
    defaults = config.DS3_FEATURE_DEFAULTS
    row = {
        "study_hours": config.STUDY_HOURS_DAILY_TO_NUMERIC.get(
            student_input.get("study_hours_daily"), defaults["study_hours"]
        ),
        "attendance": config.ATTENDANCE_BAND_TO_NUMERIC.get(
            student_input.get("attendance_percentage"), defaults["attendance"]
        ),
        "sleep_hours": config.SLEEP_BAND_TO_NUMERIC.get(
            student_input.get("sleep_hours"), defaults["sleep_hours"]
        ),
        "internet_usage": config.SCREEN_BAND_TO_INTERNET.get(
            student_input.get("screen_time_non_study"), defaults["internet_usage"]
        ),
        "assignments_completed": config.ASSIGNMENTS_ORDINAL_TO_COUNT.get(
            student_input.get("assignments_on_time"), defaults["assignments_completed"]
        ),
        "previous_score": config.CGPA_BAND_TO_PREVIOUS_SCORE.get(
            student_input.get("cgpa_category"), defaults["previous_score"]
        ),
    }
    return pd.DataFrame([row])[config.DS3_FEATURES]


class StudentPredictor:
    """Loads the artifacts once and produces a full prediction for a student."""

    def __init__(self) -> None:
        self.preprocessor = BehavioralPreprocessor.load()
        self.clusterer = StudentProfileClusterer.load()
        self.regressor = joblib.load(config.REGRESSOR_PATH)
        self.classifier_multiclass = joblib.load(config.CLASSIFIER_PATH)
        self.classifier_binary = joblib.load(config.CLASSIFIER_BINARY_PATH)
        self.feature_names = list(self.preprocessor.feature_names_)

        # SHAP explainer over the binary High-Risk model, using the saved
        # training features as the background distribution.
        background = pd.read_csv(config.PRIMARY_TRAIN_PATH).drop(columns=[config.DS1_TARGET])
        background = background[self.feature_names]
        self.explainer = RiskExplainer(self.classifier_binary, self.feature_names).fit(background)
        logger.info("StudentPredictor ready: %d artifacts loaded.", 5)

    def _prepare_ds1_row(self, student_input: dict) -> pd.DataFrame:
        """Build one DS1 row with every column the preprocessor expects.

        Missing numeric/ordinal fields become NaN (imputed later); missing
        nominal fields get a placeholder the one-hot encoder ignores.
        """
        row: dict = {}
        for column in config.DS1_NUMERIC_FEATURES + list(config.DS1_ORDINAL_FEATURES):
            row[column] = student_input.get(column, np.nan)
        for column in config.DS1_NOMINAL_FEATURES:
            value = student_input.get(column, "Unknown")
            # Engineering/PG program labels are mapped to the nearest category the
            # model was trained on (see PROGRAM_STREAM_ALIASES).
            if column == "program_stream":
                value = config.PROGRAM_STREAM_ALIASES.get(value, value)
            row[column] = value
        return pd.DataFrame([row])

    def predict(self, student_input: dict) -> dict:
        """Run all four layers for one student and return the full result.

        Takes a DS1-style profile (what the form collects) and returns the
        cluster, the score, the risk level/probability/flag, the framing, the
        interventions, and the disclaimer.
        """
        ds1_row = self._prepare_ds1_row(student_input)
        features, _ = self.preprocessor.transform(ds1_row)

        # Layer 1: behavioural cluster.
        cluster_values = self.preprocessor.cluster_matrix(ds1_row).iloc[0].to_dict()
        cluster = self.clusterer.predict_cluster(cluster_values)
        cluster["display_name"] = config.CLUSTER_DISPLAY_NAMES.get(
            cluster["cluster_id"], cluster["cluster_name"]
        )

        # Layer 3: risk classification (multiclass level + binary High-Risk flag).
        multiclass_code = int(self.classifier_multiclass.predict(features)[0])
        risk_level = config.RISK_LABEL_INVERSE[multiclass_code]
        binary_probability = float(self.classifier_binary.predict_proba(features)[0][1])
        binary_label = int(self.classifier_binary.predict(features)[0])

        # Layer 2: academic-score regression (DS1 -> DS3 feature mapping).
        regression_features = add_interaction_features(build_regression_features(student_input))
        raw_score = float(self.regressor.predict(regression_features)[0])
        predicted_score = round(min(100.0, max(0.0, raw_score)), 1)

        # Layer 4: SHAP-driven interventions.
        shap_row = self.explainer.shap_values(features)[0]
        intervention_features = dict(student_input)
        intervention_features[config.PROCRASTINATION_FEATURE] = str(
            derive_procrastination_level(ds1_row).iloc[0]
        )
        interventions = get_interventions(
            intervention_features, shap_row, self.feature_names, top_n=3
        )

        framing = config.RISK_FRAMING.get(risk_level, {})
        return {
            "cluster": {
                "id": cluster["cluster_id"],
                "name": cluster["cluster_name"],
                "display_name": cluster["display_name"],
                "description": cluster["cluster_description"],
            },
            "predicted_score": predicted_score,
            "risk_level": risk_level,
            "risk_probability": round(binary_probability, 3),
            "risk_label": binary_label,
            "framing": {
                "headline": framing.get("headline", ""),
                "reflection": framing.get("reflection", ""),
                "score_note": config.SCORE_NOTE,
            },
            "top_interventions": interventions,
            "disclaimer": config.DISCLAIMER,
            "model_versions": config.MODEL_VERSIONS,
        }

    @staticmethod
    def _apply_modification(student_input: dict, feature: str, new_value) -> dict:
        """Apply a what-if change, translating derived features to real inputs.

        procrastination_level is engineered, so a change to it is applied to its
        source behaviours (study consistency, task punctuality) instead of set
        directly, where it would just be re-derived and ignored.
        """
        modified = dict(student_input)
        if feature == config.PROCRASTINATION_FEATURE:
            modified.update(config.PROCRASTINATION_LEVEL_TO_SOURCES.get(new_value, {}))
        else:
            modified[feature] = new_value
        return modified

    def what_if(self, student_input: dict, modifications: list[dict]) -> dict:
        """Re-score after one or more changes, returning the score and risk deltas.

        modifications is a list of {"feature", "new_value"} entries, applied
        together against the same baseline so a student can see the combined
        effect of several changes at once (not just the last one). Academic levers
        move the predicted score; behavioural ones move the risk probability, so
        both deltas are reported.
        """
        baseline = self.predict(student_input)
        modified_input = dict(student_input)
        for change in modifications:
            modified_input = self._apply_modification(
                modified_input, change["feature"], change["new_value"]
            )
        modified = self.predict(modified_input)
        return {
            "modifications": modifications,
            "original_score": baseline["predicted_score"],
            "new_score": modified["predicted_score"],
            "score_delta": round(modified["predicted_score"] - baseline["predicted_score"], 1),
            "original_risk_probability": baseline["risk_probability"],
            "new_risk_probability": modified["risk_probability"],
            "risk_probability_delta": round(
                modified["risk_probability"] - baseline["risk_probability"], 3
            ),
            "original_risk_level": baseline["risk_level"],
            "new_risk_level": modified["risk_level"],
        }


_PREDICTOR: Optional[StudentPredictor] = None


def get_predictor() -> StudentPredictor:
    """Return the cached predictor, loading the artifacts the first time."""
    global _PREDICTOR
    if _PREDICTOR is None:
        _PREDICTOR = StudentPredictor()
    return _PREDICTOR


def predict_student(student_input: dict) -> dict:
    """Full prediction for one student via the cached predictor."""
    return get_predictor().predict(student_input)


def what_if_student(student_input: dict, modifications: list[dict]) -> dict:
    """Re-score one student after one or more changes."""
    return get_predictor().what_if(student_input, modifications)


def main() -> None:
    """Smoke test: run the pipeline on one real DS1 row."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
    from data.data_loader import load_dataset

    sample = load_dataset("behavioral_analytics").iloc[0].to_dict()
    result = predict_student(sample)
    import json

    logger.info("\n%s", json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
