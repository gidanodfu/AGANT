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

"""Tests del motor de reglas."""

from __future__ import annotations

from app.config import Settings
from app.contracts.enums import Decision
from app.contracts.transaction import GraphContext, Transaction
from app.evidence import RulesEngine


def _engine() -> RulesEngine:
    return RulesEngine(Settings(laya_mode="disabled"))


def _transaction(**overrides) -> Transaction:
    base = dict(
        transaction_id="T1",
        step=10,
        type="TRANSFER",
        amount=100.0,
        name_orig="C1",
        old_balance_org=1000.0,
        name_dest="M1",
        old_balance_dest=0.0,
    )
    base.update(overrides)
    return Transaction(**base)


def test_r001_forces_fraud_and_is_critical():
    rules = _engine().evaluate(_transaction(is_flagged_fraud=True), GraphContext())
    r001 = next(rule for rule in rules if rule.rule_id == "R001")
    assert r001.triggered and r001.severity == "critical" and r001.decision is Decision.FRAUD


def test_r002_high_value_transfer():
    rules = _engine().evaluate(_transaction(amount=250_000.0), GraphContext())
    assert next(r for r in rules if r.rule_id == "R002").triggered


def test_r003_drained_origin():
    rules = _engine().evaluate(
        _transaction(type="CASH_OUT", amount=1000.0, old_balance_org=1000.0), GraphContext()
    )
    assert next(r for r in rules if r.rule_id == "R003").triggered


def test_r004_destination_fan_in():
    graph = GraphContext(destination_unique_origins_before=25)
    rules = _engine().evaluate(_transaction(amount=1.0), graph)
    assert next(r for r in rules if r.rule_id == "R004").triggered


def test_legitimate_transaction_triggers_nothing_critical():
    rules = _engine().evaluate(
        _transaction(type="PAYMENT", amount=50.0, old_balance_org=1000.0), GraphContext()
    )
    assert not any(rule.triggered for rule in rules)
    assert _engine().rule_score(rules) == 0.0


def test_evaluation_is_deterministic():
    engine = _engine()
    tx = _transaction(amount=300_000.0)
    assert engine.evaluate(tx, GraphContext()) == engine.evaluate(tx, GraphContext())
