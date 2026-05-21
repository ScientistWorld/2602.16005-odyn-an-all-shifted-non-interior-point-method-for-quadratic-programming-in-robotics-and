"""
ODYN: All-Shifted Non-Interior-Point QP Solver

Implementation based on the paper:
"ODYN: An All-Shifted Non-Interior-Point Method for Quadratic Programming
in Robotics and AI" (arXiv:2602.16005)

This is a Python implementation of the ODYN QP solver algorithm.
The paper uses a C++ implementation with EIGEN; this Python version
implements the same algorithm for benchmarking purposes.

Key features:
- All-shifted NCP functions for degeneracy robustness
- Proximal primal-dual regularization
- Condensed KKT system with Cholesky factorization
- Adaptive centering and step-length parameters
- Warm-start support
- Dense and sparse backends
"""

import numpy as np
import scipy.sparse as spa
from typing import Optional, Tuple, Dict, Any
from dataclasses import dataclass, field


def _inf_norm(arr):
    """Infinity norm with empty-array guard."""
    return np.linalg.norm(arr, np.inf) if arr.size > 0 else 0.0


def _hard_threshold(value: float, threshold: float) -> float:
    """Apply the paper's threshold operator T(x; t)."""
    return 0.0 if value < threshold else value


@dataclass
class OdynParams:
    """ODYN hyperparameters. Defaults from Table II of the paper (double precision)."""
    # Neighborhood parameters
    beta: float = 0.85
    theta_n: float = 0.95

    # Centering parameters
    sigma_min: float = 0.1
    sigma_max: float = 0.9
    mu_min: float = 1e-16

    # Step-length interpolation parameters
    theta_min: float = 0.1
    theta_l: float = 0.3  # lower improvement threshold
    theta_u: float = 0.85  # upper improvement threshold
    theta_minus: float = 0.4  # decrease factor
    theta_plus: float = 0.3  # increase factor

    # Proximal penalty parameters
    rho: float = 1e-9
    rho_min: float = 1e-9
    delta: float = 5.0  # regularization decreasing factor

    # Line search parameter
    eta: float = 1e-2

    # Merit function reference multiplier in the relaxed Armijo condition.
    gamma: float = 1.0

    # Max iterations
    max_iter: int = 200

    # Numerical safeguards for the condensed dense solve. The paper's C++
    # implementation uses Eigen factorizations; this Python reproduction uses
    # explicit dense matrices, so we allow a few diagonal-regularized Cholesky
    # retries before declaring numerical failure.
    max_factorization_retries: int = 8
    regularization_floor: float = 1e-12

    @classmethod
    def single_precision(cls):
        """Single precision settings: increase rho and mu_min by 10^4."""
        p = cls()
        p.rho = 1e-5
        p.rho_min = 1e-5
        p.mu_min = 1e-12
        return p


@dataclass
class OdynResult:
    """Result of solving a QP with ODYN."""
    x: np.ndarray
    y: Optional[np.ndarray] = None  # equality multipliers
    z: Optional[np.ndarray] = None  # inequality multipliers
    success: bool = False
    iterations: int = 0
    solve_time: float = 0.0
    status: str = ""
    # KKT residuals at solution
    primal_residual: float = 0.0
    dual_residual: float = 0.0
    infeasibility: float = 0.0

    @property
    def optimality_error(self) -> float:
        return max(self.primal_residual, self.dual_residual, self.infeasibility)


