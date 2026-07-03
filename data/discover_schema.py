import pandas as pd
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

RAW_DIR = Path("data/raw")

files = {
    "behavioral_analytics":   RAW_DIR / "behavioral_analytics.csv",
    "zenodo_merged":          RAW_DIR / "zenodo_merged.csv",
    "performance_prediction": RAW_DIR / "performance_prediction.csv",
    "performance_factors":    RAW_DIR / "performance_factors.csv",
}

for name, path in files.items():
    df = pd.read_csv(path)
    logger.info("\n" + "="*60)
    logger.info(f"DATASET: {name}")
    logger.info(f"Rows: {len(df):,} | Columns: {len(df.columns)}")
    logger.info(f"\nColumns:\n{list(df.columns)}")
    logger.info(f"\nDtypes:\n{df.dtypes.to_string()}")
    logger.info(f"\nNull counts:\n{df.isnull().sum().to_string()}")
    logger.info(f"\nSample row:\n{df.iloc[0].to_dict()}")
    logger.info(f"\nValue counts for object columns:")
    for col in df.select_dtypes(include='object').columns:
        logger.info(f"  {col}: {df[col].nunique()} unique → {list(df[col].unique()[:5])}")
