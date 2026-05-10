from datetime import datetime, timezone
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from olibo import db
from olibo.common.enums import MatchStatus
from olibo.incident_report.model import IncidentReport
from olibo.match_sheet.model import Match
from olibo.team.model import TeamMember
from olibo.users.model import User

incident_report = Blueprint('incident_report', __name__)

VALID_SEVERITIES = ('low', 'medium', 'high')
VALID_STATUSES   = ('reported', 'under_review', 'resolved')
ADMIN_ROLES      = {'super_admin', 'admin_competition', 'operator'}
REPORT_NOT_FOUND = 'Report not found'

INCIDENT_ALLOWED_STATUSES = {MatchStatus.IN_PROGRESS.value, MatchStatus.COMPLETED.value}


def get_authorized_user() -> User:
    return User.query.get(get_jwt_identity())


# ==========================================
# INCIDENT REPORT ROUTES
# ==========================================


@incident_report.route('', methods=['POST'])
@jwt_required()
def create_incident_report():
    try:
        user = get_authorized_user()

        if user.role not in ADMIN_ROLES:
            return jsonify({'error': 'Unauthorized'}), 403

        data = request.get_json()

        if not all(k in data for k in ['match_id', 'incident_type', 'description']):
            return jsonify({'error': 'Missing required fields: match_id, incident_type, description'}), 400

        match = Match.query.get(data['match_id'])
        if not match:
            return jsonify({'error': 'Match not found'}), 404

        if match.status not in INCIDENT_ALLOWED_STATUSES:
            return jsonify({'error': 'Incident reports can only be added to in-progress or completed matches'}), 409

        member_id = data.get('member_id')
        if member_id:
            member = TeamMember.query.get(member_id)
            if not member:
                return jsonify({'error': 'Member not found'}), 404
            if member.team_id not in (match.home_team_id, match.away_team_id):
                return jsonify({'error': 'Member is not part of this match'}), 400

        severity = data.get('severity', 'low')
        if severity not in VALID_SEVERITIES:
            return jsonify({'error': 'severity must be low, medium or high'}), 400

        report = IncidentReport(
            match_id=data['match_id'],
            reporter_id=user.id,
            member_id=member_id,
            incident_type=data['incident_type'],
            description=data['description'],
            minute=data.get('minute'),
            severity=severity,
        )

        db.session.add(report)
        db.session.commit()

        return jsonify({'message': 'Incident report created successfully', 'report': report.to_dict()}), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@incident_report.route('', methods=['GET'])
@jwt_required()
def get_all_incident_reports():
    try:
        user = get_authorized_user()

        if user.role not in ADMIN_ROLES:
            return jsonify({'error': 'Unauthorized'}), 403

        status    = request.args.get('status')
        match_id  = request.args.get('match_id', type=int)
        severity  = request.args.get('severity')

        query = IncidentReport.query
        if status:
            query = query.filter_by(status=status)
        if match_id:
            query = query.filter_by(match_id=match_id)
        if severity:
            query = query.filter_by(severity=severity)

        reports = query.order_by(IncidentReport.created_at.desc()).all()

        return jsonify({
            'message': 'Incident reports retrieved successfully',
            'total': len(reports),
            'reports': [r.to_dict() for r in reports],
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@incident_report.route('/<int:report_id>', methods=['GET'])
@jwt_required()
def get_incident_report(report_id):
    try:
        user = get_authorized_user()

        if user.role not in ADMIN_ROLES:
            return jsonify({'error': 'Unauthorized'}), 403

        report = IncidentReport.query.get(report_id)

        if not report:
            return jsonify({'error': REPORT_NOT_FOUND}), 404

        return jsonify({'message': 'Incident report retrieved successfully', 'report': report.to_dict()}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@incident_report.route('/<int:report_id>', methods=['PUT'])
@jwt_required()
def update_incident_report(report_id):
    try:
        user = get_authorized_user()

        if user.role not in ADMIN_ROLES:
            return jsonify({'error': 'Unauthorized'}), 403

        report = IncidentReport.query.get(report_id)
        if not report:
            return jsonify({'error': REPORT_NOT_FOUND}), 404

        data = request.get_json()

        if 'incident_type' in data:
            report.incident_type = data['incident_type']
        if 'description' in data:
            report.description = data['description']
        if 'status' in data:
            if data['status'] not in VALID_STATUSES:
                return jsonify({'error': 'status must be reported, under_review or resolved'}), 400
            report.status = data['status']
        if 'resolution' in data:
            report.resolution = data['resolution']
        if 'severity' in data:
            if data['severity'] not in VALID_SEVERITIES:
                return jsonify({'error': 'severity must be low, medium or high'}), 400
            report.severity = data['severity']
        if 'minute' in data:
            report.minute = data['minute']

        report.updated_at = datetime.now(timezone.utc)
        db.session.commit()

        return jsonify({'message': 'Incident report updated successfully', 'report': report.to_dict()}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@incident_report.route('/<int:report_id>', methods=['DELETE'])
@jwt_required()
def delete_incident_report(report_id):
    try:
        user = get_authorized_user()

        if user.role not in ADMIN_ROLES:
            return jsonify({'error': 'Unauthorized'}), 403

        report = IncidentReport.query.get(report_id)
        if not report:
            return jsonify({'error': REPORT_NOT_FOUND}), 404

        db.session.delete(report)
        db.session.commit()

        return '', 204

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