class DenseOdynSolver:
    """
    Dense backend for ODYN QP solver.

    Solves: min (1/2) x^T Q x + c^T x
            s.t. A x = b
                 G x <= h
    """

    def __init__(self, params: Optional[OdynParams] = None, verbose: bool = False):
        self.params = params or OdynParams()
        self.verbose = verbose
        self._iteration_history = []

    def solve(
        self,
        Q: np.ndarray,
        c: np.ndarray,
        A: Optional[np.ndarray],
        b: Optional[np.ndarray],
        G: Optional[np.ndarray],
        h: Optional[np.ndarray],
        x_init: Optional[np.ndarray] = None,
        y_init: Optional[np.ndarray] = None,
        z_init: Optional[np.ndarray] = None,
        rtol: float = 1e-6,
        atol: float = 1e-10,
    ) -> OdynResult:
        """
        Solve a QP problem.

        Args:
            Q: (n, n) symmetric positive semidefinite cost matrix
            c: (n,) linear cost vector
            A: (m, n) equality constraint matrix (or None)
            b: (m,) equality constraint RHS (or None)
            G: (p, n) inequality constraint matrix (or None)
            h: (p,) inequality constraint RHS (or None)
            x_init: warm-start initial x
            y_init: warm-start initial equality multipliers
            z_init: warm-start initial inequality multipliers
            rtol: relative tolerance
            atol: absolute tolerance

        Returns:
            OdynResult with solution and statistics
        """
        import time
        t0 = time.time()

        n = Q.shape[0]
        m = A.shape[0] if A is not None and A.size > 0 else 0
        p = G.shape[0] if G is not None and G.size > 0 else 0

        # Initialize primal and dual variables
        x = x_init.copy() if x_init is not None else np.zeros(n)
        y = y_init.copy() if y_init is not None else np.zeros(m)
        z = z_init.copy() if z_init is not None else np.zeros(p)

        # Slack variables for Gx + s = h, s >= 0.
        s = np.maximum(h - G @ x, 1e-8) if p > 0 else np.array([])

        # Proximal estimates (initially equal to current iterate)
        x_E = x.copy()
        y_E = y.copy()
        z_E = z.copy()
        s_E = s.copy() if p > 0 else np.array([])

        # Regularization parameters
        rho_d = self.params.rho
        rho_e = self.params.rho
        rho_i = self.params.rho
        rho_n = self.params.rho

        # Centering parameters
        sigma = 0.5  # initial centering
        mu = 1.0  # initial barrier

        # Step-length interpolation parameters
        theta_d = 1.0
        theta_p = 1.0

        # Stack constraint matrices
        if A is not None and A.size > 0:
            J = np.vstack([A, G]) if G is not None and G.size > 0 else A
        elif G is not None and G.size > 0:
            J = G
        else:
            J = np.zeros((0, n))

        # Precompute D^{-1} block structure
        m_eq = m
        m_ineq = p

        # Build matrices needed for condensed system
        # D_block for equality: rho_e * I
        # D_block for inequality: P + rho_i * I (to be computed)
        # P = Phi_s^{-1} * Phi_z

        # NCP function and its derivatives
        def ncp_function(s: np.ndarray, z: np.ndarray, mu: float) -> np.ndarray:
            """Smoothed minimum NCP function: phi(s, z; mu) = s + z - sqrt((s-z)^2 + 4*mu)"""
            delta_sz = s - z
            # Clamp to prevent overflow in sqrt
            inside = np.clip(delta_sz ** 2 + 4 * mu, 0, 1e30)
            return s + z - np.sqrt(inside)

        def ncp_jacobians(s: np.ndarray, z: np.ndarray, mu: float) -> Tuple[np.ndarray, np.ndarray]:
            """
            Jacobians of the NCP function w.r.t. s and z.
            Phi_s = diag(1 - (s-z) / sqrt((s-z)^2 + 4*mu))
            Phi_z = diag(1 + (s-z) / sqrt((s-z)^2 + 4*mu))
            """
            delta_sz = s - z
            inside = np.clip(delta_sz ** 2 + 4 * mu, 1e-20, 1e30)
            denom = np.sqrt(inside)
            safe_delta = np.clip(delta_sz, -1e15, 1e15)
            Phi_s = np.diag(1.0 - safe_delta / denom)
            Phi_z = np.diag(1.0 + safe_delta / denom)
            return Phi_s, Phi_z

        def compute_residuals(x, s, y, z):
            """Compute all KKT residuals."""
            # Dual residual
            r_d = Q @ x + c
            if A is not None and A.size > 0:
                r_d = r_d + A.T @ y
            if G is not None and G.size > 0:
                r_d = r_d + G.T @ z
            r_d = r_d + rho_d * (x - x_E)

            # Equality residual
            r_eq = np.zeros(m)
            if A is not None and A.size > 0:
                r_eq = A @ x - b - rho_e * (y - y_E)

            # Inequality residual
            r_i = np.zeros(p)
            if G is not None and G.size > 0:
                r_i = G @ x + s - h - rho_i * (z - z_E)

            # NCP complementarity residual
            r_g = np.zeros(p)
            if p > 0:
                phi = ncp_function(s, z, mu)
                r_g = phi + rho_n * (s - s_E) + rho_n * (z - z_E)

            return r_d, r_eq, r_i, r_g

        def compute_merit(x, s, y, z):
            """Natural merit function M(U) = 0.5 * (r_d^T r_d + r_p^T r_p + r_g^T r_g)"""
            r_d, r_eq, r_i, r_g = compute_residuals(x, s, y, z)
            r_p = np.concatenate([r_eq, r_i])
            return 0.5 * (np.dot(r_d, r_d) + np.dot(r_p, r_p) + np.dot(r_g, r_g))

        def residual_summary(r_d, r_eq, r_i, r_g):
            """Per-residual infinity norms used by ODYN's update rules."""
            r_p = np.concatenate([r_eq, r_i]) if (r_eq.size or r_i.size) else np.array([])
            return {
                "dual": _inf_norm(r_d),
                "primal": _inf_norm(r_p),
                "ncp": _inf_norm(r_g),
                "all": _inf_norm(np.concatenate([r_d, r_eq, r_i, r_g])),
            }

        # Warm-start: adjust regularization if needed
        if x_init is not None:
            # Reduce regularization for warm-start
            rho_d *= 0.1
            rho_e *= 0.1
            rho_i *= 0.1

        status = "optimal"
        iterations = 0

        for iteration in range(self.params.max_iter):
            iterations += 1
            self._iteration_history.append({})

            # Compute residuals
            r_d, r_eq, r_i, r_g = compute_residuals(x, s, y, z)

            # Check stopping criteria
            def compute_scale(x, c, y, z):
                """Compute scaling factors for relative tolerance."""
                scales = [np.linalg.norm(Q @ x, np.inf), np.linalg.norm(c, np.inf)]
                if A is not None and A.size > 0:
                    scales.append(np.linalg.norm(A.T @ y, np.inf))
                if G is not None and G.size > 0:
                    scales.append(np.linalg.norm(G.T @ z, np.inf))
                return max(*scales, 1e-10)

            scale_d = compute_scale(x, c, y, z)
            scale_eq = _inf_norm(b) if b is not None and b.size > 0 else 1.0
            scale_i = max(
                np.linalg.norm(G @ x, np.inf) if G is not None and G.size > 0 else 0,
                np.linalg.norm(s, np.inf) if s.size > 0 else 0,
                np.linalg.norm(h, np.inf) if h is not None and np.size(h) > 0 else 0
            )
            scale_n = max(
                np.linalg.norm(s, np.inf) if s.size > 0 else 0,
                np.linalg.norm(z, np.inf) if z.size > 0 else 0,
                np.linalg.norm(r_g, np.inf) if r_g.size > 0 else 0
            )

            # Dual infeasibility: min(s, z)
            r_n = np.minimum(s, z) if p > 0 else np.array([])

            def _norm(arr, scale=1.0):
                if arr.size == 0:
                    return 0.0
                return np.linalg.norm(arr, np.inf)

            if (_norm(r_d) <= atol + rtol * scale_d and
                _norm(r_eq) <= atol + rtol * max(scale_eq, 1.0) and
                (p == 0 or _norm(r_i) <= atol + rtol * scale_i) and
                (p == 0 or _norm(r_n) <= atol + rtol * max(scale_n, 1e-3))):
                status = "optimal"
                break

            # Compute NCP Jacobians
            if p > 0:
                Phi_s, Phi_z = ncp_jacobians(s, z, mu)
            else:
                Phi_s = np.zeros((0, 0))
                Phi_z = np.zeros((0, 0))

            # Regularized Jacobians
            tPhi_s = Phi_s + rho_n * np.eye(p) if p > 0 else np.zeros((0, 0))
            tPhi_z = Phi_z + rho_n * np.eye(p) if p > 0 else np.zeros((0, 0))

            # Compute diagonal matrix P = (Phi_s + rho_n I)^{-1} (Phi_z + rho_n I)
            # and q = (Phi_s + rho_n I)^{-1} r_g used by the condensed system.
            if p > 0:
                tPhi_s_diag = np.diag(tPhi_s)
                tPhi_z_diag = np.diag(tPhi_z)
                P_diag = tPhi_z_diag / (tPhi_s_diag + 1e-20)
                P_diag = np.clip(P_diag, 1e-12, 1e12)
                q_shift = r_g / (tPhi_s_diag + 1e-20)
            else:
                P_diag = np.array([])
                q_shift = np.array([])

            # Build D matrix: D = diag(rho_e * I_eq, (P + rho_i*I)_ineq)
            D_diag = np.concatenate([
                rho_e * np.ones(m_eq),
                P_diag + rho_i
            ]) if p > 0 else rho_e * np.ones(m_eq)

            if not np.all(np.isfinite(D_diag)) or np.any(D_diag <= 0):
                status = "numerical_error"
                break
            D_inv = 1.0 / D_diag

            # Build J matrix: J = [A; G]
            if m > 0 and p > 0:
                J_mat = np.vstack([A, G])
            elif m > 0:
                J_mat = A
            elif p > 0:
                J_mat = G
            else:
                J_mat = np.zeros((0, n))

            # Condensed Hessian: H = Q + J^T * D^{-1} * J
            # For numerical stability, add small regularization
            J_D = J_mat * D_inv[:, np.newaxis]
            H = Q + J_mat.T @ J_D
            # Ensure symmetry
            H = 0.5 * (H + H.T)
            # Add proximal term
            H = H + rho_d * np.eye(n)

            if not np.all(np.isfinite(H)):
                status = "numerical_error"
                break

            # Right-hand side
            shifted_primal = np.concatenate([r_eq, r_i - q_shift]) if (m + p) > 0 else np.array([])
            if m + p > 0:
                rhs_d = -r_d - J_mat.T @ (D_inv * shifted_primal)
            else:
                rhs_d = -r_d

            # Handle NaN/Inf in RHS
            if not np.all(np.isfinite(rhs_d)):
                status = "numerical_error"
                break

            # Solve H * delta_x = rhs_d via Cholesky with escalating diagonal
            # regularization. This keeps the condensed ODYN step intact while
            # avoiding early failure from tiny negative pivots in dense Python
            # linear algebra.
            from scipy.linalg import solve_triangular
            delta_x = None
            eye_n = np.eye(n)
            base_reg = max(self.params.regularization_floor, rho_d)
            try:
                for pd_attempt in range(self.params.max_factorization_retries):
                    reg = 0.0 if pd_attempt == 0 else base_reg * (10.0 ** pd_attempt)
                    H_reg = H if reg == 0.0 else H + reg * eye_n
                    try:
                        L = np.linalg.cholesky(H_reg)
                        candidate = solve_triangular(L, rhs_d, lower=True, check_finite=False)
                        candidate = solve_triangular(L.T, candidate, check_finite=False)
                    except np.linalg.LinAlgError:
                        continue
                    if np.all(np.isfinite(candidate)):
                        delta_x = candidate
                        break
                if delta_x is None:
                    H_reg = H + base_reg * (10.0 ** self.params.max_factorization_retries) * eye_n
                    candidate = np.linalg.lstsq(H_reg, rhs_d, rcond=1e-10)[0]
                    if np.all(np.isfinite(candidate)):
                        delta_x = candidate
            except Exception:
                delta_x = None

            if delta_x is None:
                status = "numerical_error"
                break

            # Compute delta_lambda = D^{-1} * (J * delta_x + shifted residuals)
            delta_lambda_full = D_inv * (J_mat @ delta_x + shifted_primal)
            if not np.all(np.isfinite(delta_lambda_full)):
                status = "numerical_error"
                break

            if m > 0 and p > 0:
                delta_y = delta_lambda_full[:m]
                delta_z = delta_lambda_full[m:]
            elif m > 0:
                delta_y = delta_lambda_full
                delta_z = np.array([])
            elif p > 0:
                delta_y = np.array([])
                delta_z = delta_lambda_full
            else:
                delta_y = np.array([])
                delta_z = np.array([])

            # Compute delta_s from: r_g + Phi_s * delta_s + rho_n*delta_s + Phi_z * delta_z + rho_n*delta_z = 0
            # => delta_s = -(r_g + Phi_z * delta_z + rho_n*(delta_z + s - s_E)) / (Phi_s + rho_n*I)
            if p > 0:
                delta_s = -q_shift - P_diag * delta_z
            else:
                delta_s = np.array([])
            if not np.all(np.isfinite(delta_s)):
                status = "numerical_error"
                break

            # Line search
            alpha = 1.0
            M_current = compute_merit(x, s, y, z)

            # Compute directional derivative of merit
            r_d_next, _, _, r_g_next = compute_residuals(
                x + delta_x, s + delta_s, y + delta_y, z + delta_z
            )
            delta_res_d = r_d_next - r_d
            delta_res_g = r_g_next - r_g

            # Merit function directional derivative
            # dM = grad(M) @ delta_U
            # Simplified: just use norm reduction
            dM = np.dot(r_d, delta_res_d) + np.dot(r_g, delta_res_g)
            if m > 0 or p > 0:
                r_p = np.concatenate([r_eq, r_i])
                delta_res_p = J_mat @ delta_x
                dM += np.dot(r_p, delta_res_p)

            # Backtracking line search
            for ls_iter in range(20):
                x_new = x + alpha * delta_x
                s_new = s + alpha * delta_s if p > 0 else s
                y_new = y + alpha * delta_y if m > 0 else y
                z_new = z + alpha * delta_z if p > 0 else z

                M_new = compute_merit(x_new, s_new, y_new, z_new)
                if M_new <= self.params.gamma * M_current + alpha * self.params.eta * dM:
                    break
                alpha *= 0.5

            if alpha < 1e-10:
                status = "stalled"
                break

            # Save previous iterates for the proximal estimate interpolation.
            x_prev = x.copy()
            y_prev = y.copy()
            z_prev = z.copy()
            s_prev = s.copy()

            # Update iterates
            x = x_new
            s = s_new
            y = y_new
            z = z_new

            old_mu = mu
            r_d_new, r_eq_new, r_i_new, r_g_new = compute_residuals(x, s, y, z)
            old_stats = residual_summary(r_d, r_eq, r_i, r_g)
            new_stats = residual_summary(r_d_new, r_eq_new, r_i_new, r_g_new)

            # Relaxed neighborhood condition from Eq. (51). ODYN updates the
            # centering, interpolation, and proximal references only after an
            # accepted step lands inside this neighborhood.
            neighborhood_ok = (
                new_stats["all"] <= self.params.theta_n * old_stats["all"] + self.params.beta * old_mu
            )

            if neighborhood_ok:
                mu_pred = np.sum(np.minimum(s, z) ** 2) / max(p, 1) if p > 0 else 0.0
                mu = max(self.params.mu_min, sigma * mu_pred)
                if old_stats["all"] > 0 and new_stats["all"] <= self.params.theta_u * old_stats["all"]:
                    sigma = max(self.params.sigma_min, sigma - self.params.theta_minus * sigma)
                else:
                    sigma = min(self.params.sigma_max, sigma + self.params.theta_plus * (1 - sigma))
                    mu = min(mu, old_mu)

                if old_stats["dual"] > 0 and new_stats["dual"] <= self.params.theta_l * old_stats["dual"]:
                    theta_d = _hard_threshold(
                        max(0.0, theta_d - self.params.theta_minus * theta_d),
                        self.params.theta_min,
                    )
                    rho_d = max(self.params.rho_min, rho_d / self.params.delta)
                elif old_stats["dual"] > 0 and new_stats["dual"] >= self.params.theta_u * old_stats["dual"]:
                    theta_d = min(1.0, theta_d + self.params.theta_plus * (1.0 - theta_d))

                if old_stats["primal"] > 0 and new_stats["primal"] <= self.params.theta_l * old_stats["primal"]:
                    theta_p = _hard_threshold(
                        max(0.0, theta_p - self.params.theta_minus * theta_p),
                        self.params.theta_min,
                    )
                    rho_e = max(self.params.rho_min, rho_e / self.params.delta)
                    rho_i = max(self.params.rho_min, rho_i / self.params.delta)
                elif old_stats["primal"] > 0 and new_stats["primal"] >= self.params.theta_u * old_stats["primal"]:
                    theta_p = min(1.0, theta_p + self.params.theta_plus * (1.0 - theta_p))

                if old_stats["ncp"] > 0 and new_stats["ncp"] <= self.params.theta_l * old_stats["ncp"]:
                    rho_n = max(self.params.rho_min, rho_n / self.params.delta)

                # Proximal estimate update from Eq. (48).
                x_E = x + theta_d * (x_prev - x)
                y_E = y + theta_p * (y_prev - y)
                z_E = z + theta_p * (z_prev - z)
                s_E = s + theta_p * (s_prev - s)
            else:
                sigma = min(self.params.sigma_max, sigma + self.params.theta_plus * (1 - sigma))
                mu = old_mu

            # Per-iteration diagnostics
            self._iteration_history[-1].update({
                'iteration': iteration,
                'alpha': alpha,
                'mu': mu,
                'sigma': sigma,
                'rho_d': rho_d,
                'theta_d': theta_d,
                'r_norm': _inf_norm(r_d),
                'merit': M_current,
            })

        else:
            status = "max_iterations"

        solve_time = time.time() - t0

        # Compute final residuals for result
        r_d, r_eq, r_i, r_g = compute_residuals(x, s, y, z)
        r_n = np.minimum(s, z) if p > 0 else np.array([])

        return OdynResult(
            x=x,
            y=y if m > 0 else None,
            z=z if p > 0 else None,
            success=(status == "optimal"),
            iterations=iterations,
            solve_time=solve_time,
            status=status,
            primal_residual=max(_inf_norm(r_eq), _inf_norm(r_i)),
            dual_residual=_inf_norm(r_d),
            infeasibility=np.linalg.norm(r_n, np.inf) if p > 0 else 0,
        )


