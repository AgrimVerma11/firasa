"""Preprocessing pipeline for EduSense.

The primary behavioral dataset (DS1) is transformed by
:class:`BehavioralPreprocessor`, which engineers the ``procrastination_level``
proxy, imputes nulls, encodes ordinal and nominal categoricals, and scales the
continuous block. Every statistic (medians, scaler, encoder categories) is
learned on the training split only and serialised for inference.

Module-level helpers prepare the DS3 regression data and the DS2/DS4
cross-dataset validation sets used in Step 11.
"""

import logging
from pathlib import Path
from typing import Optional

import joblib
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from data.data_loader import load_dataset
from ml import config

logger = logging.getLogger(__name__)


def derive_procrastination_level(frame: pd.DataFrame) -> pd.Series:
    """Engineer the ordinal ``procrastination_level`` proxy.

    Sums the per-feature component scores defined in
    ``config.PROCRASTINATION_COMPONENT_SCORES`` and bins the total into
    Low / Medium / High using ``config.PROCRASTINATION_SCORE_BINS``.

    Args:
        frame: Dataframe containing the procrastination source columns.

    Returns:
        Categorical series of procrastination levels aligned to ``frame``.
    """
    score = pd.Series(0.0, index=frame.index)
    for column, mapping in config.PROCRASTINATION_COMPONENT_SCORES.items():
        score = score + frame[column].map(mapping).fillna(0)
    return pd.cut(
        score,
        bins=config.PROCRASTINATION_SCORE_BINS,
        labels=config.PROCRASTINATION_LEVELS,
    )


