# bot_logic.py — backward-compat re-export (fase 12)
# Implementatie zit in core/controllers/. Verwijder dit bestand wanneer
# alle consumers zijn bijgewerkt naar de nieuwe import-paden.
from __future__ import annotations

from typing import List, Tuple

from core.controllers.chat_controller import ChatController, INITIAL_GREETING
from core.models.chat_state import ChatState, make_initial_state


def handle_message(state: ChatState, user_text: str) -> Tuple[ChatState, List[str]]:
    ctrl = ChatController(state)
    return ctrl.handle(user_text)
