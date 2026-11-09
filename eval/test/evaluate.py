#!/usr/bin/env python3
"""Test-slice evaluator for the convex-QP robustness benchmark.

The evaluator owns every part of the measurement:

* the problem instances (Maros-Meszaros files checked against pinned SHA-256
  hashes, small evaluator-side perturbations, and a generated family of
  degenerate QPs),
* the requested tolerances and the per-instance CPU budget,
* the comparison baseline (OSQP, run from ``eval/test/osqp_solver.py``),
* the success test: an instance counts as solved only when the evaluator's own
  residual computation on the returned primal-dual point passes the tolerance.

Status strings, iteration counts or residuals written by a solver are never
used for scoring. Missing, malformed, non-finite, crashed, or over-budget runs
are failures, and every instance in the fixed manifest is in the denominator.

Every solver registered as ``scripts/solvers/<name>.sh`` is run through the
command-line contract documented in ``briefing/evaluation.md``; the method name
is the file stem. Running with no arguments scores every registered solver plus
the baseline and writes ``scoring/scores_test.json``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import scipy.io
import scipy.sparse as spa

SLICE = "test"
PROTOCOL = "qp-verified-kkt-v1"
EVAL_DIR = Path(__file__).resolve().parent
WORKSPACE = EVAL_DIR.parents[1]
MANIFEST_PATH = EVAL_DIR / "manifest.json"
DATA_DIR = WORKSPACE / "data" / "maros_meszaros_qpbenchmark" / "data"
SOLVER_DIR = WORKSPACE / "scripts" / "solvers"
DEFAULT_OUTPUT = WORKSPACE / "scoring" / f"scores_{SLICE}.json"
OUTCOME_DIR = WORKSPACE / "tmp" / "eval_runs" / SLICE

TOLERANCES = (("medium", 1e-6), ("high", 1e-9))
CPU_LIMIT_S = 120
WALL_LIMIT_S = 10 * CPU_LIMIT_S  # backstop for hung processes only; CPU time is the budget
# Operational guard keeping the evaluation light: once a solver has used this
# much CPU time in one evaluation, its remaining instances count as failures.
TOTAL_CPU_BUDGET_S = 7200
BASELINE_NAME = "osqp"
BASELINE_MODULE = f"eval.{SLICE}.osqp_solver"
CACHE_ENV = "QP_GYM_EVAL_CACHE"
WORKERS_ENV = "QP_GYM_WORKERS"
INF_MARKER = 9e19
FORMAT_TAG = "qp-npz-1"
NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")

# family -> (experiment name, metric template)
FAMILY_EXPERIMENTS = {
    "maros_meszaros": ("failure_rate_comparison", "failure_rate_{tol}"),
    "degenerate": ("degenerate_problems", "degenerate_failure_rate_{tol}"),
}


# --------------------------------------------------------------------------- #
# Problem construction
# --------------------------------------------------------------------------- #


@dataclass
class Instance:
    instance_id: str
    family: str
    base: str
    draw: int
    Q: spa.csc_matrix
    c: np.ndarray
    A: spa.csc_matrix
    b: np.ndarray
    G: spa.csc_matrix
    h: np.ndarray
    arrays: dict[str, np.ndarray] = field(default_factory=dict)
    content_hash: str = ""
    path: Path | None = None

    @property
    def n(self) -> int:
        return int(self.c.shape[0])

    @property
    def m(self) -> int:
        return int(self.b.shape[0])

    @property
    def p(self) -> int:
        return int(self.h.shape[0])


def _csc(matrix: Any, rows: int, cols: int) -> spa.csc_matrix:
    if matrix is None:
        return spa.csc_matrix((rows, cols))
    out = spa.csc_matrix(matrix, dtype=float)
    out.sum_duplicates()
    out.sort_indices()
    return out


def _clean_bounds(values: Any) -> np.ndarray:
    out = np.asarray(values, dtype=float).reshape(-1).copy()
    out[out >= INF_MARKER] = np.inf
    out[out <= -INF_MARKER] = -np.inf
    return out


def _split_rows(matrix: spa.csr_matrix, lower: np.ndarray, upper: np.ndarray,
                eq_rows: list, eq_rhs: list, in_rows: list, in_rhs: list) -> None:
    """Convert ``lower <= matrix x <= upper`` into ``A x = b`` and ``G x <= h`` rows."""
    if matrix.shape[0] == 0:
        return
    finite_lower = np.isfinite(lower)
    finite_upper = np.isfinite(upper)
    equal = finite_lower & finite_upper & (np.abs(upper - lower) <= 1e-10)
    upper_only = finite_upper & ~equal
    lower_only = finite_lower & ~equal
    if equal.any():
        idx = np.flatnonzero(equal)
        eq_rows.append(matrix[idx])
        eq_rhs.append(upper[idx])
    if upper_only.any():
        idx = np.flatnonzero(upper_only)
        in_rows.append(matrix[idx])
        in_rhs.append(upper[idx])
    if lower_only.any():
        idx = np.flatnonzero(lower_only)
        in_rows.append(-matrix[idx])
        in_rhs.append(-lower[idx])


def load_maros_meszaros(path: Path) -> dict[str, Any]:
    """Load a qpbenchmark MAT file as ``min 1/2 x'Qx + c'x  s.t. Ax = b, Gx <= h``.

    The last ``n`` rows of the stored constraint matrix are the variable bounds;
    they are real constraints. Fixed variables (equal bounds) become equality
    rows; infinite bounds (|value| >= 9e19) are dropped.
    """
    mat = scipy.io.loadmat(str(path))
    n = int(np.asarray(mat["n"]).reshape(-1)[0])
    P = spa.csc_matrix(mat["P"], dtype=float)
    Q = (0.5 * (P + P.T)).tocsc()
    c = np.asarray(mat["q"], dtype=float).reshape(-1)
    C_all = spa.csr_matrix(mat["A"], dtype=float)
    lower = _clean_bounds(mat["l"])
    upper = _clean_bounds(mat["u"])
    if C_all.shape[1] != n or Q.shape != (n, n) or c.shape[0] != n:
        raise ValueError(f"{path.name}: inconsistent dimensions")
    n_rows = C_all.shape[0] - n
    eq_rows: list = []
    eq_rhs: list = []
    in_rows: list = []
    in_rhs: list = []
    _split_rows(C_all[:n_rows], lower[:n_rows], upper[:n_rows], eq_rows, eq_rhs, in_rows, in_rhs)
    _split_rows(spa.identity(n, format="csr"), lower[n_rows:], upper[n_rows:], eq_rows, eq_rhs, in_rows, in_rhs)
    A = spa.vstack(eq_rows, format="csc") if eq_rows else None
    b = np.concatenate(eq_rhs) if eq_rhs else np.zeros(0)
    G = spa.vstack(in_rows, format="csc") if in_rows else None
    h = np.concatenate(in_rhs) if in_rhs else np.zeros(0)
    return {
        "Q": _csc(Q, n, n),
        "c": c,
        "A": _csc(A, b.shape[0], n),
        "b": np.asarray(b, dtype=float),
        "G": _csc(G, h.shape[0], n),
        "h": np.asarray(h, dtype=float),
    }


def perturb_problem(prob: dict[str, Any], rng: np.random.Generator, delta: float) -> dict[str, Any]:
    """Perturb a QP without changing its sparsity, feasibility, or convexity.

    Follows the masked relative perturbation used for related-QP sequences:
    a random subset of at most ``min(10%, 20)`` entries of each data vector is
    changed by a relative amount ``delta * U[-1, 1]``. Inequality right-hand
    sides are only relaxed and positive Hessian diagonal entries are only
    increased, so a feasible convex problem stays feasible and convex.
    """
    Q, c, h = prob["Q"], prob["c"].copy(), prob["h"].copy()
    n, p = c.shape[0], h.shape[0]

    def mask(size: int) -> np.ndarray:
        if size == 0:
            return np.zeros(0, dtype=bool)
        return rng.random(size) < min(0.1, 20.0 / size)

    mc = mask(n)
    c = c + delta * mc * rng.uniform(-1.0, 1.0, n) * c
    mh = mask(p)
    h = h + delta * mh * np.abs(rng.uniform(-1.0, 1.0, p)) * np.maximum(np.abs(h), 1.0)
    diag = Q.diagonal()
    mq = mask(n) & (diag > 0)
    bump = delta * mq * np.abs(rng.uniform(-1.0, 1.0, n)) * diag
    if np.any(bump > 0):
        Q = (Q + spa.diags(bump, format="csc")).tocsc()
    out = dict(prob)
    out.update({"Q": _csc(Q, n, n), "c": c, "h": h})
    return out


def _rand_psd(rng: np.random.Generator, size: int, rank: int) -> np.ndarray:
    if size == 0:
        return np.zeros((0, 0))
    M = rng.standard_normal((size, max(rank, 1)))
    return (M @ M.T) / max(rank, 1)


def degenerate_problem(rng: np.random.Generator, kind: str, n: int) -> dict[str, Any]:
    """Build a feasible, bounded convex QP whose known optimum is degenerate.

    The optimum ``x*`` and multipliers are fixed first and ``c`` is chosen so the
    KKT conditions hold exactly. Degeneracy is built in at the optimum:

    * ``redundant_ineq``: duplicated, rescaled, and looser parallel copies of
      active and inactive inequalities; some active constraints carry zero
      multipliers; more active rows than variables.
    * ``licq_failure``: equality rows repeated as inequalities and duplicated
      (rank-deficient equality matrix), variables pinned at active bounds, and
      cost data spanning many orders of magnitude.
    * ``multiple_solutions``: positive-semidefinite Hessian with a flat optimal
      face, plus always-active zero-gradient rows ``0'x <= 0``.
    """
    G_rows: list[np.ndarray] = []
    h_vals: list[float] = []
    z_vals: list[float] = []
    A_rows: list[np.ndarray] = []
    b_vals: list[float] = []
    y_vals: list[float] = []

    def ineq(row: np.ndarray, rhs: float, mult: float) -> None:
        G_rows.append(np.asarray(row, dtype=float))
        h_vals.append(float(rhs))
        z_vals.append(float(mult))

    def eq(row: np.ndarray, rhs: float, mult: float) -> None:
        A_rows.append(np.asarray(row, dtype=float))
        b_vals.append(float(rhs))
        y_vals.append(float(mult))

    eye = np.eye(n)
    if kind == "redundant_ineq":
        x_star = rng.uniform(-1.0, 1.0, n)
        if rng.random() < 0.5:
            Q = _rand_psd(rng, n, n) + 1e-3 * eye
        else:
            Q = _rand_psd(rng, n, max(1, n // 2))
        k_active = max(2, (2 * n) // 3)
        for _ in range(k_active):
            g = rng.standard_normal(n)
            total = 0.0 if rng.random() < 0.3 else rng.uniform(0.1, 1.0)
            copies = int(rng.integers(2, 5))
            weights = rng.dirichlet(np.ones(copies)) * total
            for j in range(copies):
                alpha = 1.0 if (j == 0 or rng.random() < 0.5) else rng.uniform(0.5, 2.0)
                ineq(alpha * g, alpha * float(g @ x_star), weights[j] / alpha)
        for _ in range(n):
            g = rng.standard_normal(n)
            rhs = float(g @ x_star) + rng.uniform(0.1, 1.0)
            ineq(g, rhs, 0.0)
            if rng.random() < 0.5:
                ineq(g, rhs + rng.uniform(0.0, 1.0), 0.0)
        for i in range(n):
            ineq(eye[i], 10.0, 0.0)
            ineq(-eye[i], 10.0, 0.0)
        if rng.random() < 0.5:
            for _ in range(max(1, n // 8)):
                a = rng.standard_normal(n)
                eq(a, float(a @ x_star), rng.standard_normal())
    elif kind == "licq_failure":
        x_star = rng.uniform(-1.0, 1.0, n)
        pinned = rng.random(n) < 0.3
        x_star[pinned] = 0.0
        S = 10.0 ** rng.uniform(-5.0, 0.0, n)
        Q = S[:, None] * (_rand_psd(rng, n, n) + 1e-3 * eye) * S[None, :]
        m0 = max(1, n // 4)
        for _ in range(m0):
            a = rng.standard_normal(n)
            rhs = float(a @ x_star)
            y = rng.standard_normal() * 10.0 ** rng.uniform(-4.0, 0.0)
            eq(a, rhs, y)
            if rng.random() < 0.5:
                eq(2.0 * a, 2.0 * rhs, 0.0)
            ineq(a, rhs, 0.0 if rng.random() < 0.5 else 10.0 ** rng.uniform(-4.0, 0.0))
            if rng.random() < 0.5:
                ineq(-a, -rhs, 0.0)
        for i in range(n):
            if pinned[i]:
                ineq(-eye[i], 0.0, 0.0 if rng.random() < 0.3 else 10.0 ** rng.uniform(-4.0, 0.0))
                if rng.random() < 0.3:
                    eq(eye[i], 0.0, 0.0)
            ineq(eye[i], 10.0, 0.0)
            ineq(-eye[i], 10.0, 0.0)
    elif kind == "multiple_solutions":
        n_free = max(2, n // 2)
        free = np.zeros(n, dtype=bool)
        free[rng.permutation(n)[:n_free]] = True
        x_star = np.where(free, rng.uniform(0.5, 2.5, n), np.where(rng.random(n) < 0.5, 0.0, 3.0))
        Q = np.zeros((n, n))
        fi = np.flatnonzero(free)
        bi = np.flatnonzero(~free)
        Q[np.ix_(fi, fi)] = _rand_psd(rng, fi.size, max(1, fi.size // 2))
        Q[np.ix_(bi, bi)] = _rand_psd(rng, bi.size, bi.size) + 1e-2 * np.eye(bi.size)
        for i in range(n):
            at_lower = (not free[i]) and x_star[i] == 0.0
            at_upper = (not free[i]) and x_star[i] == 3.0
            ineq(-eye[i], 0.0, rng.uniform(0.0, 1.0) if at_lower and rng.random() < 0.8 else 0.0)
            ineq(eye[i], 3.0, rng.uniform(0.0, 1.0) if at_upper and rng.random() < 0.8 else 0.0)
        for _ in range(max(1, n // 4)):
            ineq(np.zeros(n), 0.0, 0.0)
        if bi.size:
            for _ in range(max(1, bi.size // 3)):
                a = np.zeros(n)
                a[bi] = rng.standard_normal(bi.size)
                eq(a, float(a @ x_star), rng.standard_normal())
            for _ in range(max(1, bi.size // 2)):
                g = np.zeros(n)
                g[bi] = rng.standard_normal(bi.size)
                ineq(g, float(g @ x_star) + rng.uniform(0.0, 1.0), 0.0)
    else:
        raise ValueError(f"unknown degenerate kind {kind!r}")

    G = np.array(G_rows) if G_rows else np.zeros((0, n))
    h = np.array(h_vals)
    z = np.array(z_vals)
    A = np.array(A_rows) if A_rows else np.zeros((0, n))
    b = np.array(b_vals)
    y = np.array(y_vals)
    c = -(Q @ x_star + A.T @ y + G.T @ z)
    # Positive row scaling changes conditioning but not the feasible set or c.
    scale = 10.0 ** rng.uniform(-1.0, 1.0, G.shape[0])
    G = G * scale[:, None]
    h = h * scale
    perm = rng.permutation(G.shape[0])
    G, h = G[perm], h[perm]
    perm_eq = rng.permutation(A.shape[0])
    A, b = A[perm_eq], b[perm_eq]
    return {
        "Q": _csc(0.5 * (Q + Q.T), n, n),
        "c": c,
        "A": _csc(A, A.shape[0], n),
        "b": b,
        "G": _csc(G, G.shape[0], n),
        "h": h,
    }


def paper_degenerate_problems() -> dict[str, dict[str, Any]]:
    """The three small degenerate QPs of the paper's degenerate-problem table.

    The extracted text of the LICQ example is ambiguous about the sign of the
    bound on x2; ``x2 <= 0`` is used because it is the reading under which the
    stated optimum x = [0, 0] activates every constraint.
    """
    cases = {
        "redundant_ineq": (np.eye(2), np.zeros(2), np.zeros((0, 2)), np.zeros(0),
                           np.array([[-1.0, 0.0], [-1.0, 0.0]]), np.array([-1.0, 0.0])),
        "licq_failure": (np.array([[1e-10, 1e-12], [1e-12, 1e-6]]), np.array([1e-4, -1.0]),
                         np.array([[1.0, 0.0]]), np.array([0.0]),
                         np.array([[-1.0, 0.0], [0.0, 1.0]]), np.array([0.0, 0.0])),
        "multiple_solutions": (np.array([[1.0, 0.0], [0.0, 0.0]]), np.array([1.0, 0.0]),
                               np.zeros((0, 2)), np.zeros(0),
                               np.array([[0.0, 0.0], [-1.0, 0.0], [1.0, 0.0], [0.0, -1.0], [0.0, 1.0]]),
                               np.array([0.0, 0.0, 3.0, 0.0, 3.0])),
    }
    out = {}
    for name, (Q, c, A, b, G, h) in cases.items():
        out[name] = {"Q": _csc(Q, 2, 2), "c": c, "A": _csc(A, A.shape[0], 2), "b": b,
                     "G": _csc(G, G.shape[0], 2), "h": h}
    return out


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _make_instance(instance_id: str, family: str, base: str, draw: int, prob: dict[str, Any]) -> Instance:
    inst = Instance(instance_id, family, base, draw, prob["Q"], np.asarray(prob["c"], dtype=float),
                    prob["A"], np.asarray(prob["b"], dtype=float), prob["G"], np.asarray(prob["h"], dtype=float))
    if not (np.all(np.isfinite(inst.c)) and np.all(np.isfinite(inst.b)) and np.all(np.isfinite(inst.h))):
        raise ValueError(f"{instance_id}: non-finite problem data")
    inst.arrays = instance_arrays(inst)
    inst.content_hash = content_hash(inst.arrays)
    return inst


def load_base_problems(names_to_hash: dict[str, str]) -> dict[str, dict[str, Any]]:
    """Load pinned Maros-Meszaros files; any missing or altered file aborts scoring."""
    problems = {}
    for name, expected in names_to_hash.items():
        path = DATA_DIR / f"{name}.mat"
        if not path.is_file():
            raise SystemExit(f"[{SLICE}] missing benchmark file {path}; run scripts/download.sh")
        actual = _sha256_file(path)
        if actual != expected:
            raise SystemExit(f"[{SLICE}] {path} does not match its pinned SHA-256; refusing to score altered problem data")
        problems[name] = load_maros_meszaros(path)
    return problems


def build_instances(manifest: dict[str, Any]) -> list[Instance]:
    instances: list[Instance] = []
    mm = manifest["maros_meszaros"]
    base = load_base_problems(mm["problems"])
    pert = mm["perturbation"]
    for name in sorted(base):
        if pert.get("include_original", False):
            instances.append(_make_instance(f"mm/{name}/orig", "maros_meszaros", name, -1, base[name]))
        for draw in range(int(pert["draws"])):
            seed_material = f"{pert['seed']}|{name}|{draw}".encode()
            rng = np.random.default_rng(int.from_bytes(hashlib.sha256(seed_material).digest()[:8], "little"))
            prob = perturb_problem(base[name], rng, float(pert["delta"]))
            instances.append(_make_instance(f"mm/{name}/d{draw}", "maros_meszaros", name, draw, prob))
    deg = manifest["degenerate"]
    rng = np.random.default_rng(int(deg["seed"]))
    sizes = [int(s) for s in deg["sizes"]]
    for kind in deg["kinds"]:
        for k in range(int(deg["count_per_kind"])):
            size = sizes[k % len(sizes)]
            prob = degenerate_problem(rng, kind, size)
            instances.append(_make_instance(f"deg/{kind}/{k:02d}", "degenerate", kind, k, prob))
    if deg.get("include_paper_cases", False):
        for name, prob in paper_degenerate_problems().items():
            instances.append(_make_instance(f"deg/paper_{name}", "degenerate", f"paper_{name}", -1, prob))
    return instances


# --------------------------------------------------------------------------- #
# Instance files and hashing
# --------------------------------------------------------------------------- #


def instance_arrays(inst: Instance) -> dict[str, np.ndarray]:
    arrays: dict[str, np.ndarray] = {
        "format": np.array(FORMAT_TAG),
        "n": np.array(inst.n, dtype=np.int64),
        "m": np.array(inst.m, dtype=np.int64),
        "p": np.array(inst.p, dtype=np.int64),
        "c": np.ascontiguousarray(inst.c, dtype=np.float64),
        "b": np.ascontiguousarray(inst.b, dtype=np.float64),
        "h": np.ascontiguousarray(inst.h, dtype=np.float64),
    }
    for key, matrix in (("Q", inst.Q), ("A", inst.A), ("G", inst.G)):
        arrays[f"{key}_data"] = np.ascontiguousarray(matrix.data, dtype=np.float64)
        arrays[f"{key}_indices"] = np.ascontiguousarray(matrix.indices, dtype=np.int64)
        arrays[f"{key}_indptr"] = np.ascontiguousarray(matrix.indptr, dtype=np.int64)
    return arrays


def content_hash(arrays: dict[str, np.ndarray]) -> str:
    digest = hashlib.sha256()
    for key in sorted(arrays):
        arr = np.ascontiguousarray(arrays[key])
        digest.update(key.encode())
        digest.update(arr.dtype.str.encode())
        digest.update(str(arr.shape).encode())
        digest.update(arr.tobytes())
    return digest.hexdigest()


# --------------------------------------------------------------------------- #
# Verification
# --------------------------------------------------------------------------- #


def _ninf(vec: np.ndarray) -> float:
    return float(np.max(np.abs(vec))) if vec.size else 0.0


def read_solution(path: Path, inst: Instance) -> tuple[dict[str, np.ndarray] | None, str, dict[str, Any]]:
    """Read a solver output file; returns (point, reason, reported diagnostics)."""
    reported: dict[str, Any] = {}
    if not path.is_file():
        return None, "no_output", reported
    try:
        with np.load(path, allow_pickle=False) as data:
            files = set(data.files)
            if "iterations" in files:
                try:
                    reported["iterations"] = float(np.asarray(data["iterations"]).reshape(-1)[0])
                except Exception:
                    pass
            if "status" in files:
                try:
                    reported["status"] = str(np.asarray(data["status"]).reshape(-1)[0])[:64]
                except Exception:
                    pass
            point = {}
            for key, size in (("x", inst.n), ("y", inst.m), ("z", inst.p)):
                if key not in files:
                    if size == 0:
                        point[key] = np.zeros(0)
                        continue
                    return None, f"missing_{key}", reported
                arr = np.asarray(data[key], dtype=np.float64).reshape(-1)
                if arr.shape[0] != size:
                    return None, f"bad_shape_{key}", reported
                point[key] = arr
    except Exception as exc:  # unreadable or malformed file
        return None, f"unreadable_output:{type(exc).__name__}", reported
    for key, arr in point.items():
        if not np.all(np.isfinite(arr)):
            return None, f"nonfinite_{key}", reported
    return point, "ok", reported


def kkt_ratios(inst: Instance, x: np.ndarray, y: np.ndarray, z: np.ndarray) -> dict[str, float]:
    """Residual / scale ratios; a point is accepted at tolerance eps when every ratio <= eps.

    Scales follow the paper's combined absolute + relative stopping rule
    (absolute and relative tolerances equal), plus a duality-gap test.
    """
    with np.errstate(all="ignore"):
        Q, c, A, b, G, h = inst.Q, inst.c, inst.A, inst.b, inst.G, inst.h
        Qx = Q @ x
        Ax = A @ x
        Gx = G @ x
        Aty = A.T @ y
        Gtz = G.T @ z
        r_eq = _ninf(Ax - b)
        s_eq = 1.0 + max(_ninf(Ax), _ninf(b))
        r_in = _ninf(np.maximum(Gx - h, 0.0))
        s_in = 1.0 + max(_ninf(Gx), _ninf(h))
        r_du = _ninf(Qx + c + Aty + Gtz)
        s_du = 1.0 + max(_ninf(Qx), _ninf(c), _ninf(Aty), _ninf(Gtz))
        r_sg = _ninf(np.maximum(-z, 0.0))
        s_sg = 1.0 + _ninf(z)
        comp = np.minimum(np.maximum(h - Gx, 0.0), np.maximum(z, 0.0))
        r_cp = _ninf(comp)
        s_cp = 1.0 + max(_ninf(Gx), _ninf(h), _ninf(z))
        xQx = float(x @ Qx)
        cx = float(c @ x)
        dual_lin = float(b @ y + h @ z)
        r_gap = abs(xQx + cx + dual_lin)
        s_gap = 1.0 + max(abs(xQx), abs(cx), abs(dual_lin))
        ratios = {
            "primal_eq": r_eq / s_eq,
            "primal_ineq": r_in / s_in,
            "dual": r_du / s_du,
            "dual_sign": r_sg / s_sg,
            "complementarity": r_cp / s_cp,
            "gap": r_gap / s_gap,
        }
    return {k: (float(v) if np.isfinite(v) else float("inf")) for k, v in ratios.items()}


def verify(inst: Instance, output: Path, eps: float) -> dict[str, Any]:
    point, reason, reported = read_solution(output, inst)
    record: dict[str, Any] = {"reported": reported}
    if point is None:
        record.update(solved=False, reason=reason, ratios=None)
        return record
    ratios = kkt_ratios(inst, point["x"], point["y"], point["z"])
    failed = sorted(k for k, v in ratios.items() if not v <= eps)
    record.update(solved=not failed, reason="verified" if not failed else "kkt:" + ",".join(failed), ratios=ratios)
    return record


# --------------------------------------------------------------------------- #
# Solver discovery and sandboxed execution
# --------------------------------------------------------------------------- #


def _hash_tree(digest: "hashlib._Hash", root: Path, patterns: tuple[str, ...]) -> None:
    if not root.exists():
        return
    files = sorted(p for pat in patterns for p in root.rglob(pat) if p.is_file() and "__pycache__" not in p.parts)
    for path in files:
        digest.update(str(path.relative_to(WORKSPACE)).encode())
        digest.update(path.read_bytes())


def solver_fingerprint(script: Path) -> str:
    """Identify a solver's code (used only to key the optional result cache)."""
    digest = hashlib.sha256()
    digest.update(PROTOCOL.encode())
    digest.update(script.read_bytes())
    for sub in ("method", "baseline", "scripts/hardening"):
        _hash_tree(digest, WORKSPACE / sub, ("*.py", "*.sh", "*.json"))
    for path in sorted((WORKSPACE / "data").glob("*.py")):
        digest.update(path.name.encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def baseline_fingerprint() -> str:
    digest = hashlib.sha256()
    digest.update(PROTOCOL.encode())
    digest.update((EVAL_DIR / "osqp_solver.py").read_bytes())
    try:
        import osqp  # noqa: PLC0415

        digest.update(str(getattr(osqp, "__version__", "unknown")).encode())
    except Exception:
        digest.update(b"osqp-missing")
    return digest.hexdigest()


def discover_solvers() -> dict[str, dict[str, Any]]:
    solvers: dict[str, dict[str, Any]] = {}
    if SOLVER_DIR.is_dir():
        for script in sorted(SOLVER_DIR.glob("*.sh")):
            name = script.stem
            if not NAME_RE.match(name):
                print(f"[{SLICE}] skipping solver with invalid name: {script.name}", flush=True)
                continue
            if name == BASELINE_NAME:
                raise SystemExit(f"[{SLICE}] '{BASELINE_NAME}' is reserved for the evaluator-owned baseline; rename {script}")
            solvers[name] = {"cmd": ["bash", str(script)], "fingerprint": solver_fingerprint(script)}
    solvers[BASELINE_NAME] = {"cmd": [sys.executable, "-m", BASELINE_MODULE], "fingerprint": baseline_fingerprint()}
    return solvers


def available_cpus() -> int:
    try:
        count = len(os.sched_getaffinity(0))
    except Exception:
        count = os.cpu_count() or 1
    quota = None
    try:
        text = Path("/sys/fs/cgroup/cpu.max").read_text().split()
        if text and text[0] != "max":
            quota = float(text[0]) / float(text[1])
    except Exception:
        try:
            q = float(Path("/sys/fs/cgroup/cpu/cpu.cfs_quota_us").read_text())
            per = float(Path("/sys/fs/cgroup/cpu/cpu.cfs_period_us").read_text())
            if q > 0:
                quota = q / per
        except Exception:
            quota = None
    if quota is not None:
        count = min(count, max(1, int(quota)))
    return max(1, count)


def _solver_env() -> dict[str, str]:
    env = dict(os.environ)
    for key in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS",
                "VECLIB_MAXIMUM_THREADS", "BLIS_NUM_THREADS"):
        env[key] = "1"
    env["PYTHONHASHSEED"] = "0"
    env.pop(CACHE_ENV, None)
    return env


