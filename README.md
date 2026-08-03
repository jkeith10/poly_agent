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

The repository contains a runnable vertical slice: live Polymarket discovery, symmetric source research, structured AI debate, Bayesian updating with dependence discounts, cost-aware expected-value recommendations, persistent portfolios and resolutions, calibration scoring, notification adapters, background ingestion, and a live dashboard.

## Run locally

Copy `.env.example` to `.env`, replace the development credentials, and start the stack. The migration service upgrades PostgreSQL before the API, worker, and scheduler start:

```bash
docker compose up --build
```

The dashboard is served at `http://localhost:3000`, the API at `http://localhost:8000`, and interactive API documentation at `http://localhost:8000/docs`.

Set `ORACLE_ADMIN_API_KEYS` to a JSON list of high-entropy bearer tokens before exposing the API. Production configuration refuses to start without at least one administrative key. Market scans and analysis creation require this credential; read-only market and recommendation endpoints remain separately cacheable.

AI research remains disabled unless `ORACLE_AI_API_KEY`, `ORACLE_AI_MODEL`, and `ORACLE_SEARCH_API_KEY` are all configured. Research retrieves both sides independently, rejects private-network source URLs, validates structured model output, and persists cited findings.

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
