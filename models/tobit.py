"""Left-censored Gaussian (Tobit) objective for LightGBM.

The winning-price landscape (design Section 8, model 2) observes the clearing
price only on sales; an unsold lead tells us demand stayed below the deepest
reserve it was offered at. Type-I Tobit on the log-price scale:

    y* ~ N(mu(x), sigma^2)          latent log clearing price
    observed y = y*                 if sold
    observed y* < log(floor)        if unsold (left-censored)

Negative log-likelihood per row:
    uncensored:  0.5*((y - mu)/sigma)^2      (+ const)
    censored:    -log Phi((c - mu)/sigma)

Gradients/hessians in mu (lambda = phi(z)/Phi(z), the inverse Mills ratio,
computed in log space for stability; the censored hessian lambda*(z+lambda)
is positive for all z):
    uncensored:  g = (mu - y)/sigma^2,           h = 1/sigma^2
    censored:    g = lambda(z)/sigma,            h = lambda(z)*(z + lambda(z))/sigma^2
                 with z = (c - mu)/sigma

sigma is a single free scalar, profiled in an outer loop: fit trees at fixed
sigma, then re-estimate sigma by minimizing the same likelihood in sigma at
fixed mu, and repeat. tests/test_models.py checks these gradients against
numerical differentiation.
"""
from __future__ import annotations

import numpy as np
from scipy.optimize import minimize_scalar
from scipy.stats import norm

_EPS = 1e-12


def _mills(z: np.ndarray) -> np.ndarray:
    """phi(z)/Phi(z), stable for very negative z (log-space)."""
    return np.exp(norm.logpdf(z) - norm.logcdf(z))


def nll(mu: np.ndarray, y: np.ndarray, censored: np.ndarray, sigma: float) -> float:
    """Mean Tobit negative log-likelihood (y holds the bound c on censored rows)."""
    out = np.empty_like(mu)
    u = ~censored
    out[u] = 0.5 * ((y[u] - mu[u]) / sigma) ** 2 + np.log(sigma)
    out[censored] = -norm.logcdf((y[censored] - mu[censored]) / sigma)
    return float(out.mean())


def gradients(mu: np.ndarray, y: np.ndarray, censored: np.ndarray,
              sigma: float) -> tuple[np.ndarray, np.ndarray]:
    grad = np.empty_like(mu)
    hess = np.empty_like(mu)
    u = ~censored
    grad[u] = (mu[u] - y[u]) / sigma**2
    hess[u] = 1.0 / sigma**2
    z = (y[censored] - mu[censored]) / sigma
    lam = _mills(z)
    grad[censored] = lam / sigma
    hess[censored] = np.maximum(lam * (z + lam), _EPS) / sigma**2
    return grad, hess


def make_objective(y: np.ndarray, censored: np.ndarray, sigma_holder: dict):
    """LightGBM fobj closure; sigma_holder['sigma'] is read live so the outer
    profiling loop can update it between boosting runs."""
    def fobj(preds: np.ndarray, _dataset):
        return gradients(preds, y, censored, sigma_holder["sigma"])
    return fobj


def make_feval(y: np.ndarray, censored: np.ndarray, sigma_holder: dict):
    def feval(preds: np.ndarray, _dataset):
        return "tobit_nll", nll(preds, y, censored, sigma_holder["sigma"]), False
    return feval


def profile_sigma(mu: np.ndarray, y: np.ndarray, censored: np.ndarray) -> float:
    """MLE of sigma at fixed mu (bounded 1-D minimization)."""
    res = minimize_scalar(lambda s: nll(mu, y, censored, s),
                          bounds=(0.05, 5.0), method="bounded")
    return float(res.x)


def truncated_mean(mu: np.ndarray, c: np.ndarray | float, sigma: float) -> np.ndarray:
    """E[y* | y* > c] for a lower-truncated normal: mu + sigma*phi(a)/(1-Phi(a))."""
    a = (np.asarray(c) - mu) / sigma
    return mu + sigma * np.exp(norm.logpdf(a) - norm.logsf(a))
