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

"""Baselines académicos frente al RF online: reglas solas y un GBM.

Uso:  .venv/bin/python scripts/baselines.py

Escribe `results/metrics/baselines.json`. No modifica el modelo servido.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "backend"))

import numpy as np  # noqa: E402
from sklearn.ensemble import HistGradientBoostingClassifier  # noqa: E402

from app.config import get_settings  # noqa: E402
from app.contracts import (  # noqa: E402
    ComponentStatus,
    Decision,
    Evidence,
    GraphAvailability,
    MLResult,
    Transaction,
)
from app.contracts.transaction import GraphContext  # noqa: E402
from app.data.paysim_db import connect  # noqa: E402
from app.data.temporal_split import SplitName  # noqa: E402
from app.decision import FallbackPolicy  # noqa: E402
from app.evidence import RulesEngine  # noqa: E402
from app.features import load_meta, read_artifacts  # noqa: E402
from app.training.metrics import binary_metrics  # noqa: E402
from app.training.train_online import split_mask  # noqa: E402

_RULES_QUERY = """
SELECT row_id, type, amount, nameOrig, oldbalanceOrg, nameDest, isFlaggedFraud
FROM transactions WHERE step > 520 ORDER BY row_id
"""


def _rules_baselines(settings, features, labels, steps) -> dict:
    rules = RulesEngine(settings)
    policy = FallbackPolicy()
    conn = connect(settings)
    rows = conn.execute(_RULES_QUERY).fetchall()
    conn.close()

    by_split: dict[str, dict[str, list]] = {
        SplitName.VALIDATION.value: {"y": [], "fraud": [], "suspicious": []},
        SplitName.TEST.value: {"y": [], "fraud": [], "suspicious": []},
    }
    for row_id, ttype, amount, origin, ob_org, dest, flagged in rows:
        index = int(row_id) - 1
        step = int(steps[index])
        split = SplitName.VALIDATION.value if step <= 631 else SplitName.TEST.value
        vector = features[index]
        context = GraphContext(destination_unique_origins_before=int(vector[12]))
        transaction = Transaction(
            transaction_id=f"R{row_id}",
            step=step,
            type=ttype,
            amount=float(amount),
            name_orig=origin,
            old_balance_org=float(ob_org),
            name_dest=dest,
            old_balance_dest=0.0,
            is_flagged_fraud=bool(flagged),
        )
        rule_results = rules.evaluate(transaction, context)
        evidence = Evidence(
            rules=rule_results,
            ml=MLResult(available=False),
            graph=GraphAvailability(status=ComponentStatus.READY, context=context),
            rule_score=rules.rule_score(rule_results),
        )
        level, _ = policy.level(evidence)
        primary, _ = policy.primary(evidence, level)
        bucket = by_split[split]
        bucket["y"].append(int(labels[index]))
        bucket["fraud"].append(1.0 if primary is Decision.FRAUD else 0.0)
        bucket["suspicious"].append(
            1.0 if primary in (Decision.FRAUD, Decision.SUSPICIOUS) else 0.0
        )

    return {
        split: {
            "fraud_only": binary_metrics(np.array(data["y"]), np.array(data["fraud"]), 0.5),
            "fraud_or_suspicious": binary_metrics(
                np.array(data["y"]), np.array(data["suspicious"]), 0.5
            ),
        }
        for split, data in by_split.items()
    }


def _gbm_baseline(features, labels, steps) -> dict:
    train = split_mask(steps, SplitName.TRAIN)
    x_train = np.asarray(features[train], dtype=np.float32)
    y_train = np.asarray(labels[train], dtype=np.int8)
    model = HistGradientBoostingClassifier(
        max_iter=200, learning_rate=0.1, class_weight="balanced", random_state=42
    )
    start = time.time()
    model.fit(x_train, y_train)
    elapsed = time.time() - start

    result = {"train_seconds": elapsed, "params": {"max_iter": 200, "learning_rate": 0.1}}
    for split in (SplitName.VALIDATION, SplitName.TEST):
        mask = split_mask(steps, split)
        scores = model.predict_proba(np.asarray(features[mask], dtype=np.float32))[:, 1]
        result[split.value] = binary_metrics(np.asarray(labels[mask]), scores, 0.5)

    # El GBM usa class_weight balanceado: sus probabilidades están sesgadas al
    # alza, así que el umbral 0.5 no es comparable. Se selecciona el umbral por
    # F1 en VALIDATION (misma metodología que el RF) y se reporta TEST con él.
    val_mask = split_mask(steps, SplitName.VALIDATION)
    val_scores = model.predict_proba(np.asarray(features[val_mask], dtype=np.float32))[:, 1]
    val_labels = np.asarray(labels[val_mask])
    best_threshold, best_f1 = 0.5, -1.0
    for candidate in np.linspace(0.05, 0.999, 96):
        f1 = binary_metrics(val_labels, val_scores, float(candidate))["f1"]
        if f1 > best_f1:
            best_threshold, best_f1 = round(float(candidate), 4), f1
    test_mask = split_mask(steps, SplitName.TEST)
    test_scores = model.predict_proba(np.asarray(features[test_mask], dtype=np.float32))[:, 1]
    result["best_threshold_validation"] = best_threshold
    result["test_at_best_threshold"] = binary_metrics(
        np.asarray(labels[test_mask]), test_scores, best_threshold
    )
    return result


def main() -> int:
    settings = get_settings()
    artifacts = read_artifacts(settings)
    meta = load_meta(settings)
    features = artifacts.load_features()
    labels = artifacts.load_labels()
    steps = artifacts.load_steps()

    payload = {
        "dataset": "paysim",
        "feature_version": meta["feature_version"],
        "rules_only": _rules_baselines(settings, features, labels, steps),
        "hist_gradient_boosting": _gbm_baseline(features, labels, steps),
    }
    settings.metrics_path.mkdir(parents=True, exist_ok=True)
    (settings.metrics_path / "baselines.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    gbm = payload["hist_gradient_boosting"]
    print(f"[rules] test fraud-only={payload['rules_only']['test']['fraud_only']['f1']:.4f}")
    print(
        f"[gbm] train={gbm['train_seconds']:.1f}s test_f1@0.5={gbm['test']['f1']:.4f} "
        f"best_thr={gbm['best_threshold_validation']} "
        f"test_f1@best={gbm['test_at_best_threshold']['f1']:.4f}"
    )
    print(f"[out] {settings.metrics_path / 'baselines.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