class BehavioralPreprocessor:
    """Fit/transform pipeline for the primary behavioral dataset (DS1).

    Produces a fully numeric, model-ready feature matrix: the continuous block
    (native numerics + ordinal-encoded features + the engineered procrastination
    level) is median-imputed and standard-scaled, and the nominal features are
    one-hot encoded. All learned state is fit on training data only.
    """

    def __init__(self) -> None:
        self.numeric_features = list(config.DS1_NUMERIC_FEATURES)
        self.ordinal_features = list(config.DS1_ORDINAL_FEATURES)
        self.nominal_features = list(config.DS1_NOMINAL_FEATURES)
        self.derived_features = list(config.DS1_DERIVED_FEATURES)
        # The continuous block: numerics, ordinal codes, and procrastination.
        self.continuous_features = (
            self.numeric_features + self.ordinal_features + self.derived_features
        )

        self.medians_: Optional[pd.Series] = None
        self.scaler_: Optional[StandardScaler] = None
        self.encoder_: Optional[OneHotEncoder] = None
        self.ohe_feature_names_: list[str] = []
        self.feature_names_: list[str] = []

    def _engineer(self, frame: pd.DataFrame) -> pd.DataFrame:
        """Derive procrastination and encode ordinals to integer codes.

        Args:
            frame: Raw DS1 dataframe.

        Returns:
            Copy with ordinal features replaced by their integer codes and the
            engineered procrastination code added. Nominal features are left as
            raw labels for one-hot encoding.
        """
        work = frame.copy()
        work[config.PROCRASTINATION_FEATURE] = derive_procrastination_level(work)

        for column, order in config.DS1_ORDINAL_FEATURES.items():
            code_map = {category: rank for rank, category in enumerate(order)}
            work[column] = work[column].map(code_map)

        proc_map = {level: rank for rank, level in enumerate(config.PROCRASTINATION_LEVELS)}
        work[config.PROCRASTINATION_FEATURE] = pd.to_numeric(
            work[config.PROCRASTINATION_FEATURE].astype(object).map(proc_map)
        )
        return work

    def fit(self, frame: pd.DataFrame) -> "BehavioralPreprocessor":
        """Learn imputation medians, scaler, and encoder from training data.

        Args:
            frame: Raw DS1 training split.

        Returns:
            The fitted preprocessor.
        """
        work = self._engineer(frame)

        self.medians_ = work[self.continuous_features].median()
        imputed = work[self.continuous_features].fillna(self.medians_)

        self.scaler_ = StandardScaler().fit(imputed)
        self.encoder_ = OneHotEncoder(handle_unknown="ignore", sparse_output=False)
        self.encoder_.fit(work[self.nominal_features])

        self.ohe_feature_names_ = list(
            self.encoder_.get_feature_names_out(self.nominal_features)
        )
        self.feature_names_ = self.continuous_features + self.ohe_feature_names_
        logger.info(
            "Fitted BehavioralPreprocessor: %d continuous + %d one-hot = %d features",
            len(self.continuous_features),
            len(self.ohe_feature_names_),
            len(self.feature_names_),
        )
        return self

    def _check_fitted(self) -> None:
        if self.scaler_ is None or self.encoder_ is None:
            raise RuntimeError("BehavioralPreprocessor must be fitted before use.")

    def transform(self, frame: pd.DataFrame) -> tuple[pd.DataFrame, Optional[pd.Series]]:
        """Transform raw DS1 rows into the model-ready feature matrix.

        Args:
            frame: Raw DS1 dataframe (train, test, or a single inference row).

        Returns:
            Tuple of the feature matrix and the encoded target series (or None
            if the target column is absent, as during inference).
        """
        self._check_fitted()
        work = self._engineer(frame)
        imputed = work[self.continuous_features].fillna(self.medians_)

        scaled = self.scaler_.transform(imputed)
        encoded = self.encoder_.transform(work[self.nominal_features])
        features = pd.DataFrame(
            np.hstack([scaled, encoded]),
            columns=self.feature_names_,
            index=frame.index,
        )

        target = None
        if config.DS1_TARGET in frame.columns:
            target = frame[config.DS1_TARGET].map(config.RISK_LABEL_MAP)
        return features, target

    def fit_transform(self, frame: pd.DataFrame) -> tuple[pd.DataFrame, Optional[pd.Series]]:
        """Fit on the data, then return its transformed feature matrix."""
        return self.fit(frame).transform(frame)

    def cluster_matrix(self, frame: pd.DataFrame) -> pd.DataFrame:
        """Return the imputed, unscaled clustering feature subset.

        The clustering layer applies its own scaler, so this exposes the
        engineered and median-imputed cluster features without standardisation.

        Args:
            frame: Raw DS1 dataframe.

        Returns:
            Dataframe of the configured cluster features, median-imputed.
        """
        self._check_fitted()
        work = self._engineer(frame)
        imputed = work[self.continuous_features].fillna(self.medians_)
        return imputed[config.DS1_CLUSTER_FEATURES].copy()

    def save(self, path: Path = config.PREPROCESSOR_PATH) -> None:
        """Serialise the fitted preprocessor to disk."""
        self._check_fitted()
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self, path)
        logger.info("Saved preprocessor -> %s", path)

    @classmethod
    def load(cls, path: Path = config.PREPROCESSOR_PATH) -> "BehavioralPreprocessor":
        """Load a fitted preprocessor from disk."""
        return joblib.load(path)


def prepare_primary_data(save: bool = True) -> dict:
    """Split DS1, fit the preprocessor on the train split, and transform both.

    Args:
        save: If True, persist the fitted preprocessor and processed CSVs.

    Returns:
        Dict with keys ``X_train``, ``X_test``, ``y_train``, ``y_test``, and
        ``preprocessor``.
    """
    raw = load_dataset("behavioral_analytics")
    train_raw, test_raw = train_test_split(
        raw,
        test_size=config.TEST_SIZE,
        random_state=config.RANDOM_SEED,
        stratify=raw[config.DS1_TARGET],
    )

    preprocessor = BehavioralPreprocessor().fit(train_raw)
    x_train, y_train = preprocessor.transform(train_raw)
    x_test, y_test = preprocessor.transform(test_raw)
    logger.info(
        "Primary data prepared: train=%d, test=%d, features=%d",
        len(x_train),
        len(x_test),
        x_train.shape[1],
    )

    if save:
        preprocessor.save()
        x_train.assign(**{config.DS1_TARGET: y_train.values}).to_csv(
            config.PRIMARY_TRAIN_PATH, index=False
        )
        x_test.assign(**{config.DS1_TARGET: y_test.values}).to_csv(
            config.PRIMARY_TEST_PATH, index=False
        )
        logger.info("Wrote %s and %s", config.PRIMARY_TRAIN_PATH.name, config.PRIMARY_TEST_PATH.name)

    return {
        "X_train": x_train,
        "X_test": x_test,
        "y_train": y_train,
        "y_test": y_test,
        "preprocessor": preprocessor,
    }


