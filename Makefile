# Copyright (C) 2026 Josue David (gidanodfu)
# https://github.com/gidanodfu/AGANT
.PHONY: setup data features train test test-py test-js run bench docker all

setup:
	bash scripts/setup_env.sh

data:
	.venv/bin/python scripts/download_paysim.py
	.venv/bin/python scripts/prepare_paysim.py

features:
	.venv/bin/python scripts/prepare_features.py

train:
	.venv/bin/python scripts/train.py
	.venv/bin/python scripts/thresholds.py
	.venv/bin/python scripts/evaluate_variants.py
	.venv/bin/python scripts/baselines.py

test-py:
	.venv/bin/python -m pytest

test-js:
	cd frontend && npm test

test: test-py test-js

run:
	.venv/bin/uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port 8000

bench:
	.venv/bin/python scripts/benchmark_e2e.py --records 3000 --batch 32

docker:
	docker compose up --build

all: setup data features train bench
