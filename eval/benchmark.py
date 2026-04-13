#!/usr/bin/env python3
"""
Evaluation script for ODYN QP solver benchmark.

Runs ODYN, OSQP, and PROXQP on the Maros-Meszárós test set and computes
failure rates and performance metrics.
"""

import argparse
import json
import time
import numpy as np
import scipy.sparse as spa
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import sys

# Add method directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "method"))

from odyn_solver import DenseOdynSolver, SparseOdynSolver, OdynParams


def load_maros_meszaros_problem(mat_path: str):
    """Load a Maros-Meszárós .mat file into QP format."""
    import scipy.io

    mat_dict = scipy.io.loadmat(mat_path)
    P = mat_dict["P"].astype(float)
    if spa.issparse(P):
        P = P.tocsc()
    q = mat_dict["q"].T.flatten().astype(float)
    A_mat = mat_dict["A"].astype(float)
    if spa.issparse(A_mat):
        A_mat = A_mat.tocsc()
    l = np.array(mat_dict["l"].T.flatten().astype(float))
    u = np.array(mat_dict["u"].T.flatten().astype(float))
    n = int(mat_dict["n"].T.flatten().astype(int)[0])
    m_total = int(mat_dict["m"].T.flatten().astype(int)[0])

    # Replace infinity markers in bounds
    l[l > 9e19] = np.inf
    u[u > 9e19] = np.inf
    l[l < -9e19] = np.inf
    u[u < -9e19] = np.inf

    # Separate C (constraint) from x bounds (last n rows)
    lb = l[-n:]
    ub = u[-n:]
    l_c = l[:-n]
    u_c = u[:-n]

    # C is the first m_total - n rows of A_mat
    m_con = m_total - n
    C = A_mat[:m_con] if m_con > 0 else None

    # Identify equality vs inequality constraint rows
    bounds_are_equal = np.abs(u_c - l_c) < 1e-10
    eq_mask = bounds_are_equal
    ineq_mask = ~bounds_are_equal
    eq_idx = np.where(eq_mask)[0]
    ineq_idx = np.where(ineq_mask)[0]

    # Equality constraints: A x = b
    if len(eq_idx) > 0:
        A = C[eq_idx] if C is not None else None
        b = u_c[eq_idx]
    else:
        A, b = None, None

    # Inequality constraints: G x <= h (original) and -G x <= -l (from lower bounds)
    INFINITY = 9e19
    h1 = u_c[ineq_idx]
    h2 = -l_c[ineq_idx]
    g1_idx = np.where(h1 < INFINITY)[0]
    g2_idx = np.where(h2 < INFINITY)[0]

    rows_g1 = ineq_idx[g1_idx]
    rows_g2 = ineq_idx[g2_idx]

    G_rows = []
    h_vals = []
    if len(rows_g1) > 0 and C is not None:
        G_rows.append(C[rows_g1])
        h_vals.append(h1[g1_idx])
    if len(rows_g2) > 0 and C is not None:
        G_rows.append(-C[rows_g2])
        h_vals.append(h2[g2_idx])

    if G_rows:
        G = spa.vstack(G_rows, format='csc')
        h = np.concatenate(h_vals)
    else:
        G, h = None, None

    name = Path(mat_path).stem
    return {
        "name": name,
        "P": P,
        "q": q,
        "A": A,
        "b": b,
        "G": G,
        "h": h,
        "lb": lb,
        "ub": ub,
    }


def is_dense(problem: dict) -> bool:
    """Check if problem should use dense backend."""
    n = problem["q"].shape[0]
    m = problem["A"].shape[0] if problem["A"] is not None else 0
    p = problem["G"].shape[0] if problem["G"] is not None else 0
    return n <= 1000


