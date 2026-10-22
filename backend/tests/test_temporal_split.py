"""Tests for Task 14: Model-A Temporal Splitting.

Verifies:
1. Primary split is non-random, purely temporal.
2. Embargo gap between train end and test start >= 30 days.
3. Test positive count >= 10 (Task 14 stopping condition).
4. No leakage/overlap across train, embargo, and test partitions.
5. Rolling origin folds preserve temporal causality and embargo constraints.
"""

from datetime import date
import pytest
import pandas as pd

from tools.training.dataset_builder import build_model_a_dataset
from tools.training.split import create_rolling_origin_splits, create_temporal_split


def test_task14_temporal_split_properties():
    df, report = build_model_a_dataset()
    df_train, df_test, split_res = create_temporal_split(df, test_weeks=7, min_embargo_days=30)

    # 1. Row counts add up
    assert split_res.train_rows == len(df_train)
    assert split_res.test_rows == len(df_test)
    assert split_res.train_rows + split_res.test_rows + split_res.embargo_rows == len(df)

    # 2. Strict chronological ordering (Train < Test)
    train_end = date.fromisoformat(split_res.train_date_range[1])
    test_start = date.fromisoformat(split_res.test_date_range[0])
    assert train_end < test_start

    # 3. Embargo gap >= 30 days
    assert split_res.embargo_days >= 30
    assert (test_start - train_end).days >= 30

    # 4. Zero date overlap
    train_dates = set(df_train["prediction_date"].unique())
    test_dates = set(df_test["prediction_date"].unique())
    assert len(train_dates.intersection(test_dates)) == 0

    # 5. Class balance check (Task 14: test positive count >= 10)
    assert split_res.train_positive_count > 0
    assert split_res.test_positive_count >= 10, f"Test positive count {split_res.test_positive_count} is too low!"
    assert split_res.test_positive_count == 295
    assert split_res.train_positive_count == 960


def test_task14_rolling_origin_folds():
    df, _ = build_model_a_dataset()
    df_train, _, _ = create_temporal_split(df, test_weeks=7, min_embargo_days=30)

    folds = create_rolling_origin_splits(df_train, n_splits=2, val_weeks=4, min_embargo_days=30)
    assert len(folds) >= 1

    for f_train, f_val in folds:
        f_train_end = date.fromisoformat(str(f_train["prediction_date"].max()))
        f_val_start = date.fromisoformat(str(f_val["prediction_date"].min()))
        assert f_train_end < f_val_start
        assert (f_val_start - f_train_end).days >= 30
