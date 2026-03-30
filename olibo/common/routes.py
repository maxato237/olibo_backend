from flask import Blueprint
from flask_jwt_extended import jwt_required
from olibo.common.enums import UserRole, VoteType
from olibo.common.enums import RegistrationStatus
from olibo.common.enums import MatchStatus
from olibo_models import CardType
from olibo.common.enums import PaymentStatus

enum = Blueprint('enum', __name__)

@enum.route('/roles', methods=['GET'])
def get_roles():
    roles = [
        {
            "label": role.value.replace('_', ' ').title(),
            "value": role.value
        }
        for role in UserRole
    ]
    return {"roles": roles}, 200

@enum.route('/registrations', methods=['GET'])
@jwt_required()
def get_registration_statuses():
    statuses = [status.value for status in RegistrationStatus]
    return {"registration_status": statuses}, 200

@enum.route('/match_status', methods=['GET'])
@jwt_required()
def get_match_statuses():
    statuses = [status.value for status in MatchStatus]
    return {"match_status": statuses}, 200

@enum.route('/card_types', methods=['GET'])
@jwt_required()
def get_card_types():
    card_types = [card_type.value for card_type in CardType]
    return {"card_types": card_types}, 200

@enum.route('/vote_types', methods=['GET'])
@jwt_required()
def get_vote_types():
    vote_types = [vote_type.value for vote_type in VoteType]
    return {"vote_types": vote_types}, 200

@enum.route('/payment_status', methods=['GET'])
@jwt_required()
def get_payment_status():
    payment_statuses = [status.value for status in PaymentStatus]
    return {"payment_statuses": payment_statuses}, 200