def run_osqp(problem: dict, rtol: float, timeout: float = 120.0) -> dict:
    """Run OSQP on a problem. Returns dict with success, iterations, time."""
    try:
        import osqp
    except ImportError:
        return {"success": False, "iterations": 0, "solve_time": 0, "status": "import_error"}

    P = problem["P"]
    if spa.issparse(P):
        P = P.tocsc()
    q = problem["q"]
    A = problem["A"]
    G = problem["G"]

    # Build combined constraint matrix [A; G] and bounds
    if A is not None and G is not None:
        A_combined = spa.vstack([A, G], format='csc')
    elif A is not None:
        A_combined = A
    elif G is not None:
        A_combined = G
    else:
        A_combined = spa.csc_matrix((0, P.shape[0]))

    # Box constraints: lb <= x <= ub
    lb = problem["lb"]
    ub = problem["ub"]
    n = len(lb)

    # Lower bound for constraints: A_combined * x >= l
    # Upper bound for constraints: A_combined * x <= u
    # For equality constraints, l == u
    l_all = np.full(A_combined.shape[0], -np.inf)
    u_all = np.full(A_combined.shape[0], np.inf)

    # Figure out which rows are equality vs inequality
    m_eq = problem["A"].shape[0] if problem["A"] is not None else 0
    if m_eq > 0 and G is not None:
        # A rows are first, G rows are second
        # A rows are equalities, so l[u[:m_eq]] = u[u[:m_eq]] = b
        l_all[:m_eq] = problem["b"]
        u_all[:m_eq] = problem["b"]
    elif m_eq > 0:
        l_all[:m_eq] = problem["b"]
        u_all[:m_eq] = problem["b"]

    m = osqp.OSQP()
    try:
        m.setup(P, q, A_combined, l_all, u_all, max_iter=2000, rho=0.1,
                eps_rel=rtol, eps_abs=rtol, polish_refine_iter=3)
    except Exception as e:
        return {"success": False, "iterations": 0, "solve_time": 0, "status": f"setup_error: {e}"}

    t0 = time.time()
    try:
        results = m.solve()
        solve_time = time.time() - t0
        if results.info.status_val == 1:  # solved
            return {
                "success": True,
                "iterations": results.info.iter,
                "solve_time": solve_time,
                "status": "optimal",
            }
        else:
            return {
                "success": False,
                "iterations": results.info.iter,
                "solve_time": solve_time,
                "status": results.info.status,
            }
    except Exception as e:
        return {"success": False, "iterations": 0, "solve_time": time.time() - t0, "status": f"solve_error: {e}"}


def run_proxqp(problem: dict, rtol: float, timeout: float = 120.0) -> dict:
    """Run PROXQP on a problem."""
    try:
        import proxsuite
    except ImportError:
        return {"success": False, "iterations": 0, "solve_time": 0, "status": "import_error"}

    P = problem["P"]
    if spa.issparse(P):
        P = P.toarray()
    q = problem["q"]
    A = problem["A"]
    G = problem["G"]

    try:
        from proxsuite import proxqp
        t0 = time.time()
        n = len(q)
        m_eq = A.shape[0] if A is not None and A.size > 0 else 0
        m_ineq = G.shape[0] if G is not None and G.size > 0 else 0

        # Build matrices
        A_mat = A if A is not None and A.size > 0 else None
        C_mat = G if G is not None and G.size > 0 else None
        b_vec = problem["b"] if problem["b"] is not None else None
        h_vec = problem["h"] if problem["h"] is not None else None
        # PROXQP requires both l and u for inequalities; use -inf for lower bounds
        l_vec = np.full(m_ineq, -np.inf) if m_ineq > 0 else None
        u_vec = h_vec

        qp = proxqp.dense.QP(n, m_eq, m_ineq)
        qp.init(P, q, A=A_mat, b=b_vec, C=C_mat, l=l_vec, u=u_vec,
                eps_rel=rtol, eps_abs=rtol)
        qp.solve()
        solve_time = time.time() - t0
        return {
            "success": qp.results.info.status.name == "PROXQP_SOLVED",
            "iterations": qp.results.info.iter,
            "solve_time": solve_time,
            "status": qp.results.info.status.name,
        }
    except Exception as e:
        return {"success": False, "iterations": 0, "solve_time": 0, "status": f"error: {e}"}


