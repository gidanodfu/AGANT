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

"""División temporal de PaySim por ``step``.

Se evalúa temporalmente (no random split): la variación de la tasa de
fraude entre ventanas es señal de drift y se documenta, no se oculta.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

TRAIN_END = 520
VALIDATION_END = 631


class SplitName(str, Enum):
    TRAIN = "train"
    VALIDATION = "validation"
    TEST = "test"


@dataclass(frozen=True)
class TemporalSplit:
    train_end: int = TRAIN_END
    validation_end: int = VALIDATION_END

    def of(self, step: int) -> SplitName:
        if step <= self.train_end:
            return SplitName.TRAIN
        if step <= self.validation_end:
            return SplitName.VALIDATION
        return SplitName.TEST

    def bounds(self, split: SplitName) -> tuple[int | None, int | None]:
        if split is SplitName.TRAIN:
            return None, self.train_end
        if split is SplitName.VALIDATION:
            return self.train_end + 1, self.validation_end
        return self.validation_end + 1, None

    def describe(self) -> dict[str, tuple[int | None, int | None]]:
        return {split.value: self.bounds(split) for split in SplitName}


_DEFAULT = TemporalSplit()


def split_for_step(step: int) -> SplitName:
    return _DEFAULT.of(step)
