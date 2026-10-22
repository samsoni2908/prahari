"""
PRAHARI — Model-A Temporal Split Engine (Task 14)
Canonical Reference: AGENTS.md §8, rules.md, docs/ml.md §6.2

Temporal Splitting Contract:
1. Primary train/test split MUST NOT be random.
2. Temporal ordering: Train strictly precedes Test.
3. Strict Embargo Gap >= 30 days between train cutoff and test start to eliminate
   horizon overlap (since prediction horizon is 30 days).
4. Test window remains untouched until final evaluation.
5. Rolling-origin cross-validation within training window.
"""

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any, Dict, Generator, List, Optional, Tuple
import pandas as pd


@dataclass(frozen=True)
class TemporalSplitResult:
    """Structured report and data container for temporal splitting."""

    train_rows: int
    test_rows: int
    embargo_rows: int
    train_date_range: Tuple[str, str]
    test_date_range: Tuple[str, str]
    embargo_days: int
    train_positive_count: int
    train_negative_count: int
    train_positive_rate: float
    test_positive_count: int
    test_negative_count: int
    test_positive_rate: float


def create_temporal_split(
    df: pd.DataFrame,
    date_col: str = "prediction_date",
    test_weeks: int = 7,
    min_embargo_days: int = 30,
) -> Tuple[pd.DataFrame, pd.DataFrame, TemporalSplitResult]:
    """Creates a strict chronological train/test split with >= 30d embargo gap.

    Args:
        df: Input DataFrame containing prediction_date and target_leave_anomaly.
        date_col: Column name representing observation timestamp T.
        test_weeks: Number of trailing weeks to hold out for final test set.
        min_embargo_days: Minimum days between train end and test start.

    Returns:
        (df_train, df_test, split_result_metadata)
    """
    sorted_dates = sorted(df[date_col].unique())
    if len(sorted_dates) < test_weeks + 2:
        raise ValueError(f"Insufficient distinct dates ({len(sorted_dates)}) for temporal split.")

    # 1. Define Test Window (chronological tail)
    test_dates = sorted_dates[-test_weeks:]
    test_start = test_dates[0]
    test_start_d = date.fromisoformat(test_start) if isinstance(test_start, str) else test_start

    # 2. Determine Train End with Embargo Constraint: test_start - min_embargo_days
    cutoff_limit = test_start_d - timedelta(days=min_embargo_days)
    train_dates = [
        d for d in sorted_dates
        if (date.fromisoformat(d) if isinstance(d, str) else d) <= cutoff_limit
    ]

    if not train_dates:
        raise ValueError(f"No training dates remain after applying {min_embargo_days}d embargo.")

    train_end = train_dates[-1]
    train_end_d = date.fromisoformat(train_end) if isinstance(train_end, str) else train_end

    # Exact embargo days
    embargo_days = (test_start_d - train_end_d).days
    embargo_dates = [d for d in sorted_dates if d > train_end and d < test_start]

    # 3. Create Partition DataFrames
    df_train = df[df[date_col].isin(train_dates)].copy()
    df_test = df[df[date_col].isin(test_dates)].copy()
    df_embargo = df[df[date_col].isin(embargo_dates)].copy()

    # 4. Compute Metrics
    train_pos = int((df_train["target_leave_anomaly"] == 1).sum())
    train_neg = int((df_train["target_leave_anomaly"] == 0).sum())
    train_rate = round(train_pos / len(df_train), 4) if len(df_train) > 0 else 0.0

    test_pos = int((df_test["target_leave_anomaly"] == 1).sum())
    test_neg = int((df_test["target_leave_anomaly"] == 0).sum())
    test_rate = round(test_pos / len(df_test), 4) if len(df_test) > 0 else 0.0

    result = TemporalSplitResult(
        train_rows=len(df_train),
        test_rows=len(df_test),
        embargo_rows=len(df_embargo),
        train_date_range=(str(train_dates[0]), str(train_end)),
        test_date_range=(str(test_start), str(test_dates[-1])),
        embargo_days=embargo_days,
        train_positive_count=train_pos,
        train_negative_count=train_neg,
        train_positive_rate=train_rate,
        test_positive_count=test_pos,
        test_negative_count=test_neg,
        test_positive_rate=test_rate,
    )

    return df_train, df_test, result


def create_rolling_origin_splits(
    df_train: pd.DataFrame,
    date_col: str = "prediction_date",
    n_splits: int = 3,
    val_weeks: int = 4,
    min_embargo_days: int = 30,
) -> List[Tuple[pd.DataFrame, pd.DataFrame]]:
    """Generates rolling-origin train/validation folds within the training window.

    Each fold respects the minimum 30-day embargo gap between fold train and fold val.
    """
    sorted_dates = sorted(df_train[date_col].unique())
    folds: List[Tuple[pd.DataFrame, pd.DataFrame]] = []

    # Iterate backwards from train tail to form validation blocks
    for i in range(n_splits):
        end_idx = len(sorted_dates) - (i * val_weeks)
        start_val_idx = end_idx - val_weeks
        if start_val_idx <= 4:
            break

        val_dates = sorted_dates[start_val_idx:end_idx]
        val_start_d = date.fromisoformat(val_dates[0]) if isinstance(val_dates[0], str) else val_dates[0]

        fold_train_dates = [
            d for d in sorted_dates[:start_val_idx]
            if (val_start_d - (date.fromisoformat(d) if isinstance(d, str) else d)).days >= min_embargo_days
        ]
        if not fold_train_dates:
            continue

        f_train = df_train[df_train[date_col].isin(fold_train_dates)].copy()
        f_val = df_train[df_train[date_col].isin(val_dates)].copy()
        folds.append((f_train, f_val))

    return folds


__all__ = ["TemporalSplitResult", "create_temporal_split", "create_rolling_origin_splits"]
