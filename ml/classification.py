"""Academic risk classification (Layer 3).

AcademicRiskClassifier compares logistic regression, random forest, and XGBoost
in two framings: multiclass (Low / Moderate / High) and binary (High Risk vs the
rest). Low Risk is under the minority threshold, so SMOTE is tried on the
training split and metrics are reported before and after so its effect is
visible. It also draws the confusion matrix, ROC and precision-recall curves,
and (binary only) an F1-versus-threshold plot.
"""

import logging
from pathlib import Path
from typing import Optional

import joblib
import numpy as np
import pandas as pd
from imblearn.over_sampling import SMOTE
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler, label_binarize
from xgboost import XGBClassifier

from ml import config

logger = logging.getLogger(__name__)

HIGH_RISK_CODE = config.RISK_LABEL_MAP["High Risk"]


class AcademicRiskClassifier:
    """Risk classifier with multiclass and binary modes."""

    def __init__(self, mode: str = "multiclass") -> None:
        if mode not in {"multiclass", "binary"}:
            raise ValueError("mode must be 'multiclass' or 'binary'")
        self.mode = mode
        self.models_: dict[str, object] = {}
        self.metrics_before_: Optional[pd.DataFrame] = None
        self.metrics_after_: Optional[pd.DataFrame] = None
        self.metrics_: Optional[pd.DataFrame] = None
        self.best_name_: Optional[str] = None
        self.best_model_: Optional[object] = None
        self.smote_evaluated_: bool = False
        self.best_used_smote_: bool = False
        self.optimal_threshold_: Optional[float] = None

    # -- target / model helpers ---------------------------------------------
    def encode_target(self, y_multiclass: pd.Series) -> pd.Series:
        """Map the multiclass-coded target to the current mode."""
        if self.mode == "binary":
            return (y_multiclass == HIGH_RISK_CODE).astype(int)
        return y_multiclass

    @property
    def class_labels(self) -> list[str]:
        """Readable class labels for the current mode."""
        if self.mode == "binary":
            return ["Not High Risk", "High Risk"]
        return config.RISK_LEVELS

    def _candidate_models(self) -> dict[str, object]:
        return {
            "logistic_regression": Pipeline(
                [
                    ("scaler", StandardScaler()),
                    ("model", LogisticRegression(**config.LOGISTIC_REGRESSION_PARAMS)),
                ]
            ),
            "random_forest": RandomForestClassifier(**config.RF_CLASSIFIER_PARAMS),
            "xgboost": XGBClassifier(**config.XGB_CLASSIFIER_PARAMS),
        }

    def _fit_models(self, x_train, y_train) -> dict[str, object]:
        models = self._candidate_models()
        for model in models.values():
            model.fit(x_train, y_train)
        return models

    def _resample(self, x_train, y_train):
        """SMOTE the training split, keeping the column names."""
        resampled_x, resampled_y = SMOTE(random_state=config.RANDOM_SEED).fit_resample(
            x_train, y_train
        )
        return pd.DataFrame(resampled_x, columns=x_train.columns), resampled_y

    # -- metrics ------------------------------------------------------------
    def _evaluate(self, model, x_test, y_test) -> dict:
        predictions = model.predict(x_test)
        probabilities = model.predict_proba(x_test)
        if self.mode == "binary":
            roc_auc = roc_auc_score(y_test, probabilities[:, 1])
        else:
            roc_auc = roc_auc_score(y_test, probabilities, multi_class="ovr", average="macro")
        return {
            "accuracy": round(accuracy_score(y_test, predictions), 3),
            "f1_macro": round(f1_score(y_test, predictions, average="macro"), 3),
            "precision_macro": round(precision_score(y_test, predictions, average="macro", zero_division=0), 3),
            "recall_macro": round(recall_score(y_test, predictions, average="macro"), 3),
            "roc_auc": round(roc_auc, 3),
        }

    def _evaluate_all(self, models, x_test, y_test) -> pd.DataFrame:
        rows = {name: self._evaluate(model, x_test, y_test) for name, model in models.items()}
        return pd.DataFrame(rows).T

    def fit(self, x_train, y_train_multiclass, x_test, y_test_multiclass) -> "AcademicRiskClassifier":
        """Fit and evaluate every model, before and after SMOTE.

        Targets arrive multiclass-coded and are converted to the active mode
        here. Whichever variant scores higher on macro F1 (resampled or not) is
        kept, since SMOTE does not always help.
        """
        y_train = self.encode_target(y_train_multiclass)
        y_test = self.encode_target(y_test_multiclass)

        distribution = pd.Series(y_train).value_counts(normalize=True)
        self.smote_evaluated_ = distribution.min() < config.MINORITY_CLASS_THRESHOLD
        logger.info(
            "[%s] class balance: %s | minority below threshold: %s",
            self.mode,
            distribution.round(3).to_dict(),
            self.smote_evaluated_,
        )

        base_models = self._fit_models(x_train, y_train)
        self.metrics_before_ = self._evaluate_all(base_models, x_test, y_test)

        if self.smote_evaluated_:
            resampled_x, resampled_y = self._resample(x_train, y_train)
            smote_models = self._fit_models(resampled_x, resampled_y)
            self.metrics_after_ = self._evaluate_all(smote_models, x_test, y_test)
        else:
            smote_models = base_models
            self.metrics_after_ = self.metrics_before_

        # Pick the best (model, resampling) combination by macro F1 rather than
        # assuming SMOTE always helps. It doesn't when the label is already
        # near-separable, so keep whichever variant scores higher.
        before_name = self.metrics_before_["f1_macro"].idxmax()
        after_name = self.metrics_after_["f1_macro"].idxmax()
        before_best = self.metrics_before_.loc[before_name, "f1_macro"]
        after_best = self.metrics_after_.loc[after_name, "f1_macro"]

        if self.smote_evaluated_ and after_best > before_best:
            self.models_, self.metrics_ = smote_models, self.metrics_after_
            self.best_name_, self.best_used_smote_ = after_name, True
        else:
            self.models_, self.metrics_ = base_models, self.metrics_before_
            self.best_name_, self.best_used_smote_ = before_name, False

        self.best_model_ = self.models_[self.best_name_]
        if self.mode == "binary":
            self.optimal_threshold_ = self._optimal_threshold(x_test, y_test)
        logger.info(
            "[%s] best model: %s (SMOTE used: %s)",
            self.mode, self.best_name_, self.best_used_smote_,
        )
        return self

    def _optimal_threshold(self, x_test, y_test) -> float:
        """The positive-class probability threshold that maximises F1."""
        proba = self.best_model_.predict_proba(x_test)[:, 1]
        thresholds = np.linspace(0.1, 0.9, 81)
        f1_scores = [f1_score(y_test, (proba >= t).astype(int)) for t in thresholds]
        return round(float(thresholds[int(np.argmax(f1_scores))]), 3)

    def classification_report_text(self, x_test, y_test_multiclass) -> str:
        """Text classification report for the best model."""
        y_test = self.encode_target(y_test_multiclass)
        return classification_report(
            y_test, self.best_model_.predict(x_test), target_names=self.class_labels, zero_division=0
        )

    # -- plots --------------------------------------------------------------
    def plot_confusion_matrix(self, x_test, y_test_multiclass, save_path: Optional[Path] = None):
        import matplotlib.pyplot as plt
        import seaborn as sns

        y_test = self.encode_target(y_test_multiclass)
        matrix = confusion_matrix(y_test, self.best_model_.predict(x_test))
        fig, ax = plt.subplots(figsize=(5.5, 4.5))
        sns.heatmap(
            matrix, annot=True, fmt="d", cmap="Purples",
            xticklabels=self.class_labels, yticklabels=self.class_labels, ax=ax,
        )
        ax.set_xlabel("Predicted")
        ax.set_ylabel("Actual")
        ax.set_title(f"Confusion matrix ({self.mode}, {self.best_name_})")
        fig.tight_layout()
        if save_path:
            fig.savefig(save_path, dpi=120, bbox_inches="tight")
        return fig

    def plot_roc_curves(self, x_test, y_test_multiclass, save_path: Optional[Path] = None):
        """ROC for each model on one axis (macro one-vs-rest when multiclass)."""
        import matplotlib.pyplot as plt

        y_test = self.encode_target(y_test_multiclass)
        fig, ax = plt.subplots(figsize=(7, 6))
        for name, model in self.models_.items():
            proba = model.predict_proba(x_test)
            if self.mode == "binary":
                fpr, tpr, _ = roc_curve(y_test, proba[:, 1])
                area = roc_auc_score(y_test, proba[:, 1])
            else:
                fpr, tpr, area = self._macro_roc(y_test, proba)
            ax.plot(fpr, tpr, label=f"{name} (AUC {area:.3f})")
        ax.plot([0, 1], [0, 1], color="grey", linestyle="--")
        ax.set_xlabel("False positive rate")
        ax.set_ylabel("True positive rate")
        ax.set_title(f"ROC curves ({self.mode})")
        ax.legend()
        fig.tight_layout()
        if save_path:
            fig.savefig(save_path, dpi=120, bbox_inches="tight")
        return fig

    @staticmethod
    def _macro_roc(y_test, proba):
        """Macro-averaged one-vs-rest ROC across the classes."""
        classes = sorted(pd.Series(y_test).unique())
        binarized = label_binarize(y_test, classes=classes)
        grid = np.linspace(0, 1, 200)
        mean_tpr = np.zeros_like(grid)
        for index in range(len(classes)):
            fpr, tpr, _ = roc_curve(binarized[:, index], proba[:, index])
            mean_tpr += np.interp(grid, fpr, tpr)
        mean_tpr /= len(classes)
        return grid, mean_tpr, roc_auc_score(y_test, proba, multi_class="ovr", average="macro")

    def plot_precision_recall(self, x_test, y_test_multiclass, save_path: Optional[Path] = None):
        """Precision-recall curve for the High Risk class."""
        import matplotlib.pyplot as plt

        y_test = self.encode_target(y_test_multiclass)
        positive = y_test if self.mode == "binary" else (y_test == HIGH_RISK_CODE).astype(int)
        if self.mode == "binary":
            scores = self.best_model_.predict_proba(x_test)[:, 1]
        else:
            scores = self.best_model_.predict_proba(x_test)[:, HIGH_RISK_CODE]
        precision, recall, _ = precision_recall_curve(positive, scores)
        fig, ax = plt.subplots(figsize=(7, 5))
        ax.plot(recall, precision, color=config.BRAND_PRIMARY)
        ax.set_xlabel("Recall")
        ax.set_ylabel("Precision")
        ax.set_title(f"Precision-recall for High Risk ({self.mode}, {self.best_name_})")
        fig.tight_layout()
        if save_path:
            fig.savefig(save_path, dpi=120, bbox_inches="tight")
        return fig

    def plot_threshold_tuning(self, x_test, y_test_multiclass, save_path: Optional[Path] = None):
        """F1 against the decision threshold (binary only)."""
        if self.mode != "binary":
            raise RuntimeError("Threshold tuning is only defined for binary mode.")
        import matplotlib.pyplot as plt

        y_test = self.encode_target(y_test_multiclass)
        proba = self.best_model_.predict_proba(x_test)[:, 1]
        thresholds = np.linspace(0.1, 0.9, 81)
        f1_scores = [f1_score(y_test, (proba >= t).astype(int)) for t in thresholds]
        fig, ax = plt.subplots(figsize=(7, 4.5))
        ax.plot(thresholds, f1_scores, color=config.BRAND_PRIMARY)
        ax.axvline(self.optimal_threshold_, color=config.RISK_PALETTE["High Risk"], linestyle="--",
                   label=f"optimal = {self.optimal_threshold_}")
        ax.set_xlabel("Decision threshold")
        ax.set_ylabel("F1 (High Risk)")
        ax.set_title("F1 versus threshold")
        ax.legend()
        fig.tight_layout()
        if save_path:
            fig.savefig(save_path, dpi=120, bbox_inches="tight")
        return fig

    # -- persistence --------------------------------------------------------
    def save(self, path: Optional[Path] = None) -> None:
        """Save the best model (multiclass or binary path, by mode)."""
        if self.best_model_ is None:
            raise RuntimeError("Nothing to save; fit the classifier first.")
        path = path or (config.CLASSIFIER_PATH if self.mode == "multiclass" else config.CLASSIFIER_BINARY_PATH)
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self.best_model_, path)
        logger.info("Saved %s classifier (%s) -> %s", self.mode, self.best_name_, path)

    @classmethod
    def load(cls, path: Path):
        """Load a saved classifier."""
        return joblib.load(path)


def main() -> None:
    """Train both modes on DS1 and save the best model of each."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
    from ml.preprocessing import prepare_primary_data

    data = prepare_primary_data(save=False)
    for mode in ("multiclass", "binary"):
        classifier = AcademicRiskClassifier(mode=mode).fit(
            data["X_train"], data["y_train"], data["X_test"], data["y_test"]
        )
        logger.info("[%s] before SMOTE:\n%s", mode, classifier.metrics_before_.to_string())
        logger.info("[%s] after SMOTE:\n%s", mode, classifier.metrics_after_.to_string())
        classifier.save()


if __name__ == "__main__":
    main()
