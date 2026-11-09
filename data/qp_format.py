"""Reader/writer for the benchmark's QP instance and solution files.

Instance file (``.npz``, written by the evaluator), problem

    minimize 1/2 x'Qx + c'x   subject to   A x = b,   G x <= h

* ``n``, ``m``, ``p``: number of variables, equality rows, inequality rows;
* ``Q_data``/``Q_indices``/``Q_indptr``: CSC arrays of the symmetric n x n Q
  (``A_*`` and ``G_*`` likewise for the m x n and p x n constraint matrices);
* ``c`` (n,), ``b`` (m,), ``h`` (p,).

Solution file (``.npz``, written by a solver): ``x`` (n,), ``y`` (m,),
``z`` (p,) with the sign convention ``Qx + c + A'y + G'z = 0`` and ``z >= 0``.
Any other entries (for example ``iterations`` or ``status``) are kept only as
unscored diagnostics.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import numpy as np
import scipy.sparse as spa


def read_instance(path: str | Path) -> dict[str, Any]:
    with np.load(path, allow_pickle=False) as data:
        n, m, p = (int(data[k]) for k in ("n", "m", "p"))

        def matrix(key: str, rows: int) -> spa.csc_matrix:
            return spa.csc_matrix(
                (np.array(data[f"{key}_data"]), np.array(data[f"{key}_indices"]), np.array(data[f"{key}_indptr"])),
                shape=(rows, n),
            )

        return {
            "n": n,
            "m": m,
            "p": p,
            "Q": matrix("Q", n),
            "c": np.array(data["c"], dtype=float),
            "A": matrix("A", m),
            "b": np.array(data["b"], dtype=float),
            "G": matrix("G", p),
            "h": np.array(data["h"], dtype=float),
        }


def write_solution(path: str | Path, x: np.ndarray, y: np.ndarray, z: np.ndarray, **extra: Any) -> None:
    """Atomically write a solution file (partial files are never left behind)."""
    path = Path(path)
    tmp = path.with_name(path.name + ".partial.npz")
    np.savez(tmp, x=np.asarray(x, dtype=float), y=np.asarray(y, dtype=float), z=np.asarray(z, dtype=float),
             **{k: np.asarray(v) for k, v in extra.items()})
    os.replace(tmp, path)
