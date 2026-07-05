"""Explainability and the intervention engine (Layer 4).

SHAP explains the deployed binary High-Risk classifier. An earlier version
assumed a tree model and TreeExplainer, but logistic regression is what won, so
RiskExplainer uses shap.LinearExplainer, which is exact for a linear model. LIME
is run on the same model in the notebook as a second opinion. get_interventions
turns one student's SHAP values into a ranked, actionable set of steps via
INTERVENTION_MAP.
"""

import logging
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
import shap

from ml import config

logger = logging.getLogger(__name__)


# Keyed by the real DS1 feature names and the actual "bad" states a student can
# be in. A feature only produces an intervention when the student is currently
# in one of these states, so there is nothing to suggest for a good habit.
INTERVENTION_MAP: dict[str, dict] = {
    "procrastination_level": {
        "High": {
            "recommendation": "Break work into 25-minute focused blocks and start each "
                              "session with the single hardest task. Fix a daily start time.",
            "expected_impact": "high",
        },
        "Medium": {
            "recommendation": "Set personal deadlines 24 hours ahead of the real ones and "
                              "keep a short daily priority list.",
            "expected_impact": "medium",
        },
    },
    "sleep_hours": {
        "4–5 hours": {
            "recommendation": "Protect 7-8 hours of sleep. Set a consistent wake time and "
                              "remove screens 30 minutes before bed.",
            "expected_impact": "high",
        },
        "6–7 hours": {
            "recommendation": "Audit caffeine timing and keep the study space separate from "
                              "the sleep space to improve sleep quality.",
            "expected_impact": "medium",
        },
    },
    "career_goal_clarity": {
        "Not clear": {
            "recommendation": "Attend one domain talk or hackathon this month and speak to two "
                              "seniors working in an area you find interesting.",
            "expected_impact": "high",
        },
        "Somewhat clear": {
            "recommendation": "Narrow to two or three target roles and start one focused "
                              "certification to close the skills gap.",
            "expected_impact": "medium",
        },
    },
    "stress_level": {
        "High": {
            "recommendation": "Add 20 minutes of daily physical activity and speak to a "
                              "counsellor or trusted peer. Use short breathing resets before study.",
            "expected_impact": "high",
        },
        "Medium": {
            "recommendation": "Practise five-minute box breathing before study sessions and cap "
                              "social media to set time windows.",
            "expected_impact": "medium",
        },
    },
    "study_hours_daily": {
        "Less than 1 hour": {
            "recommendation": "Add one dedicated two-hour study block each day in a "
                              "distraction-free space.",
            "expected_impact": "high",
        },
    },
    "screen_time_non_study": {
        "More than 6 hours": {
            "recommendation": "Use an app blocker during study hours and keep the phone in "
                              "another room rather than on silent.",
            "expected_impact": "high",
        },
    },
    "events_participation": {
        "Never participate in such events": {
            "recommendation": "Register for one upcoming hackathon or department event this "
                              "term, focused on learning rather than winning.",
            "expected_impact": "medium",
        },
    },
    "projects_internships": {
        "Not currently, but intend to in the future": {
            "recommendation": "Apply to three internships or start one portfolio project this "
                              "month, targeting startups and labs alongside larger firms.",
            "expected_impact": "medium",
        },
    },
}


def _bucket_value(feature: str, value) -> Optional[str]:
    """Turn a student's raw value into an intervention bucket key.

    stress_level is numeric so it gets thresholded; everything else just matches
    its value against the map keys. Returns None when there is no intervention
    for the current value.
    """
    options = INTERVENTION_MAP[feature]
    if feature == "stress_level":
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            return None
        if numeric >= 3.5:
            return "High"
        if numeric >= 2.5:
            return "Medium"
        return None
    return value if value in options else None


