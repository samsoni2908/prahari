"""
PRAHARI — Model-A Candidate Model (Task 17)
Canonical Reference: AGENTS.md §8, rules.md, docs/ml.md §6.4

Regularized Logistic Regression with balanced class weighting:
- C = 0.5 (locked regularization parameter)
- class_weight = 'balanced'
- max_iter = 1000
- random_state = 26186
- solver = 'lbfgs'
"""

from sklearn.linear_model import LogisticRegression


def build_hr_model(
    C: float = 0.5,
    class_weight: str = "balanced",
    max_iter: int = 1000,
    random_state: int = 26186,
    solver: str = "lbfgs",
) -> LogisticRegression:
    """Builds candidate regularized Logistic Regression model for Model-A."""
    return LogisticRegression(
        C=C,
        class_weight=class_weight,
        max_iter=max_iter,
        random_state=random_state,
        solver=solver,
    )


__all__ = ["build_hr_model"]
