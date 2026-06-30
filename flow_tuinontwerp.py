# flow_tuinontwerp.py
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple

from flow_tuinaanleg import parse_m2, _is_dont_know


@dataclass
class TuinontWerpFlow:
    """Flow voor een 3D tuinontwerp prijsindicatie. Eén vraag: tuin m²."""
    step_index: int = 0
    answers: Dict[str, Any] = field(default_factory=dict)

    _STEPS = ("tuin_m2",)

    def is_done(self) -> bool:
        return self.step_index >= len(self._STEPS)

    def get_question(self) -> str:
        if self.is_done():
            return ""
        return (
            "Hoe groot is uw tuin in m²?\n"
            "_(bijv. 80 of 150 — dit bepaalt de indicatieprijs voor het ontwerp)_"
        )

    def handle(self, user_text: str) -> Tuple[str, bool]:
        if self.is_done():
            return "", True

        if _is_dont_know(user_text):
            return (
                "_Geef een schatting — een ronde waarde is prima. "
                "Een gemiddelde achtertuin is ca. 50–100 m²._\n\n"
                + self.get_question()
            ), False

        v = parse_m2(user_text)
        if v is None:
            return "Geef een getal in m², bijv. 80.", False
        if v <= 0 or v > 10000:
            return "Geef een getal tussen 1 en 10.000 m².", False

        self.answers["tuin_m2"] = v
        self.step_index += 1
        return "", True

    def to_answers(self) -> Dict[str, Any]:
        return {
            "tuin_m2": self.answers.get("tuin_m2", 0),
            "_flow_type": "tuinontwerp",
        }
