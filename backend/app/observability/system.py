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

"""Validación de arranque y estado del sistema.

AGANT no bloquea todo el sistema por una dependencia opcional: si un
componente no crítico falta, queda ``DEGRADED`` y mantiene su fallback.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..config import Settings
from ..contracts.enums import ComponentStatus


@dataclass
class ComponentCheck:
    name: str
    status: ComponentStatus
    required: bool = False
    detail: str = ""


@dataclass
class StartupReport:
    components: list[ComponentCheck] = field(default_factory=list)

    @property
    def ready(self) -> bool:
        return all(
            c.status is not ComponentStatus.FAILED and c.status is not ComponentStatus.UNAVAILABLE
            for c in self.components
            if c.required
        )

    @property
    def degraded(self) -> list[ComponentCheck]:
        return [
            c
            for c in self.components
            if c.status in (ComponentStatus.FAILED, ComponentStatus.UNAVAILABLE)
        ]

    def summary(self) -> str:
        if self.ready and not self.degraded:
            return "AGANT READY"
        if self.ready:
            names = ", ".join(f"{c.name}={c.status.value}" for c in self.degraded)
            return f"AGANT READY (degradado: {names})"
        names = ", ".join(
            f"{c.name}={c.status.value}" for c in self.components if c.required
        )
        return f"AGANT DEGRADED ({names})"

    def component_status(self) -> dict[str, str]:
        return {c.name: c.status.value for c in self.components}


def _check_gpu() -> ComponentCheck:
    try:
        import torch

        if torch.cuda.is_available():
            name = torch.cuda.get_device_name(0)
            return ComponentCheck("gpu", ComponentStatus.READY, False, name)
        return ComponentCheck("gpu", ComponentStatus.UNAVAILABLE, False, "CUDA no disponible")
    except Exception as exc:  # noqa: BLE001 - se reporta como estado, no se silencia
        return ComponentCheck("gpu", ComponentStatus.UNAVAILABLE, False, type(exc).__name__)


def _check_dataset(settings: Settings) -> ComponentCheck:
    if settings.paysim_csv.exists():
        return ComponentCheck("dataset", ComponentStatus.READY, False, "paysim.csv presente")
    return ComponentCheck(
        "dataset", ComponentStatus.UNAVAILABLE, False, "paysim.csv no encontrado"
    )


def _check_models(settings: Settings, ml: object | None = None) -> ComponentCheck:
    if ml is not None:
        if getattr(ml, "available", False):
            return ComponentCheck("model", ComponentStatus.READY, False, getattr(ml, "model_version", None) or "cargado")
        return ComponentCheck(
            "model", ComponentStatus.UNAVAILABLE, False, getattr(ml, "load_error", None) or "no cargado"
        )
    models = list(settings.models_path.glob("*.joblib")) if settings.models_path.exists() else []
    if models:
        return ComponentCheck("model", ComponentStatus.READY, False, f"{len(models)} artefacto(s)")
    return ComponentCheck("model", ComponentStatus.UNAVAILABLE, False, "sin artefactos entrenados")


def _check_laya(settings: Settings, laya: object | None = None) -> ComponentCheck:
    if laya is not None:
        return ComponentCheck("laya", getattr(laya, "status", ComponentStatus.LOADING), False, getattr(laya, "mode", settings.laya_mode))
    if not settings.laya_enabled or settings.laya_mode == "disabled":
        return ComponentCheck("laya", ComponentStatus.DISABLED, False, "deshabilitado")
    return ComponentCheck("laya", ComponentStatus.LOADING, False, f"modo={settings.laya_mode}")


def collect_startup_report(
    settings: Settings, *, ml: object | None = None, laya: object | None = None
) -> StartupReport:
    checks = [
        ComponentCheck("config", ComponentStatus.READY, True, f"env={settings.env}"),
        _check_gpu(),
        _check_dataset(settings),
        _check_models(settings, ml),
        _check_laya(settings, laya),
    ]
    return StartupReport(components=checks)