_LIMIT_SH = 'ulimit -c 0; ulimit -H -t {hard} && ulimit -S -t {soft} && exec "$@"'


def run_limited(cmd: list[str], log_path: Path) -> dict[str, Any]:
    """Run one solver call under a CPU-time limit (plus a wall-clock backstop)."""
    wrapped = ["bash", "-c", _LIMIT_SH.format(soft=CPU_LIMIT_S, hard=CPU_LIMIT_S + 5), "qp-gym-limit", *cmd]
    start = time.monotonic()
    killed = False
    with log_path.open("wb") as log:
        proc = subprocess.Popen(wrapped, cwd=str(WORKSPACE), env=_solver_env(), stdin=subprocess.DEVNULL,
                                stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        while True:
            pid, status, usage = os.wait4(proc.pid, os.WNOHANG)
            if pid == proc.pid:
                break
            if not killed and time.monotonic() - start > WALL_LIMIT_S:
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                killed = True
            time.sleep(0.02)
        proc.returncode = os.waitstatus_to_exitcode(status)
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            pass
    return {
        "returncode": int(proc.returncode),
        "cpu_s": float(usage.ru_utime + usage.ru_stime),
        "wall_s": float(time.monotonic() - start),
        "wall_killed": killed,
    }


def _cache_dir(key: str) -> Path | None:
    root = os.environ.get(CACHE_ENV)
    if not root:
        return None
    return Path(root) / key[:2] / key


def run_job(solver: str, spec: dict[str, Any], inst: Instance, tol_name: str, tol: float,
            workdir: Path) -> dict[str, Any]:
    key = hashlib.sha256(
        f"{PROTOCOL}|{spec['fingerprint']}|{inst.content_hash}|{tol!r}|{CPU_LIMIT_S}".encode()
    ).hexdigest()
    cache = _cache_dir(key)
    cache_hit = False
    run_info: dict[str, Any]
    if cache is not None and (cache / "meta.json").is_file():
        run_info = json.loads((cache / "meta.json").read_text())
        output = cache / "output.npz"
        cache_hit = True
    else:
        job_dir = workdir / "runs" / solver / f"{inst.instance_id.replace('/', '__')}__{tol_name}"
        job_dir.mkdir(parents=True, exist_ok=True)
        output = job_dir / "output.npz"
        if output.exists():
            output.unlink()
        cmd = [*spec["cmd"], "--problem", str(inst.path), "--output", str(output), "--tol", repr(tol)]
        run_info = run_limited(cmd, job_dir / "solver.log")
        if cache is not None:
            tmp = cache.parent / f".{key}.{os.getpid()}.{threading.get_ident()}.tmp"
            shutil.rmtree(tmp, ignore_errors=True)
            tmp.mkdir(parents=True, exist_ok=True)
            if output.is_file():
                shutil.copy2(output, tmp / "output.npz")
            shutil.copy2(job_dir / "solver.log", tmp / "solver.log")
            (tmp / "meta.json").write_text(json.dumps(run_info))
            if cache.exists():
                shutil.rmtree(tmp, ignore_errors=True)
            else:
                os.replace(tmp, cache)
            output = cache / "output.npz"
    record = verify(inst, output, tol)
    record.update({
        "solver": solver,
        "instance": inst.instance_id,
        "family": inst.family,
        "base": inst.base,
        "draw": inst.draw,
        "tolerance": tol_name,
        "instance_hash": inst.content_hash,
        "cache_hit": cache_hit,
        "raw_output": str(output) if output.is_file() else None,
        **{k: run_info.get(k) for k in ("returncode", "cpu_s", "wall_s", "wall_killed")},
    })
    return record


# --------------------------------------------------------------------------- #
# Scoring
# --------------------------------------------------------------------------- #


def summarize(records: list[dict[str, Any]], solvers: list[str], instances: list[Instance]) -> dict[str, Any]:
    totals: dict[str, int] = {}
    for inst in instances:
        totals[inst.family] = totals.get(inst.family, 0) + 1
    experiments: dict[str, Any] = {}
    diagnostics: dict[str, Any] = {}
    for solver in solvers:
        diag_solver: dict[str, Any] = {}
        for family, (exp_name, template) in FAMILY_EXPERIMENTS.items():
            if family not in totals:
                continue
            diag_family: dict[str, Any] = {}
            for tol_name, _ in TOLERANCES:
                recs = [r for r in records if r["solver"] == solver and r["family"] == family and r["tolerance"] == tol_name]
                solved = sum(1 for r in recs if r["solved"])
                total = totals[family]  # fixed denominator: every manifest instance
                rate = 100.0 * (total - solved) / total
                experiments.setdefault(exp_name, {"results": {}})["results"].setdefault(solver, {})[
                    template.format(tol=tol_name)] = rate
                reasons: dict[str, int] = {}
                for r in recs:
                    if not r["solved"]:
                        key = r["reason"].split(":")[0] if not r["reason"].startswith("kkt") else r["reason"]
                        reasons[key] = reasons.get(key, 0) + 1
                iters = [r["reported"].get("iterations") for r in recs if r["solved"] and "iterations" in r["reported"]]
                diag_family[tol_name] = {
                    "instances": total,
                    "verified_solved": solved,
                    "failure_reasons": dict(sorted(reasons.items())),
                    "median_reported_iterations_unverified_unscored":
                        float(np.median(iters)) if iters else None,
                }
            diag_solver[family] = diag_family
        diagnostics[solver] = diag_solver
    return {"experiments": experiments, "diagnostics": diagnostics}


def evaluate(instances: list[Instance], output_path: Path, *, slice_name: str, only: list[str] | None,
             workers: int | None, keep_workdir: bool, provenance_extra: dict[str, Any]) -> dict[str, Any]:
    if output_path.exists():
        output_path.unlink()  # never leave a stale score behind if this run fails
    solvers = discover_solvers()
    if only:
        unknown = sorted(set(only) - set(solvers))
        if unknown:
            raise SystemExit(f"[{slice_name}] unknown solvers requested: {unknown}; known: {sorted(solvers)}")
        solvers = {k: v for k, v in solvers.items() if k in only}
    n_workers = workers or int(os.environ.get(WORKERS_ENV, "0") or 0) or min(8, available_cpus())
    workdir = Path(tempfile.mkdtemp(prefix=f"qp_gym_{slice_name}_"))
    print(f"[{slice_name}] {len(instances)} instances x {len(TOLERANCES)} tolerances x {len(solvers)} solvers "
          f"({', '.join(solvers)}); workers={n_workers}; cpu budget={CPU_LIMIT_S}s/instance", flush=True)
    try:
        inst_dir = workdir / "instances"
        inst_dir.mkdir(parents=True)
        for idx, inst in enumerate(instances):
            inst.path = inst_dir / f"inst_{idx:05d}.npz"
            np.savez(inst.path, **inst.arrays)
        # Largest problems first for better packing across workers.
        order = sorted(instances, key=lambda i: -(i.Q.nnz + i.A.nnz + i.G.nnz + i.n * i.p // 64))
        jobs = [(s, solvers[s], inst, tn, tv) for inst in order for tn, tv in TOLERANCES for s in solvers]
        records: list[dict[str, Any]] = []
        lock = threading.Lock()
        started = time.monotonic()
        cpu_used = {name: 0.0 for name in solvers}

        def work(job: tuple) -> None:
            solver, spec, inst, tol_name, tol = job
            base_rec = {"solver": solver, "instance": inst.instance_id, "family": inst.family, "base": inst.base,
                        "draw": inst.draw, "tolerance": tol_name, "solved": False, "reported": {}, "ratios": None}
            with lock:
                exhausted = cpu_used[solver] >= TOTAL_CPU_BUDGET_S
            if exhausted:
                rec = {**base_rec, "reason": "total_cpu_budget_exhausted"}
            else:
                try:
                    rec = run_job(solver, spec, inst, tol_name, tol, workdir)
                except Exception as exc:  # evaluator-side failure for this job: count as unsolved
                    rec = {**base_rec, "reason": f"evaluator_error:{type(exc).__name__}:{exc}"}
            with lock:
                cpu_used[solver] += float(rec.get("cpu_s") or 0.0)
                records.append(rec)
                done = len(records)
                if done % 25 == 0 or done == len(jobs) or not rec.get("cache_hit", False):
                    print(f"[{slice_name}] {done}/{len(jobs)} {solver:>12s} {inst.instance_id:<28s} {tol_name:<6s} "
                          f"{'OK ' if rec['solved'] else 'FAIL'} {rec['reason'][:40]:<40s} "
                          f"cpu={rec.get('cpu_s') or 0:.1f}s t={time.monotonic() - started:.0f}s", flush=True)

        with ThreadPoolExecutor(max_workers=n_workers) as pool:
            list(pool.map(work, jobs))
    finally:
        if not keep_workdir:
            shutil.rmtree(workdir, ignore_errors=True)

    summary = summarize(records, list(solvers), instances)
    scores = {
        "_provenance": {
            "generator": f"eval.{slice_name}.evaluate" if slice_name in ("train", "test") else "eval.benchmark",
            "slice": slice_name,
            "protocol": PROTOCOL,
            "tolerances": {k: v for k, v in TOLERANCES},
            "cpu_seconds_per_instance": CPU_LIMIT_S,
            "total_cpu_seconds_per_solver": TOTAL_CPU_BUDGET_S,
            "instances": {fam: sum(1 for i in instances if i.family == fam) for fam in FAMILY_EXPERIMENTS},
            "success_criterion": "evaluator-computed residuals of the returned (x, y, z) are within the tolerance "
                                 "for primal feasibility, dual feasibility, multiplier sign, complementarity, and "
                                 "duality gap; solver-reported status/iterations are ignored; every manifest "
                                 "instance counts, unsolved or missing ones as failures",
            "solvers": sorted(solvers),
            **provenance_extra,
        },
        "_diagnostics": summary["diagnostics"],
        "experiments": summary["experiments"],
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(scores, indent=2) + "\n")
    OUTCOME_DIR.mkdir(parents=True, exist_ok=True)
    out_records = OUTCOME_DIR.parent / slice_name / "outcomes.jsonl"
    out_records.parent.mkdir(parents=True, exist_ok=True)
    with out_records.open("w") as handle:
        for rec in sorted(records, key=lambda r: (r["solver"], r["instance"], r["tolerance"])):
            handle.write(json.dumps(rec, default=str) + "\n")
    print(json.dumps(scores["experiments"], indent=2))
    print(f"[{slice_name}] wrote {output_path} (elapsed {time.monotonic() - started:.0f}s)", flush=True)
    return scores


def load_manifest() -> dict[str, Any]:
    manifest = json.loads(MANIFEST_PATH.read_text())
    if manifest.get("slice") != SLICE or manifest.get("protocol") != PROTOCOL:
        raise SystemExit(f"{MANIFEST_PATH}: unexpected slice/protocol")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--solvers", nargs="+", default=None,
                        help="Restrict to these solver names (default: every scripts/solvers/*.sh plus the baseline).")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--workers", type=int, default=None)
    parser.add_argument("--keep-workdir", action="store_true")
    args = parser.parse_args()
    output = Path(args.output)
    if output.exists():
        output.unlink()  # a run that aborts (e.g. altered data) must not leave a stale score
    manifest = load_manifest()
    instances = build_instances(manifest)
    evaluate(instances, Path(args.output), slice_name=SLICE, only=args.solvers, workers=args.workers,
             keep_workdir=args.keep_workdir, provenance_extra={"manifest": str(MANIFEST_PATH.relative_to(WORKSPACE))})


if __name__ == "__main__":
    main()