def prepare_regression_data(save: bool = True) -> dict:
    """Split DS3 into the regression train/test sets.

    Scaling is applied inside the regression model pipelines (Step 8), so the
    splits here are the raw numeric features and target.

    Args:
        save: If True, persist the processed CSVs.

    Returns:
        Dict with keys ``X_train``, ``X_test``, ``y_train``, ``y_test``.
    """
    raw = load_dataset("performance_prediction")
    features = raw[config.DS3_FEATURES]
    target = raw[config.DS3_TARGET]

    x_train, x_test, y_train, y_test = train_test_split(
        features,
        target,
        test_size=config.TEST_SIZE,
        random_state=config.RANDOM_SEED,
    )
    logger.info(
        "Regression data prepared from DS3: train=%d, test=%d, features=%d",
        len(x_train),
        len(x_test),
        x_train.shape[1],
    )

    if save:
        x_train.assign(**{config.DS3_TARGET: y_train.values}).to_csv(
            config.REGRESSION_TRAIN_PATH, index=False
        )
        x_test.assign(**{config.DS3_TARGET: y_test.values}).to_csv(
            config.REGRESSION_TEST_PATH, index=False
        )
        logger.info(
            "Wrote %s and %s",
            config.REGRESSION_TRAIN_PATH.name,
            config.REGRESSION_TEST_PATH.name,
        )

    return {"X_train": x_train, "X_test": x_test, "y_train": y_train, "y_test": y_test}


# Dataset key -> loader name, for the validation-set extraction.
_VALIDATION_SOURCES = {
    "ds2": "zenodo_merged",
    "ds4": "performance_factors",
}


def prepare_validation_set(dataset_key: str, save: bool = True) -> pd.DataFrame:
    """Extract a cross-dataset validation set in canonical feature space.

    Selects the columns that map to the shared canonical features for the given
    dataset, renames them to the canonical names, and appends the exam-score
    target as ``exam_score``. DS2 rows are de-duplicated first.

    Args:
        dataset_key: ``"ds2"`` (negative control) or ``"ds4"`` (holdout).
        save: If True, persist the extracted CSV.

    Returns:
        Dataframe of shared canonical features plus the ``exam_score`` target.
    """
    if dataset_key not in _VALIDATION_SOURCES:
        raise KeyError(f"Unsupported validation dataset '{dataset_key}'.")

    raw = load_dataset(_VALIDATION_SOURCES[dataset_key])
    if dataset_key == "ds2":
        before = len(raw)
        raw = raw.drop_duplicates().reset_index(drop=True)
        logger.info("DS2 de-duplicated: %d -> %d rows", before, len(raw))

    columns = {
        canonical: mapping[dataset_key]
        for canonical, mapping in config.CROSS_DATASET_FEATURE_MAP.items()
        if mapping[dataset_key] is not None
    }
    extracted = pd.DataFrame(
        {canonical: raw[column] for canonical, column in columns.items()}
    )
    extracted["exam_score"] = raw[config.CROSS_DATASET_REGRESSION_TARGETS[dataset_key]]
    logger.info(
        "Validation set %s prepared: %d rows, shared features %s",
        dataset_key,
        len(extracted),
        list(columns.keys()),
    )

    if save:
        path = config.VAL_DS2_PATH if dataset_key == "ds2" else config.VAL_DS4_PATH
        extracted.to_csv(path, index=False)
        logger.info("Wrote %s", path.name)

    return extracted


def main() -> None:
    """Run the full preprocessing pipeline and write all processed artifacts."""
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s"
    )
    prepare_primary_data(save=True)
    prepare_regression_data(save=True)
    prepare_validation_set("ds2", save=True)
    prepare_validation_set("ds4", save=True)
    logger.info("Preprocessing complete.")


if __name__ == "__main__":
    main()
