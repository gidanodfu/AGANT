# AGANT — Detección híbrida de fraude financiero (reglas + ML + grafo + Laya).
# Copyright (C) 2026 Josue David (gidanodfu)
# https://github.com/gidanodfu/AGANT
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
.PHONY: setup data features train test test-py test-js run bench docker all

setup:
	bash scripts/setup_env.sh

data:
	.venv/bin/python scripts/download_paysim.py
	.venv/bin/python scripts/prepare_paysim.py

features:
	.venv/bin/python scripts/prepare_features.py

train:
	.venv/bin/python scripts/model_selection.py
	.venv/bin/python scripts/train.py
	.venv/bin/python scripts/thresholds.py
	.venv/bin/python scripts/evaluate_variants.py
	.venv/bin/python scripts/baselines.py
	.venv/bin/python scripts/confidence_intervals.py

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