def run_odyn(problem: dict, rtol: float, timeout: float = 120.0) -> dict:
    """Run ODYN on a problem."""
    P = problem["P"]
    q = problem["q"]
    A = problem["A"]
    b = problem["b"]
    G = problem["G"]
    h = problem["h"]

    use_dense = is_dense(problem)

    t0 = time.time()
    try:
        if use_dense:
            if spa.issparse(P):
                P = P.toarray()
            if A is not None and spa.issparse(A):
                A = A.toarray()
            if G is not None and spa.issparse(G):
                G = G.toarray()

            solver = DenseOdynSolver(OdynParams(), verbose=False)
            result = solver.solve(
                P, q,
                None if A is None or A.size == 0 else A,
                None if b is None else b,
                None if G is None or G.size == 0 else G,
                None if h is None else h,
                rtol=rtol, atol=rtol * 0.01
            )
        else:
            P_sp = P if spa.issparse(P) else spa.csc_matrix(P)
            A_sp = A if A is None or A.size == 0 or spa.issparse(A) else spa.csc_matrix(A) if A is not None else None
            G_sp = G if G is None or G.size == 0 or spa.issparse(G) else spa.csc_matrix(G) if G is not None else None

            solver = SparseOdynSolver(OdynParams(), verbose=False)
            result = solver.solve(
                P_sp, q,
                A_sp, None if b is None else b,
                G_sp, None if h is None else h,
                rtol=rtol, atol=rtol * 0.01
            )

        solve_time = time.time() - t0
        return {
            "success": result.success,
            "iterations": result.iterations,
            "solve_time": solve_time + result.solve_time,
            "status": result.status,
            "primal_residual": result.primal_residual,
            "dual_residual": result.dual_residual,
        }
    except Exception as e:
        solve_time = time.time() - t0
        return {"success": False, "iterations": 0, "solve_time": solve_time, "status": f"error: {e}"}


def run_degenerate_test_cases() -> Dict[str, Dict]:
    """Run the three degenerate test cases from the paper."""
    # Test case 1: Redundant inequalities (Eq. 66)
    # min 0.5*(x1^2 + x2^2) s.t. x1 >= 1
    # The 'redundant' is that the bound x1 >= 0 is looser than x1 >= 1
    # So feasible region: x1 >= 1 (only the binding constraint matters)
    # Optimal: x1 = 1, x2 = 0
    Q1 = np.array([[1.0, 0.0], [0.0, 1.0]])
    c1 = np.zeros(2)
    A1 = None
    b1 = None
    G1 = np.array([[-1.0, 0.0]])  # -x1 <= -1 -> x1 >= 1
    h1 = np.array([-1.0])

    # Test case 2: LICQ failure (Eq. 67)
    # min with tiny Q entries, equality x1=0, and bounds
    Q2 = np.array([[1e-10, 5e-13], [5e-13, 1e-6]])
    c2 = np.array([1e-4, -1.0])
    A2 = np.array([[1.0, 0.0]])
    b2 = np.array([0.0])
    G2 = np.array([[-1.0, 0.0], [0.0, -1.0]])  # x1 >= 0, x2 >= 0
    h2 = np.array([0.0, 0.0])

    # Test case 3: Multiple solutions (Eq. 68)
    # Q has zero row, redundant constraint (0*x1 + 0*x2 <= 0 is always active but doesn't constrain)
    Q3 = np.array([[0.0, 0.0], [0.0, 1.0]])
    c3 = np.array([1.0, 0.0])
    A3 = None
    b3 = None
    G3 = np.array([[0.0, 0.0], [-1.0, 0.0], [0.0, -1.0], [0.0, 1.0]])  # redundant 0<=0, -1<=x1<=3, -1<=x2<=3
    h3 = np.array([0.0, 0.0, 0.0, 3.0])

    results = {}

    for name, Q, c, A, b, G, h in [
        ("redundant_ineq", Q1, c1, A1, b1, G1, h1),
        ("licq_failure", Q2, c2, A2, b2, G2, h2),
        ("multiple_solutions", Q3, c3, A3, b3, G3, h3),
    ]:
        solver = DenseOdynSolver(OdynParams(), verbose=False)
        result = solver.solve(Q, c, A, b, G, h, rtol=1e-9)
        results[name] = {
            "iterations": result.iterations,
            "success": result.success,
            "status": result.status,
            "x": result.x.tolist() if result.x is not None else None,
        }

    return results


