# ORACLE

ORACLE is an AI-powered prediction-market intelligence platform designed to identify positive expected-value opportunities while preserving uncertainty, provenance, and auditability.

This repository is organized as a modular monorepo. Runtime applications are isolated from reusable domain packages, deployment assets, and cross-cutting documentation.

## Repository layout

```text
apps/          Deployable API, worker, and dashboard applications
packages/      Python domain and infrastructure packages
tests/         Cross-package integration, contract, and end-to-end tests
deploy/        Local and hosted deployment definitions
docs/          Architecture decisions and operational documentation
scripts/       Repository automation entry points
```

The repository contains a runnable vertical slice: live Polymarket discovery, structured evidence inputs, Bayesian updating with dependence discounts, cost-aware expected-value recommendations, portfolio and calibration metrics, alert policy, persistence models, background ingestion, and the dashboard.

## Run locally

Copy `.env.example` to `.env`, replace the development credentials, and start the stack:

```bash
docker compose up --build
```

The dashboard is served at `http://localhost:3000`, the API at `http://localhost:8000`, and interactive API documentation at `http://localhost:8000/docs`.

## Safety model

ORACLE supplies probabilistic decision support and never guarantees outcomes. AI debate outputs are strict, citation-bearing JSON; deterministic services own Bayesian updates, expected-value calculations, position limits, and alert thresholds. Autonomous trade execution is intentionally outside the system boundary.

## Development checks

```bash
python -m pip install -e '.[dev]'
pytest
ruff check .
mypy packages apps/api apps/worker
npm --prefix apps/dashboard install
npm --prefix apps/dashboard run build
```