def get_interventions(
    student_features: dict,
    shap_values_for_student: np.ndarray,
    feature_names: list[str],
    top_n: int = 3,
) -> list[dict]:
    """Rank a student's interventions by SHAP magnitude and return the top few.

    Takes the student's raw values, their SHAP vector, and the matching feature
    names. Only features that are both in an addressable bad state and pushing
    the student toward High Risk make the list. Each result carries the feature,
    its current value, the SHAP impact, the recommendation, its expected impact,
    and a priority.
    """
    shap_by_feature = dict(zip(feature_names, shap_values_for_student))

    scored = []
    for feature in INTERVENTION_MAP:
        if feature not in shap_by_feature:
            continue
        impact = float(shap_by_feature[feature])
        # Only recommend fixing features that push the student toward High Risk.
        # A negative SHAP means the feature is currently helping, so we leave it
        # alone rather than advise changing something that is already working.
        if impact <= 0:
            continue
        bucket = _bucket_value(feature, student_features.get(feature))
        entry = INTERVENTION_MAP[feature].get(bucket) if bucket else None
        if entry is None:
            continue
        scored.append((feature, student_features.get(feature), impact, entry))

    scored.sort(key=lambda item: item[2], reverse=True)

    interventions = []
    for priority, (feature, current_value, impact, entry) in enumerate(scored[:top_n], start=1):
        interventions.append(
            {
                "feature": feature,
                "current_value": current_value,
                "shap_impact": round(impact, 4),
                "recommendation": entry["recommendation"],
                "expected_impact": entry["expected_impact"],
                "priority": priority,
            }
        )
    return interventions


class RiskExplainer:
    """SHAP over the deployed binary (High Risk) logistic pipeline."""

    def __init__(self, model_pipeline, feature_names: list[str]) -> None:
        self.pipeline = model_pipeline
        self.scaler = model_pipeline.named_steps["scaler"]
        self.model = model_pipeline.named_steps["model"]
        self.feature_names = list(feature_names)
        self.explainer_ = None
        self.expected_value_: Optional[float] = None

    def fit(self, background_features: pd.DataFrame) -> "RiskExplainer":
        """Fit the linear explainer using the scaled training data as background."""
        scaled_background = self.scaler.transform(background_features)
        self.explainer_ = shap.LinearExplainer(self.model, scaled_background)
        self.expected_value_ = self.explainer_.expected_value
        return self

    def shap_values(self, features: pd.DataFrame) -> np.ndarray:
        """SHAP values for the positive class (n_samples x n_features)."""
        return self.explainer_.shap_values(self.scaler.transform(features))

    def scaled_frame(self, features: pd.DataFrame) -> pd.DataFrame:
        """Scaled features as a named dataframe, which the SHAP plots want."""
        return pd.DataFrame(
            self.scaler.transform(features), columns=self.feature_names, index=features.index
        )

    def mean_abs_shap(self, features: pd.DataFrame) -> pd.Series:
        """Global importance: mean absolute SHAP per feature, sorted high to low."""
        values = np.abs(self.shap_values(features)).mean(axis=0)
        return pd.Series(values, index=self.feature_names).sort_values(ascending=False)

    def plot_beeswarm(self, features: pd.DataFrame, save_path: Optional[Path] = None):
        import matplotlib.pyplot as plt

        shap.summary_plot(
            self.shap_values(features), self.scaled_frame(features),
            feature_names=self.feature_names, show=False, max_display=15,
        )
        fig = plt.gcf()
        fig.tight_layout()
        if save_path:
            fig.savefig(save_path, dpi=120, bbox_inches="tight")
        return fig

    def plot_bar(self, features: pd.DataFrame, save_path: Optional[Path] = None):
        import matplotlib.pyplot as plt

        shap.summary_plot(
            self.shap_values(features), self.scaled_frame(features),
            feature_names=self.feature_names, plot_type="bar", show=False, max_display=15,
        )
        fig = plt.gcf()
        fig.tight_layout()
        if save_path:
            fig.savefig(save_path, dpi=120, bbox_inches="tight")
        return fig

    def plot_dependence(self, feature: str, features: pd.DataFrame, interaction: Optional[str] = None,
                        save_path: Optional[Path] = None):
        import matplotlib.pyplot as plt

        shap.dependence_plot(
            feature, self.shap_values(features), self.scaled_frame(features),
            interaction_index=interaction, show=False,
        )
        fig = plt.gcf()
        fig.tight_layout()
        if save_path:
            fig.savefig(save_path, dpi=120, bbox_inches="tight")
        return fig

    def force_plot_html(self, features: pd.DataFrame, row_index: int, save_path: Path) -> None:
        """Save an interactive HTML force plot for one student."""
        scaled = self.scaled_frame(features)
        values = self.shap_values(features)
        plot = shap.force_plot(
            self.expected_value_, values[row_index], scaled.iloc[row_index],
            feature_names=self.feature_names,
        )
        shap.save_html(str(save_path), plot)

