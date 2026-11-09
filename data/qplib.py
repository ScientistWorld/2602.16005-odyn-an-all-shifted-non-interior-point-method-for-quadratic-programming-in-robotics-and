"""Maros-Meszaros QP loader and small paper benchmark instances (development helper).

The evaluators in ``eval/`` do not import this module: they load and check the
benchmark files with their own code and hand solvers instance files in the
format described in ``data/qp_format.py``.

The loader converts the qpbenchmark MAT format into the standard form used by
the paper:

    minimize 0.5 x^T Q x + c^T x
    subject to A x = b, G x <= h.

It is intentionally method-agnostic so evaluation and baselines can consume
the same problems without importing anything from ``method/``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import scipy.sparse as spa

INF_MARKER = 9e19


def _as_csc(matrix: Any) -> spa.csc_matrix:
    if matrix is None:
        return spa.csc_matrix((0, 0))
    if spa.issparse(matrix):
        return matrix.astype(float).tocsc()
    return spa.csc_matrix(np.asarray(matrix, dtype=float))


def _clean_bounds(values: np.ndarray) -> np.ndarray:
    out = np.asarray(values, dtype=float).copy()
    out[out >= INF_MARKER] = np.inf
    out[out <= -INF_MARKER] = -np.inf
    return out


def _append_bound_rows(
    rows: list[spa.csc_matrix],
    rhs: list[np.ndarray],
    matrix: spa.csc_matrix,
    lower: np.ndarray,
    upper: np.ndarray,
) -> None:
    finite_lower = np.isfinite(lower)
    finite_upper = np.isfinite(upper)
    equal = finite_lower & finite_upper & (np.abs(upper - lower) <= 1e-10)

    upper_only = finite_upper & ~equal
    lower_only = finite_lower & ~equal

    # Fixed variables (equal bounds) are kept as a pair of opposite
    # inequalities, so they are never silently dropped.
    if np.any(equal):
        rows.append(matrix[equal])
        rhs.append(upper[equal])
        rows.append(-matrix[equal])
        rhs.append(-lower[equal])
    if np.any(upper_only):
        rows.append(matrix[upper_only])
        rhs.append(upper[upper_only])
    if np.any(lower_only):
        rows.append(-matrix[lower_only])
        rhs.append(-lower[lower_only])


def load_maros_meszaros_problem(mat_path: str | Path) -> dict[str, Any]:
    """Load one Maros-Meszaros MAT file into ``Q, c, A, b, G, h`` form."""
    import scipy.io

    mat_path = Path(mat_path)
    mat = scipy.io.loadmat(mat_path)

    Q = _as_csc(mat["P"])
    c = np.asarray(mat["q"], dtype=float).reshape(-1)
    C_all = _as_csc(mat["A"])
    lower = _clean_bounds(np.asarray(mat["l"], dtype=float).reshape(-1))
    upper = _clean_bounds(np.asarray(mat["u"], dtype=float).reshape(-1))
    n = int(np.asarray(mat["n"]).reshape(-1)[0])

    # qpbenchmark stores general constraints followed by explicit variable
    # bounds. The variable bounds are real constraints for ODYN and baselines.
    row_lower = lower[:-n]
    row_upper = upper[:-n]
    var_lower = lower[-n:]
    var_upper = upper[-n:]
    C = C_all[: len(row_lower)] if len(row_lower) else spa.csc_matrix((0, n))

    finite_lower = np.isfinite(row_lower)
    finite_upper = np.isfinite(row_upper)
    eq_mask = finite_lower & finite_upper & (np.abs(row_upper - row_lower) <= 1e-10)

    A = C[eq_mask] if np.any(eq_mask) else None
    b = row_upper[eq_mask] if np.any(eq_mask) else None

    G_rows: list[spa.csc_matrix] = []
    h_vals: list[np.ndarray] = []
    if C.shape[0] > 0:
        _append_bound_rows(G_rows, h_vals, C[~eq_mask], row_lower[~eq_mask], row_upper[~eq_mask])

    eye = spa.eye(n, format="csc")
    _append_bound_rows(G_rows, h_vals, eye, var_lower, var_upper)

    if G_rows:
        G = spa.vstack(G_rows, format="csc")
        h = np.concatenate(h_vals).astype(float)
    else:
        G = None
        h = None

    return {
        "name": mat_path.stem,
        "Q": Q,
        "P": Q,
        "c": c,
        "q": c,
        "A": A,
        "b": b,
        "G": G,
        "h": h,
        "lb": var_lower,
        "ub": var_upper,
        "source": str(mat_path),
    }


def estimated_dense_size_gb(problem: dict[str, Any]) -> float:
    """Estimate memory needed to materialize Q, A, and G as dense arrays."""
    total = 0
    for key in ("Q", "A", "G"):
        matrix = problem.get(key)
        if matrix is None:
            continue
        total += int(matrix.shape[0]) * int(matrix.shape[1]) * 8
    return total / 1e9


def degenerate_cases() -> dict[str, dict[str, Any]]:
    """Three small degenerate QPs used in the paper's Table IV."""
    cases: dict[str, dict[str, Any]] = {}

    cases["redundant_ineq"] = {
        "name": "redundant_ineq",
        "Q": np.eye(2),
        "P": np.eye(2),
        "c": np.zeros(2),
        "q": np.zeros(2),
        "A": None,
        "b": None,
        # x1 >= 1 plus looser redundant x1 >= 0.
        "G": np.array([[-1.0, 0.0], [-1.0, 0.0]]),
        "h": np.array([-1.0, 0.0]),
    }

    cases["licq_failure"] = {
        "name": "licq_failure",
        "Q": np.array([[1e-10, 1e-12], [1e-12, 1e-6]]),
        "P": np.array([[1e-10, 1e-12], [1e-12, 1e-6]]),
        "c": np.array([1e-4, -1.0]),
        "q": np.array([1e-4, -1.0]),
        "A": np.array([[1.0, 0.0]]),
        "b": np.array([0.0]),
        # OCR in the markdown makes this case ambiguous. This bounded version
        # matches the text claim that the optimum has x = [0, 0].
        "G": np.array([[-1.0, 0.0], [0.0, 1.0]]),
        "h": np.array([0.0, 0.0]),
    }

    cases["multiple_solutions"] = {
        "name": "multiple_solutions",
        "Q": np.array([[1.0, 0.0], [0.0, 0.0]]),
        "P": np.array([[1.0, 0.0], [0.0, 0.0]]),
        "c": np.array([1.0, 0.0]),
        "q": np.array([1.0, 0.0]),
        "A": None,
        "b": None,
        # Redundant zero row plus bounds. x2 remains non-unique.
        "G": np.array([[0.0, 0.0], [-1.0, 0.0], [1.0, 0.0], [0.0, -1.0], [0.0, 1.0]]),
        "h": np.array([0.0, 1.0, 3.0, 0.0, 3.0]),
    }

    return cases