class SparseOdynSolver:
    """
    Sparse backend for ODYN QP solver.
    Uses scipy.sparse matrices for large problems.
    """

    def __init__(self, params: Optional[OdynParams] = None, verbose: bool = False):
        self.params = params or OdynParams()
        self.verbose = verbose

    def solve(
        self,
        Q: spa.csc_matrix,
        c: np.ndarray,
        A: Optional[spa.csc_matrix],
        b: Optional[np.ndarray],
        G: Optional[spa.csc_matrix],
        h: Optional[np.ndarray],
        x_init: Optional[np.ndarray] = None,
        y_init: Optional[np.ndarray] = None,
        z_init: Optional[np.ndarray] = None,
        rtol: float = 1e-6,
        atol: float = 1e-10,
    ) -> OdynResult:
        """
        Solve a sparse QP problem.
        For now, fall back to dense solver for smaller problems.
        """
        # Convert to dense if problem is small enough
        n = Q.shape[0]
        m = A.shape[0] if A is not None and A.size > 0 else 0
        p = G.shape[0] if G is not None and G.size > 0 else 0

        # For small problems, use dense solver
        if n <= 1000 and Q.nnz < n * n * 0.1:
            Q_dense = Q.toarray()
            A_dense = A.toarray() if A is not None and A.size > 0 else None
            G_dense = G.toarray() if G is not None and G.size > 0 else None

            dense_solver = DenseOdynSolver(self.params, self.verbose)
            return dense_solver.solve(
                Q_dense, c, A_dense, b, G_dense, h,
                x_init, y_init, z_init, rtol, atol
            )

        # For larger sparse problems, use sparse linear algebra
        return self._solve_sparse(
            Q, c, A, b, G, h,
            x_init, y_init, z_init, rtol, atol
        )

    def _solve_sparse(
        self,
        Q: spa.csc_matrix,
        c: np.ndarray,
        A: Optional[spa.csc_matrix],
        b: Optional[np.ndarray],
        G: Optional[spa.csc_matrix],
        h: Optional[np.ndarray],
        x_init: Optional[np.ndarray],
        y_init: Optional[np.ndarray],
        z_init: Optional[np.ndarray],
        rtol: float,
        atol: float,
    ) -> OdynResult:
        """Sparse implementation of ODYN."""
        import time
        t0 = time.time()

        n = Q.shape[0]
        m = A.shape[0] if A is not None and A.size > 0 else 0
        p = G.shape[0] if G is not None and G.size > 0 else 0

        # Initialize
        x = x_init.copy() if x_init is not None else np.zeros(n)
        y = y_init.copy() if y_init is not None else np.zeros(m)
        z = z_init.copy() if z_init is not None else np.zeros(p)

        # Slack for Gx + s = h, s >= 0.
        if p > 0:
            Gx = G @ x
            s = np.maximum(h - Gx, 1e-8)
        else:
            s = np.array([])

        # Proximal estimates
        x_E = x.copy()
        y_E = y.copy()
        z_E = z.copy()
        s_E = s.copy() if p > 0 else np.array([])

        # Parameters
        rho_d = self.params.rho
        rho_e = self.params.rho
        rho_i = self.params.rho
        rho_n = self.params.rho

        sigma = 0.5
        mu = 1.0

        theta_d = 1.0
        theta_p = 1.0

        def ncp_function(s, z, mu):
            delta = s - z
            return s + z - np.sqrt(delta ** 2 + 4 * mu)

        def ncp_jacobians(s, z, mu):
            delta = s - z
            denom = np.sqrt(delta ** 2 + 4 * mu)
            # For efficiency, compute diagonal entries directly
            Phi_s_diag = 1.0 - delta / denom
            Phi_z_diag = 1.0 + delta / denom
            return Phi_s_diag, Phi_z_diag

        def residuals(x, s, y, z):
            r_d = Q @ x + c
            if m > 0:
                r_d = r_d + A.T @ y
            if p > 0:
                r_d = r_d + G.T @ z
            r_d = r_d + rho_d * (x - x_E)

            r_eq = np.zeros(m)
            if m > 0:
                r_eq = A @ x - b - rho_e * (y - y_E)

            r_i = np.zeros(p)
            if p > 0:
                r_i = G @ x + s - h - rho_i * (z - z_E)

            r_g = np.zeros(p)
            if p > 0:
                phi = ncp_function(s, z, mu)
                r_g = phi + rho_n * (s - s_E) + rho_n * (z - z_E)

            return r_d, r_eq, r_i, r_g

        def residual_summary(r_d, r_eq, r_i, r_g):
            r_p = np.concatenate([r_eq, r_i]) if (r_eq.size or r_i.size) else np.array([])
            return {
                "dual": _inf_norm(r_d),
                "primal": _inf_norm(r_p),
                "ncp": _inf_norm(r_g),
                "all": _inf_norm(np.concatenate([r_d, r_eq, r_i, r_g])),
            }

        status = "optimal"
        iterations = 0

        for iteration in range(self.params.max_iter):
            iterations += 1

            r_d, r_eq, r_i, r_g = residuals(x, s, y, z)

            # Stopping criteria from Eq. (52), matching the dense backend.
            scale_d = max(
                _inf_norm(Q @ x),
                _inf_norm(c),
                _inf_norm(A.T @ y) if m > 0 else 0.0,
                _inf_norm(G.T @ z) if p > 0 else 0.0,
                1e-10,
            )
            scale_eq = max(_inf_norm(A @ x) if m > 0 else 0.0, _inf_norm(b) if b is not None else 0.0, 1.0)
            scale_i = max(
                _inf_norm(G @ x) if p > 0 else 0.0,
                _inf_norm(s),
                _inf_norm(h) if h is not None else 0.0,
            )
            scale_n = max(_inf_norm(s), _inf_norm(z), _inf_norm(r_g), 1e-3)
            if (
                _inf_norm(r_d) <= atol + rtol * scale_d
                and (m == 0 or _inf_norm(r_eq) <= atol + rtol * scale_eq)
                and (p == 0 or _inf_norm(r_i) <= atol + rtol * scale_i)
                and (p == 0 or _inf_norm(np.minimum(s, z)) <= atol + rtol * scale_n)
            ):
                status = "optimal"
                break

            # NCP Jacobians
            if p > 0:
                Phi_s_d, Phi_z_d = ncp_jacobians(s, z, mu)
            else:
                Phi_s_d = np.array([])
                Phi_z_d = np.array([])

            tPhi_s_d = Phi_s_d + rho_n
            tPhi_z_d = Phi_z_d + rho_n

            # Diagonal P matrix
            if p > 0:
                P_d = tPhi_z_d / (tPhi_s_d + 1e-20)
                P_d = np.clip(P_d, 1e-12, 1e12)
                q_shift = r_g / (tPhi_s_d + 1e-20)
            else:
                P_d = np.array([])
                q_shift = np.array([])

            # D diagonal
            D_d = np.concatenate([rho_e * np.ones(m), P_d + rho_i]) if p > 0 else rho_e * np.ones(m)
            D_inv = 1.0 / D_d

            # Build J matrix
            if m > 0 and p > 0:
                J = spa.vstack([A, G], format='csc')
            elif m > 0:
                J = A
            elif p > 0:
                J = G
            else:
                J = spa.csc_matrix((0, n))

            # Condensed Hessian H = Q + J^T D^{-1} J + rho_d I
            J_D = J.multiply(D_inv[:, np.newaxis])
            H = Q + J.T @ J_D + rho_d * spa.eye(n)

            # Right-hand side
            shifted_primal = np.concatenate([r_eq, r_i - q_shift]) if (m + p) > 0 else np.array([])
            rhs_d = -r_d - J.T @ (D_inv * shifted_primal) if (m + p) > 0 else -r_d

            # Solve H * dx = rhs using sparse Cholesky
            try:
                from scipy.sparse.linalg import splu
                H_LT = spa.linalg.factorized(H.tocsc())
                delta_x = H_LT(rhs_d)
            except Exception:
                # Fallback to CG
                from scipy.sparse.linalg import cg
                delta_x, info = cg(H, rhs_d, maxiter=100)
                if info != 0:
                    delta_x = np.zeros(n)

            # delta_lambda
            delta_lam = D_inv * (J @ delta_x + shifted_primal)

            if m > 0 and p > 0:
                delta_y = delta_lam[:m]
                delta_z = delta_lam[m:]
            elif m > 0:
                delta_y = delta_lam
                delta_z = np.array([])
            else:
                delta_y = np.array([])
                delta_z = delta_lam

            # delta_s
            if p > 0:
                delta_s = -q_shift - P_d * delta_z
            else:
                delta_s = np.array([])

            # Line search
            alpha = 1.0
            M_cur = 0.5 * (np.dot(r_d, r_d) + np.dot(r_eq, r_eq) + np.dot(r_i, r_i) + np.dot(r_g, r_g))
            rd_step, req_step, ri_step, rg_step = residuals(
                x + delta_x,
                s + delta_s if p > 0 else s,
                y + delta_y if m > 0 else y,
                z + delta_z if p > 0 else z,
            )
            dM = (
                np.dot(r_d, rd_step - r_d)
                + np.dot(r_eq, req_step - r_eq)
                + np.dot(r_i, ri_step - r_i)
                + np.dot(r_g, rg_step - r_g)
            )

            for ls_iter in range(20):
                xn = x + alpha * delta_x
                sn = s + alpha * delta_s if p > 0 else s
                yn = y + alpha * delta_y if m > 0 else y
                zn = z + alpha * delta_z if p > 0 else z

                rd_n, req_n, ri_n, rg_n = residuals(xn, sn, yn, zn)
                M_n = 0.5 * (np.dot(rd_n, rd_n) + np.dot(req_n, req_n) + np.dot(ri_n, ri_n) + np.dot(rg_n, rg_n))
                if M_n <= self.params.gamma * M_cur + alpha * self.params.eta * dM:
                    break
                alpha *= 0.5

            if alpha < 1e-10:
                status = "stalled"
                break

            x_prev = x.copy()
            y_prev = y.copy()
            z_prev = z.copy()
            s_prev = s.copy()

            x = xn
            s = sn
            y = yn
            z = zn

            old_mu = mu
            rd_new, req_new, ri_new, rg_new = residuals(x, s, y, z)
            old_stats = residual_summary(r_d, r_eq, r_i, r_g)
            new_stats = residual_summary(rd_new, req_new, ri_new, rg_new)
            neighborhood_ok = (
                new_stats["all"] <= self.params.theta_n * old_stats["all"] + self.params.beta * old_mu
            )

            if neighborhood_ok:
                mu_pred = np.sum(np.minimum(s, z) ** 2) / max(p, 1) if p > 0 else 0.0
                mu = max(self.params.mu_min, sigma * mu_pred)
                if old_stats["all"] > 0 and new_stats["all"] <= self.params.theta_u * old_stats["all"]:
                    sigma = max(self.params.sigma_min, sigma - self.params.theta_minus * sigma)
                else:
                    sigma = min(self.params.sigma_max, sigma + self.params.theta_plus * (1.0 - sigma))
                    mu = min(mu, old_mu)

                if old_stats["dual"] > 0 and new_stats["dual"] <= self.params.theta_l * old_stats["dual"]:
                    theta_d = _hard_threshold(
                        max(0.0, theta_d - self.params.theta_minus * theta_d),
                        self.params.theta_min,
                    )
                    rho_d = max(self.params.rho_min, rho_d / self.params.delta)
                elif old_stats["dual"] > 0 and new_stats["dual"] >= self.params.theta_u * old_stats["dual"]:
                    theta_d = min(1.0, theta_d + self.params.theta_plus * (1.0 - theta_d))

                if old_stats["primal"] > 0 and new_stats["primal"] <= self.params.theta_l * old_stats["primal"]:
                    theta_p = _hard_threshold(
                        max(0.0, theta_p - self.params.theta_minus * theta_p),
                        self.params.theta_min,
                    )
                    rho_e = max(self.params.rho_min, rho_e / self.params.delta)
                    rho_i = max(self.params.rho_min, rho_i / self.params.delta)
                elif old_stats["primal"] > 0 and new_stats["primal"] >= self.params.theta_u * old_stats["primal"]:
                    theta_p = min(1.0, theta_p + self.params.theta_plus * (1.0 - theta_p))

                if old_stats["ncp"] > 0 and new_stats["ncp"] <= self.params.theta_l * old_stats["ncp"]:
                    rho_n = max(self.params.rho_min, rho_n / self.params.delta)

                x_E = x + theta_d * (x_prev - x)
                y_E = y + theta_p * (y_prev - y)
                z_E = z + theta_p * (z_prev - z)
                s_E = s + theta_p * (s_prev - s)
            else:
                sigma = min(self.params.sigma_max, sigma + self.params.theta_plus * (1.0 - sigma))
                mu = old_mu

        else:
            status = "max_iterations"

        solve_time = time.time() - t0

        r_d, r_eq, r_i, r_g = residuals(x, s, y, z)

        return OdynResult(
            x=x,
            y=y if m > 0 else None,
            z=z if p > 0 else None,
            success=(status == "optimal"),
            iterations=iterations,
            solve_time=solve_time,
            status=status,
            primal_residual=max(_inf_norm(r_eq), _inf_norm(r_i)),
            dual_residual=_inf_norm(r_d),
            infeasibility=np.linalg.norm(np.minimum(s, z), np.inf) if p > 0 else 0,
        )


