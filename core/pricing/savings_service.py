from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from core.pricing.price_table import PriceTable


class SavingsService:
    """
    Verzamelt alle kostenbesparing-logica.
    Delegeert voorlopig naar savings.py (implementatie verhuist in fase 12).
    """

    def __init__(self, price_table: PriceTable = None):
        self.prices = price_table

    # ----------------------------------------------------------
    # Keuzetekst na offerte
    # ----------------------------------------------------------

    def post_offer_choices_text(self) -> str:
        from core.pricing.savings import post_offer_choices_text
        return post_offer_choices_text()

    def post_offer_choices_losse_text(self) -> str:
        from core.pricing.savings import post_offer_choices_losse_text
        return post_offer_choices_losse_text()

    def post_offer_choices_tuinontwerp_text(self) -> str:
        from core.pricing.savings import post_offer_choices_tuinontwerp_text
        return post_offer_choices_tuinontwerp_text()

    # ----------------------------------------------------------
    # Kostenbesparing menu's (tekst + mapping)
    # ----------------------------------------------------------

    def lower_costs_menu_text(self, ans: dict, base_costs: dict = None) -> Tuple[str, Dict[str, str]]:
        from core.pricing.savings import lower_costs_menu_text
        return lower_costs_menu_text(ans, base_costs)

    def lower_costs_menu_losse_text(self, ans: dict, base_costs: dict = None) -> Tuple[str, Dict[str, str]]:
        from core.pricing.savings import lower_costs_menu_losse_text
        return lower_costs_menu_losse_text(ans, base_costs)

    def more_green_choice_text(self, ans: dict, base_costs: dict) -> Tuple[str, Dict[str, str]]:
        from core.pricing.savings import more_green_choice_text
        return more_green_choice_text(ans, base_costs)

    def extras_select_menu_text(self, ans: dict, base_costs: dict) -> Tuple[str, Dict[str, str]]:
        from core.pricing.savings import extras_select_menu_text
        return extras_select_menu_text(ans, base_costs)

    def material_part_menu_text(self, ans: dict) -> Tuple[str, Dict[str, str]]:
        from core.pricing.savings import material_part_menu_text
        return material_part_menu_text(ans)

    def material_choice_menu_text_cheaper(
        self, ans: dict, base_costs: dict, item_specs: tuple
    ) -> Tuple[str, Dict[str, str]]:
        from core.pricing.savings import material_choice_menu_text_cheaper
        return material_choice_menu_text_cheaper(ans, base_costs, item_specs)

    def vlonder_choice_menu_text(self, ans: dict, base_costs: dict) -> Tuple[str, Dict[str, str]]:
        from core.pricing.savings import vlonder_choice_menu_text
        return vlonder_choice_menu_text(ans, base_costs)

    def overkapping_choice_menu_text(self, ans: dict, base_costs: dict) -> Tuple[str, Dict[str, str]]:
        from core.pricing.savings import overkapping_choice_menu_text
        return overkapping_choice_menu_text(ans, base_costs)

    def voegen_choice_menu_text(self, ans: dict, base_costs: dict) -> Tuple[str, Dict[str, str]]:
        from core.pricing.savings import voegen_choice_menu_text
        return voegen_choice_menu_text(ans, base_costs)

    def verlichting_choice_menu_text(self, ans: dict, base_costs: dict) -> Tuple[str, Dict[str, str]]:
        from core.pricing.savings import verlichting_choice_menu_text
        return verlichting_choice_menu_text(ans, base_costs)

    def beregening_systeem_choice_text(self, ans: dict, base_costs: dict) -> Tuple[str, Dict[str, str]]:
        from core.pricing.savings import beregening_systeem_choice_text
        return beregening_systeem_choice_text(ans, base_costs)

    def erf_remove_select_menu_text(self, ans: dict, base_costs: dict) -> Tuple[str, Dict[str, str]]:
        from core.pricing.savings import erf_remove_select_menu_text
        return erf_remove_select_menu_text(ans, base_costs)

    def erf_item_select_menu_text(self, ans: dict, base_costs: dict) -> Tuple[str, Dict[str, str]]:
        from core.pricing.savings import erf_item_select_menu_text
        return erf_item_select_menu_text(ans, base_costs)

    def erf_haag_menu_text(self, ans: dict, base_costs: dict, item_index: int) -> Tuple[str, Dict[str, str]]:
        from core.pricing.savings import erf_haag_menu_text
        return erf_haag_menu_text(ans, base_costs, item_index)

    def erf_schutting_menu_text(self, ans: dict, base_costs: dict, item_index: int) -> Tuple[str, Dict[str, str]]:
        from core.pricing.savings import erf_schutting_menu_text
        return erf_schutting_menu_text(ans, base_costs, item_index)

    def losse_component_remove_menu_text(self, ans: dict, base_costs: dict) -> Tuple[str, Dict[str, str]]:
        from core.pricing.savings import losse_component_remove_menu_text
        return losse_component_remove_menu_text(ans, base_costs)

    # ----------------------------------------------------------
    # Apply-functies (antwoorden aanpassen)
    # ----------------------------------------------------------

    def apply_set_ratio(self, answers: dict, ratio_code: str) -> Tuple[dict, str]:
        from core.pricing.savings import apply_set_ratio
        return apply_set_ratio(answers, ratio_code)

    def apply_ratio_proportional(self, answers: dict, ratio_code: str) -> Tuple[dict, str]:
        from core.pricing.savings import apply_ratio_proportional
        return apply_ratio_proportional(answers, ratio_code)

    def apply_remove_selected_extras(self, answers: dict, selected_actions: List[str]) -> Tuple[dict, str]:
        from core.pricing.savings import apply_remove_selected_extras
        return apply_remove_selected_extras(answers, selected_actions)

    def apply_material_change(self, answers: dict, part: Any, choice_digit: str) -> Tuple[dict, str]:
        from core.pricing.savings import apply_material_change
        return apply_material_change(answers, part, choice_digit)

    def apply_vlonder_change(self, answers: dict, action: str) -> Tuple[dict, str]:
        from core.pricing.savings import apply_vlonder_change
        return apply_vlonder_change(answers, action)

    def apply_overkapping_change(self, answers: dict, action: str) -> Tuple[dict, str]:
        from core.pricing.savings import apply_overkapping_change
        return apply_overkapping_change(answers, action)

    def apply_voegen_change(self, answers: dict) -> Tuple[dict, str]:
        from core.pricing.savings import apply_voegen_change
        return apply_voegen_change(answers)

    def apply_verlichting_change(self, answers: dict) -> Tuple[dict, str]:
        from core.pricing.savings import apply_verlichting_change
        return apply_verlichting_change(answers)

    def apply_beregening_remove(self, answers: dict) -> Tuple[dict, str]:
        from core.pricing.savings import apply_beregening_remove
        return apply_beregening_remove(answers)

    def apply_beregening_systeem_change(self, answers: dict, systeem: str) -> Tuple[dict, str]:
        from core.pricing.savings import apply_beregening_systeem_change
        return apply_beregening_systeem_change(answers, systeem)

    def apply_erf_changes(self, answers: dict, selected_actions: List[str]) -> Tuple[dict, str]:
        from core.pricing.savings import apply_erf_changes
        return apply_erf_changes(answers, selected_actions)

    def apply_erf_item_haag_change(self, answers: dict, item_index: int, action: str) -> Tuple[dict, str]:
        from core.pricing.savings import apply_erf_item_haag_change
        return apply_erf_item_haag_change(answers, item_index, action)

    def apply_erf_item_schutting_change(self, answers: dict, item_index: int, action: str) -> Tuple[dict, str]:
        from core.pricing.savings import apply_erf_item_schutting_change
        return apply_erf_item_schutting_change(answers, item_index, action)

    def apply_remove_losse_component(self, answers: dict, comp_key: str) -> Tuple[dict, str]:
        from core.pricing.savings import apply_remove_losse_component
        return apply_remove_losse_component(answers, comp_key)

    def apply_remove_losse_item(self, answers: dict, comp_base: str, index: int) -> Tuple[dict, str]:
        from core.pricing.savings import apply_remove_losse_item
        return apply_remove_losse_item(answers, comp_base, index)

    # ----------------------------------------------------------
    # Parse-helpers (input validatie)
    # ----------------------------------------------------------

    @staticmethod
    def parse_multi_digits(user_text: str, *, allowed: Tuple[str, ...]) -> Optional[Tuple[str, ...]]:
        from core.pricing.savings import parse_multi_digits
        return parse_multi_digits(user_text, allowed=allowed)

    @staticmethod
    def parse_single_digit(user_text: str, *, allowed: Tuple[str, ...]) -> Optional[str]:
        from core.pricing.savings import parse_single_digit
        return parse_single_digit(user_text, allowed=allowed)

    @staticmethod
    def parse_material_parts(user_text: str) -> Optional[Tuple[str, ...]]:
        from core.pricing.savings import parse_material_parts
        return parse_material_parts(user_text)

    @staticmethod
    def is_cancel(text: str) -> bool:
        from core.pricing.savings import is_cancel
        return is_cancel(text)

    @staticmethod
    def is_back(text: str) -> bool:
        from core.pricing.savings import is_back
        return is_back(text)

    # ----------------------------------------------------------
    # Detectie-helpers (antwoorden inspecteren)
    # ----------------------------------------------------------

    @staticmethod
    def has_vlonder(ans: dict) -> bool:
        from core.pricing.savings import has_vlonder
        return has_vlonder(ans)

    @staticmethod
    def has_paving(ans: dict) -> bool:
        from core.pricing.savings import has_paving
        return has_paving(ans)

    @staticmethod
    def has_beregening_downgrade(ans: dict) -> bool:
        from core.pricing.savings import has_beregening_downgrade
        return has_beregening_downgrade(ans)

    @staticmethod
    def has_haag_downgrade(ans: dict) -> bool:
        from core.pricing.savings import has_haag_downgrade
        return has_haag_downgrade(ans)

    @staticmethod
    def has_overkapping_downgrade(ans: dict) -> bool:
        from core.pricing.savings import has_overkapping_downgrade
        return has_overkapping_downgrade(ans)

    @staticmethod
    def has_extras(ans: dict) -> bool:
        from core.pricing.savings import has_extras
        return has_extras(ans)

    @staticmethod
    def has_erfafscheiding(ans: dict) -> bool:
        from core.pricing.savings import has_erfafscheiding
        return has_erfafscheiding(ans)

    @staticmethod
    def erf_stats(ans: dict) -> dict:
        from core.pricing.savings import erf_stats
        return erf_stats(ans)

    @staticmethod
    def saving_text_from_delta(
        base_costs: dict, preview_costs: dict, *, keys: Tuple[str, ...]
    ) -> str:
        from core.pricing.savings import saving_text_from_delta
        return saving_text_from_delta(base_costs, preview_costs, keys=keys)
