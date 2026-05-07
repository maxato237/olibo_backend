from flask import Blueprint
from olibo.common.enums import (
    UserRole, RegistrationStatus, MatchStatus, CardType, VoteType, PaymentStatus,
    ROLE_LABELS_FR, REGISTRATION_STATUS_LABELS_FR, MATCH_STATUS_LABELS_FR,
    CARD_TYPE_LABELS_FR, VOTE_TYPE_LABELS_FR, PAYMENT_STATUS_LABELS_FR,
    RankingPreset, RANKING_PRESET_RULES, RANKING_PRESET_LABELS_FR, RANKING_TIEBREAKER_LABELS_FR,
)

enum = Blueprint('enum', __name__)


@enum.route('/roles', methods=['GET'])
def get_roles():
    return {"roles": [
        {"value": r.value, "label": ROLE_LABELS_FR.get(r.value, r.value)}
        for r in UserRole
    ]}, 200


@enum.route('/registrations', methods=['GET'])
def get_registration_statuses():
    return {"registration_status": [
        {"value": s.value, "label": REGISTRATION_STATUS_LABELS_FR.get(s.value, s.value)}
        for s in RegistrationStatus
    ]}, 200


@enum.route('/match_status', methods=['GET'])
def get_match_statuses():
    return {"match_status": [
        {"value": s.value, "label": MATCH_STATUS_LABELS_FR.get(s.value, s.value)}
        for s in MatchStatus
    ]}, 200


@enum.route('/card_types', methods=['GET'])
def get_card_types():
    return {"card_types": [
        {"value": c.value, "label": CARD_TYPE_LABELS_FR.get(c.value, c.value)}
        for c in CardType
    ]}, 200


@enum.route('/vote_types', methods=['GET'])
def get_vote_types():
    return {"vote_types": [
        {"value": v.value, "label": VOTE_TYPE_LABELS_FR.get(v.value, v.value)}
        for v in VoteType
    ]}, 200


@enum.route('/payment_status', methods=['GET'])
def get_payment_status():
    return {"payment_statuses": [
        {"value": s.value, "label": PAYMENT_STATUS_LABELS_FR.get(s.value, s.value)}
        for s in PaymentStatus
    ]}, 200


@enum.route('/ranking_presets', methods=['GET'])
def get_ranking_presets():
    return {"ranking_presets": [
        {
            "value":             p.value,
            "label":             RANKING_PRESET_LABELS_FR.get(p.value, p.value),
            "tiebreaker_order":  RANKING_PRESET_RULES.get(p.value, []),
            "tiebreaker_labels": RANKING_TIEBREAKER_LABELS_FR,
        }
        for p in RankingPreset
    ]}, 200
