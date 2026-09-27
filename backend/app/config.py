# Copyright (C) 2026 Josue David (gidanodfu)
# https://github.com/gidanodfu/AGANT
#
# This file is part of AGANT.
#
# AGANT is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of
# the License, or (at your option) any later version.
#
# AGANT is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with AGANT. If not, see <https://www.gnu.org/licenses/>.

"""Configuración central de AGANT, dirigida por variables de entorno.

No se codifican rutas, puertos, tokens ni umbrales. Todo valor ajustable
vive aquí y puede sobrescribirse con variables con prefijo ``AGANT_``.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]

LAYA_MODES = {"disabled", "pretrained", "custom"}
DECISION_MODES = {"hybrid", "laya_all"}


class Settings(BaseSettings):
    """Configuración tipada y validada de AGANT."""

    model_config = SettingsConfigDict(
        env_prefix="AGANT_",
        env_file=str(REPO_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    env: str = "development"
    log_level: str = "INFO"

    data_dir: str = "./data"
    results_dir: str = "./results"
    frontend_dir: str = "./frontend"

    threshold_suspicious: float = 0.2
    threshold_fraud: float = 0.5

    chunk_rows: int = 250_000
    batch_size: int = 32
    block_size: int = 100_000
    publish_mode: str = "sampled"
    publish_sample_every: int = 100
    request_timeout_ms: int = 2000

    graph_max_accounts: int = 2_000_000
    graph_max_edges: int = 2_000_000

    rule_high_amount: float = 200_000.0
    rule_dest_fan_in: int = 10

    max_events: int = 1000
    ws_replay: bool = False

    decision_mode: str = "hybrid"
    laya_enabled: bool = True
    laya_mode: str = "pretrained"
    laya_device: str = "cuda"
    laya_model_id: str = "convaiinnovations/laya"
    laya_subfolder: str = "typed-decisions"
    laya_custom_subfolder: str | None = None
    laya_subfolders: str = "typed-decisions,multilingual"
    laya_warmup: bool = True
    laya_url: str | None = None

    cors_origins: str = "http://localhost:8000,http://127.0.0.1:8000"
    allowed_ws_origins: str = "http://localhost:8000,http://127.0.0.1:8000"
    admin_token: str | None = None
    health_strict: bool = False
    rate_limit_decision_per_min: int = 600
    rate_limit_flow_per_min: int = 300
    api_url: str = "http://localhost:8000"
    ws_url: str = "ws://localhost:8000"

    @field_validator("laya_mode")
    @classmethod
    def _validate_laya_mode(cls, value: str) -> str:
        value = value.strip().lower()
        if value not in LAYA_MODES:
            raise ValueError(f"AGANT_LAYA_MODE inválido: {value!r}; usar {sorted(LAYA_MODES)}")
        return value

    @field_validator("decision_mode")
    @classmethod
    def _validate_decision_mode(cls, value: str) -> str:
        value = value.strip().lower()
        if value not in DECISION_MODES:
            raise ValueError(
                f"AGANT_DECISION_MODE inválido: {value!r}; usar {sorted(DECISION_MODES)}"
            )
        return value

    @model_validator(mode="after")
    def _validate(self) -> "Settings":
        if not 0.0 <= self.threshold_suspicious < self.threshold_fraud <= 1.0:
            raise ValueError(
                "se requiere 0 <= AGANT_THRESHOLD_SUSPICIOUS < AGANT_THRESHOLD_FRAUD <= 1"
            )
        if self.chunk_rows <= 0 or self.batch_size <= 0:
            raise ValueError("AGANT_CHUNK_ROWS y AGANT_BATCH_SIZE deben ser positivos")
        if self.block_size <= 0:
            raise ValueError("AGANT_BLOCK_SIZE debe ser positivo")
        if self.batch_size not in (32, 64):
            # 32/64 son los tamaños de lote soportados por la UI; otros se aceptan
            # pero se documentan como avanzados.
            pass
        if self.publish_mode not in ("sampled", "all"):
            raise ValueError("AGANT_PUBLISH_MODE debe ser 'sampled' o 'all'")
        if self.laya_mode == "custom" and not self.laya_custom_subfolder:
            raise ValueError("AGANT_LAYA_MODE=custom exige AGANT_LAYA_CUSTOM_SUBFOLDER")
        return self

    def _resolve(self, raw: str) -> Path:
        path = Path(raw)
        return path if path.is_absolute() else (REPO_ROOT / path).resolve()

    @property
    def data_path(self) -> Path:
        return self._resolve(self.data_dir)

    @property
    def raw_data_path(self) -> Path:
        return self.data_path / "raw"

    @property
    def processed_data_path(self) -> Path:
        return self.data_path / "processed"

    @property
    def results_path(self) -> Path:
        return self._resolve(self.results_dir)

    @property
    def frontend_path(self) -> Path:
        return self._resolve(self.frontend_dir)

    @property
    def models_path(self) -> Path:
        return self.results_path / "models"

    @property
    def metrics_path(self) -> Path:
        return self.results_path / "metrics"

    @property
    def benchmarks_path(self) -> Path:
        return self.results_path / "benchmarks"

    @property
    def paysim_csv(self) -> Path:
        return self.raw_data_path / "paysim.csv"

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    @property
    def allowed_ws_origin_list(self) -> list[str]:
        return [item.strip() for item in self.allowed_ws_origins.split(",") if item.strip()]

    @property
    def laya_subfolder_list(self) -> list[str]:
        return [item.strip() for item in self.laya_subfolders.split(",") if item.strip()]

    @property
    def laya_custom_available(self) -> bool:
        # Custom es usable si hay subcarpetas seleccionables (catálogo).
        return bool(self.laya_subfolder_list)

    @property
    def laya_active_subfolder(self) -> str | None:
        if self.laya_mode == "custom":
            return self.laya_custom_subfolder
        if self.laya_mode == "pretrained":
            return self.laya_subfolder
        return None


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Devuelve la configuración cacheada (recargable con ``get_settings.cache_clear()``)."""
    return Settings()
