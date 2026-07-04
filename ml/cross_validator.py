"""Cross-dataset external validation (Step 11).

The score regressor is trained on DS3. This checks how well that relationship
carries over to two datasets it never saw: DS4 (the untouched holdout) and DS2
(the negative control with no real signal). The datasets share only a few
features and use different units, so transfer is measured with a shared-feature
model and per-dataset standardisation. These numbers are not the production
headline R2; they answer a different question, which is whether the pattern holds
on data collected somewhere else.
"""

import logging
from typing import Optional

import numpy as np
import pandas as pd
from sklearn.metrics import r2_score, root_mean_squared_error
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from xgboost import XGBRegressor

from data.data_loader import load_dataset
from ml import config

logger = logging.getLogger(__name__)

_TARGET_SOURCES = {"ds2": "zenodo_merged", "ds4": "performance_factors"}


class CrossDatasetValidator:
    """Trains a shared-feature regressor on DS3 and transfers it to DS2/DS4."""

    def __init__(self) -> None:
        self.source_key = config.REGRESSION_SOURCE  # "ds3"
        self.results_: dict[str, dict] = {}

    def _shared_features(self, target_key: str) -> list[str]:
        """Canonical features that both the source and the target have."""
        return [
            canonical
            for canonical, mapping in config.CROSS_DATASET_FEATURE_MAP.items()
            if mapping[self.source_key] is not None and mapping[target_key] is not None
        ]

    def _canonical_frame(self, frame: pd.DataFrame, dataset_key: str, shared: list[str]) -> pd.DataFrame:
        """Pick and rename a dataset's columns into canonical feature space."""
        columns = {config.CROSS_DATASET_FEATURE_MAP[c][dataset_key]: c for c in shared}
        return frame[list(columns)].rename(columns=columns)[shared]

    @staticmethod
    def _metrics(y_true, y_pred) -> dict:
        """Metrics on the standardised target.

        RMSE is in SD units, R2 is baseline-independent, and Pearson r is
        scale/offset invariant, so r is the transfer signal I trust most.
        """
        if np.std(y_pred) < 1e-9:
            correlation = 0.0
        else:
            correlation = float(np.corrcoef(y_true, y_pred)[0, 1])
        return {
            "rmse_sd": round(root_mean_squared_error(y_true, y_pred), 3),
            "r2": round(r2_score(y_true, y_pred), 3),
            "pearson_r": round(correlation, 3),
            "n": int(len(y_true)),
        }

    @staticmethod
    def _standardise(values: pd.Series, mean: float, std: float) -> np.ndarray:
        return ((values - mean) / std).to_numpy()

    def evaluate(self, target_key: str) -> dict:
        """Train on DS3's shared features and measure transfer to one dataset.

        target_key is 'ds2' (control) or 'ds4' (holdout). Returns the shared
        features, the DS3 source-test metrics, the transfer metrics, and the
        trained model.
        """
        shared = self._shared_features(target_key)

        source = load_dataset("performance_prediction")
        source_x = self._canonical_frame(source, self.source_key, shared)
        source_y = source[config.DS3_TARGET]
        x_train, x_test, y_train, y_test = train_test_split(
            source_x, source_y, test_size=config.TEST_SIZE, random_state=config.RANDOM_SEED
        )

        # Standardise features and target per dataset, so the metrics reflect
        # whether the relationship transfers rather than the difference in
        # exam-score baselines and units across independently collected datasets.
        source_scaler = StandardScaler().fit(x_train)
        source_mean, source_std = float(y_train.mean()), float(y_train.std())
        model = XGBRegressor(**config.XGB_REGRESSOR_PARAMS)
        model.fit(source_scaler.transform(x_train), self._standardise(y_train, source_mean, source_std))
        source_metrics = self._metrics(
            self._standardise(y_test, source_mean, source_std),
            model.predict(source_scaler.transform(x_test)),
        )

        target_frame = load_dataset(_TARGET_SOURCES[target_key])
        if target_key == "ds2":
            target_frame = target_frame.drop_duplicates().reset_index(drop=True)
        target_x = self._canonical_frame(target_frame, target_key, shared)
        target_y = target_frame[config.CROSS_DATASET_REGRESSION_TARGETS[target_key]]

        target_scaler = StandardScaler().fit(target_x)
        target_mean, target_std = float(target_y.mean()), float(target_y.std())
        target_actual = self._standardise(target_y, target_mean, target_std)
        target_predicted = model.predict(target_scaler.transform(target_x))
        target_metrics = self._metrics(target_actual, target_predicted)

        result = {
            "shared_features": shared,
            "source": source_metrics,
            "target": target_metrics,
            "target_actual_z": target_actual,
            "target_predicted": target_predicted,
            "model": model,
        }
        self.results_[target_key] = result
        logger.info(
            "%s transfer | shared=%s | source R2=%.3f r=%.3f | target R2=%.3f r=%.3f",
            target_key, shared, source_metrics["r2"], source_metrics["pearson_r"],
            target_metrics["r2"], target_metrics["pearson_r"],
        )
        return result

    def summary(self) -> pd.DataFrame:
        """Source-vs-transfer metrics for every dataset evaluated."""
        rows = []
        for target_key, result in self.results_.items():
            rows.append({
                "target": target_key,
                "role": "holdout" if target_key == config.REGRESSION_HOLDOUT else "control",
                "n_shared": len(result["shared_features"]),
                "source_r2": result["source"]["r2"],
                "source_r": result["source"]["pearson_r"],
                "target_r2": result["target"]["r2"],
                "target_r": result["target"]["pearson_r"],
                "target_rmse_sd": result["target"]["rmse_sd"],
            })
        return pd.DataFrame(rows).set_index("target")


def main() -> None:
    """Run the DS4 holdout and DS2 control transfers and print the summary."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
    validator = CrossDatasetValidator()
    validator.evaluate(config.REGRESSION_HOLDOUT)   # ds4
    validator.evaluate(config.REGRESSION_CONTROL)   # ds2
    logger.info("\n%s", validator.summary().to_string())


if __name__ == "__main__":
    main()