def solve_qp(
    Q: np.ndarray,
    c: np.ndarray,
    A: Optional[np.ndarray] = None,
    b: Optional[np.ndarray] = None,
    G: Optional[np.ndarray] = None,
    h: Optional[np.ndarray] = None,
    x0: Optional[np.ndarray] = None,
    y0: Optional[np.ndarray] = None,
    z0: Optional[np.ndarray] = None,
    rtol: float = 1e-6,
    dense: bool = True,
    verbose: bool = False,
) -> OdynResult:
    """
    Convenience function to solve a QP with ODYN.

    Args:
        Q: (n, n) cost matrix
        c: (n,) linear cost
        A: (m, n) equality constraint matrix
        b: (m,) equality RHS
        G: (p, n) inequality constraint matrix
        h: (p,) inequality RHS
        x0, y0, z0: warm-start initializations
        rtol: relative tolerance
        dense: use dense backend (faster for small problems)
        verbose: print iteration info

    Returns:
        OdynResult with solution
    """
    params = OdynParams()

    if dense:
        solver = DenseOdynSolver(params, verbose)
    else:
        solver = SparseOdynSolver(params, verbose)

    return solver.solve(
        Q, c,
        None if A is None or A.size == 0 else A,
        None if b is None else b,
        None if G is None or G.size == 0 else G,
        None if h is None else h,
        x0, y0, z0,
        rtol=rtol
    )
