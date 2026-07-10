# db_logger.py — backward-compatible re-export, verwijder in fase 12
from infrastructure.db.repositories.session_repository import SessionRepository

_repo = SessionRepository()

def log_session_created(session_id, user_agent=None):       return _repo.log_session_created(session_id, user_agent)
def log_message(session_id, role, content, flow_step=None): return _repo.log_message(session_id, role, content, flow_step)
def update_session_flow(session_id, flow_type):             return _repo.update_session_flow(session_id, flow_type)
def update_session_completed(session_id):                   return _repo.update_session_completed(session_id)
def update_session_ended(session_id):                       return _repo.update_session_ended(session_id)
def log_event(session_id, event_type, event_data=None):     return _repo.log_event(session_id, event_type, event_data)
def log_price_calculation(session_id, flow_type, costs):    return _repo.log_price_calculation(session_id, flow_type, costs)
def log_contact_submission(session_id, naam, telefoon, email, adres=None, woonplaats=None, notitie=None, price_calculation_id=None, email_sent_at=None) -> str | None:
    return _repo.log_contact_submission(session_id, naam, telefoon, email, adres, woonplaats, notitie, price_calculation_id, email_sent_at)
def save_leadscore(session_id, score, label, breakdown):    return _repo.save_leadscore(session_id, score, label, breakdown)
def increment_terug_actie(session_id, stap=None):           return _repo.increment_terug_actie(session_id, stap)
def log_prijs_gezien(session_id, min_eur, max_eur):         return _repo.log_prijs_gezien(session_id, min_eur, max_eur)
def log_drop_off(session_id, stap):                         return _repo.log_drop_off(session_id, stap)
def log_offerte_aangevraagd(session_id):                    return _repo.log_offerte_aangevraagd(session_id)