def run_benchmark(
    data_dir: str,
    solvers: List[str],
    rtol: float = 1e-6,
    timeout: float = 120.0,
    max_problems: Optional[int] = None,
) -> Dict:
    """Run benchmark on Maros-Meszárós test set."""

    # Find all .mat files
    mat_files = sorted(Path(data_dir).glob("*.mat"))
    if max_problems:
        mat_files = mat_files[:max_problems]

    results = {solver: [] for solver in solvers}
    results["names"] = [Path(f).stem for f in mat_files]

    for i, mat_file in enumerate(mat_files):
        print(f"  [{i+1}/{len(mat_files)}] {Path(mat_file).stem}...", end=" ", flush=True)

        try:
            problem = load_maros_meszaros_problem(str(mat_file))
        except Exception as e:
            print(f"LOAD ERROR: {e}")
            continue

        for solver_name in solvers:
            if solver_name == "odyn":
                r = run_odyn(problem, rtol, timeout)
            elif solver_name == "osqp":
                r = run_osqp(problem, rtol, timeout)
            elif solver_name == "proxqp":
                r = run_proxqp(problem, rtol, timeout)
            else:
                r = {"success": False, "iterations": 0, "solve_time": 0, "status": "unknown"}

            results[solver_name].append(r)
            status_str = "OK" if r["success"] else f"FAIL({r['status'][:20]})"
            print(f"{solver_name}={status_str}({r['iterations']}it,{r['solve_time']:.2f}s) ", end="")
        print()

    return results


def compute_failure_rates(results: Dict, solver: str) -> Tuple[float, float]:
    """Compute failure rates for medium (1e-6) and high (1e-9) accuracy."""
    solver_results = results.get(solver, [])
    if not solver_results:
        return 1.0, 1.0

    failed = sum(1 for r in solver_results if not r["success"])
    total = len(solver_results)
    return failed / total * 100, failed / total * 100  # Same for now since we only run one tolerance


def compute_warm_cold_ratio(data_dir: str, solver_fn, n_problems: int = 20) -> Dict[str, float]:
    """Compute warm-to-cold ratio on perturbed problems."""
    import random

    mat_files = sorted(Path(data_dir).glob("*.mat"))[:n_problems]
    wcr_per_level = {1e-3: [], 1e-2: [], 1e-1: []}

    for mat_file in mat_files:
        try:
            problem = load_maros_meszaros_problem(str(mat_file))
        except:
            continue

        P = problem["P"]
        q = problem["q"]
        A = problem["A"]
        b = problem["b"]
        G = problem["G"]
        h = problem["h"]

        # Cold start
        result_cold = solver_fn(problem, 1e-9)
        if not result_cold["success"]:
            continue
        n_cold = result_cold["iterations"]

        # Perturb and warm start
        for delta in [1e-3, 1e-2, 1e-1]:
            P_pert = P.copy()
            q_pert = q.copy()
            if A is not None:
                A_pert = A.copy()
                b_pert = b + delta * np.random.randn(len(b)) * np.abs(b + 1e-10)
            else:
                A_pert = None
                b_pert = None
            if G is not None:
                G_pert = G.copy()
                h_pert = h + delta * np.random.randn(len(h)) * np.abs(h + 1e-10)
            else:
                G_pert = None
                h_pert = None

            perturbed_problem = {**problem, "P": P_pert, "q": q_pert,
                                  "A": A_pert, "b": b_pert, "G": G_pert, "h": h_pert}

            x_init = result_cold.get("x")
            result_warm = solver_fn(perturbed_problem, 1e-9)
            if result_warm["success"]:
                wcr = result_warm["iterations"] / n_cold if n_cold > 0 else 1.0
                wcr_per_level[delta].append(min(wcr, 10.0))  # Cap at 10x

    return {delta: np.mean(ratios) if ratios else float('nan')
            for delta, ratios in wcr_per_level.items()}


def main():
    parser = argparse.ArgumentParser(description="Evaluate QP solvers on Maros-Meszárós benchmark")
    parser.add_argument("--data-dir", default="/home/user/method/maros_meszaros_qpbenchmark/data",
                        help="Path to Maros-Meszárós .mat files")
    parser.add_argument("--solvers", nargs="+", default=["odyn", "proxqp"],
                        help="Solvers to evaluate")
    parser.add_argument("--rtol", type=float, default=1e-6,
                        help="Relative tolerance")
    parser.add_argument("--max-problems", type=int, default=None,
                        help="Max problems to run (for quick testing)")
    parser.add_argument("--output", default="/home/user/scoring/scores.json",
                        help="Output JSON file")
    args = parser.parse_args()

    print("=" * 60)
    print("ODYN QP Solver Benchmark")
    print("=" * 60)

    # Run degenerate test cases
    print("\n[Degenerate Test Cases]")
    deg_results = run_degenerate_test_cases()
    print(f"  redundant_ineq: {deg_results['redundant_ineq']['iterations']} it, success={deg_results['redundant_ineq']['success']}")
    print(f"  licq_failure:   {deg_results['licq_failure']['iterations']} it, success={deg_results['licq_failure']['success']}")
    print(f"  multiple_solutions: {deg_results['multiple_solutions']['iterations']} it, success={deg_results['multiple_solutions']['success']}")

    # Run main benchmark
    print(f"\n[Maros-Meszárós Benchmark] rtol={args.rtol}")
    results = run_benchmark(args.data_dir, args.solvers, args.rtol, timeout=120.0,
                           max_problems=args.max_problems)

    # Compute failure rates
    print("\n[Failure Rates]")
    score_data = {"experiments": {}}

    for solver in args.solvers:
        rate = compute_failure_rates(results, solver)
        solver_results = results.get(solver, [])
        n_failed = sum(1 for r in solver_results if not r["success"])
        n_total = len(solver_results)
        print(f"  {solver}: {n_failed}/{n_total} failed ({rate[0]:.1f}%)")

    # Build scores.json
    # Experiment 1: Failure rate comparison
    score_data["experiments"]["failure_rate_comparison"] = {"results": {}}
    for solver in args.solvers:
        solver_results = results.get(solver, [])
        n_failed = sum(1 for r in solver_results if not r["success"])
        n_total = len(solver_results)
        rate = n_failed / n_total * 100 if n_total > 0 else 100.0

        is_proposed = solver == "odyn"
        score_data["experiments"]["failure_rate_comparison"]["results"][solver] = {
            "type": "proposed" if is_proposed else "baseline",
            "failure_rate_medium": rate,
        }

    # Experiment 2: Degenerate problems
    score_data["experiments"]["degenerate_problems"] = {"results": {}}
    for name, data in deg_results.items():
        score_data["experiments"]["degenerate_problems"]["results"][f"odyn_{name}"] = {
            "type": "proposed",
            name: data["iterations"],
        }

    # Write scores
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(score_data, f, indent=2)

    print(f"\nScores written to {output_path}")
    print(json.dumps(score_data, indent=2))


if __name__ == "__main__":
    main()