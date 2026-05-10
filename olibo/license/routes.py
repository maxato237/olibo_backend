from datetime import datetime

from flask import Blueprint, request, jsonify, make_response
from flask_jwt_extended import jwt_required

from olibo import db
from olibo.common.helpers import get_authorized_user
from olibo.license.model import License
from olibo.season.model import Season
from olibo.team.model import TeamMember, Team

license = Blueprint('license', __name__)


# ==========================================
# UTILITY
# ==========================================

def revoke_season_licenses(season_id: int) -> int:
    """Passe toutes les licences d'une saison à is_valid = False.
    Retourne le nombre de licences révoquées.
    """
    updated = License.query.filter_by(season_id=season_id, is_valid=True).update({'is_valid': False})
    db.session.flush()
    return updated


def _active_season_label() -> tuple:
    """Retourne (Season | None, label str) de la saison active."""
    season = Season.query.filter_by(is_active=True).first()
    label = season.label if season else str(datetime.utcnow().year)
    return season, label

def _check_season_closed(season) -> dict | None:
    """Retourne une erreur JSON-serialisable si la saison est inactive ou terminée."""
    if season and not season.is_active:
        return {'error': f"Season '{season.label}' is inactive. Licenses cannot be created or modified for an inactive season."}
    if season and season.end_date < datetime.utcnow().date():
        return {'error': f"Season '{season.label}' is closed. Licenses cannot be created or modified for a closed season."}
    return None

# ==========================================
# LICENSE ROUTES
# ==========================================


@license.route('/verify', methods=['GET'])
def verify_license_public():
    """Endpoint public — pas d'authentification. Utilisé par les QR codes des licences."""
    try:
        license_number = request.args.get('n', '').strip()
        if not license_number:
            return jsonify({'error': 'License number required'}), 400
        lic = License.query.filter_by(license_number=license_number).first()
        if not lic:
            return jsonify({'error': 'License not found'}), 404

        member = lic.member
        team   = member.team if member else None
        season = lic.season
        now    = datetime.utcnow()

        if not lic.is_valid:
            status = 'revoked'
        elif lic.expiry_date < now:
            status = 'expired'
        else:
            status = 'authentic'

        return jsonify({
            'verification_status': status,
            'license': {
                'id':                lic.id,
                'license_number':    lic.license_number,
                'issue_date':        lic.issue_date.isoformat(),
                'expiry_date':       lic.expiry_date.isoformat(),
                'is_valid':          lic.is_valid,
                'season_label':      season.label if season else None,
                'season_label_short': getattr(season, 'label_short', None),
            },
            'member': {
                'id':              member.id,
                'first_name':      member.first_name,
                'last_name':       member.last_name,
                'photo':           member.photo,
                'position':        member.position,
                'jersey_number':   member.jersey_number,
                'nationality':     member.nationality,
                'nationality_label': member.nationality_label,
                'category':        member.category,
                'gender':          member.gender,
                'height_cm':       member.height_cm,
                'weight_kg':       member.weight_kg,
                'birth_date':      member.birth_date.isoformat() if member.birth_date else None,
                'is_captain':      member.is_captain,
                'preferred_foot':  member.preferred_foot,
            } if member else None,
            'team': {
                'id':   team.id,
                'name': team.name,
                'logo': team.logo,
            } if team else None,
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@license.route('', methods=['POST'])
@jwt_required()
def create_license():
    try:
        user = get_authorized_user()

        if user.role not in ['super_admin', 'admin_competition']:
            return jsonify({'error': 'Unauthorized'}), 403

        data = request.get_json()

        if not all(k in data for k in ['member_id', 'issue_date', 'expiry_date']):
            return jsonify({'error': 'Missing required fields: member_id, issue_date, expiry_date'}), 400

        member = TeamMember.query.get(data['member_id'])
        if not member:
            return jsonify({'error': 'Member not found'}), 404

        if not member.is_player:
            return jsonify({'error': 'Licenses can only be issued to players'}), 400

        issue_date = datetime.fromisoformat(data['issue_date'])
        expiry_date = datetime.fromisoformat(data['expiry_date'])

        if expiry_date <= issue_date:
            return jsonify({'error': 'expiry_date must be after issue_date'}), 400

        # Résolution de la saison (priorité : season_id fourni > saison active)
        season_id = data.get('season_id')
        if season_id:
            season = Season.query.get(season_id)
            if not season:
                return jsonify({'error': 'Season not found'}), 404
        else:
            season, _ = _active_season_label()
            if not season:
                return jsonify({'error': 'No active season found. Licenses can only be created for an active season.'}), 409
            season_id = season.id

        # Vérification saison inactive / fermée
        err = _check_season_closed(season)
        if err:
            return jsonify(err), 409

        season_label = season.label

        existing = License.query.filter_by(member_id=data['member_id'], season_id=season_id).first()
        license_number = f"OL-{season_label}-{member.team_id:03d}-{member.id:03d}"

        if existing:
            if existing.is_valid:
                return jsonify({'error': 'This member already has an active license for this season'}), 409

            if existing.license_number != license_number:
                if License.query.filter_by(license_number=license_number).first():
                    return jsonify({'error': f'License number already exists: {license_number}'}), 409
                existing.license_number = license_number

            existing.is_valid = True
            existing.issue_date = issue_date
            existing.expiry_date = expiry_date
            if 'document_url' in data:
                existing.document_url = data.get('document_url')
            db.session.commit()

            return jsonify({'message': 'License reactivated successfully', 'license': existing.to_dict()}), 200

        if License.query.filter_by(license_number=license_number).first():
            return jsonify({'error': f'License number already exists: {license_number}'}), 409

        license_obj = License(
            member_id=data['member_id'],
            season_id=season_id,
            license_number=license_number,
            issue_date=issue_date,
            expiry_date=expiry_date,
            document_url=data.get('document_url'),
        )

        db.session.add(license_obj)
        db.session.commit()

        return jsonify({'message': 'License created successfully', 'license': license_obj.to_dict()}), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@license.route('', methods=['GET'])
@jwt_required()
def get_all_licenses():
    try:
        current_user = get_authorized_user()

        if current_user.role not in ['super_admin', 'admin_competition', 'operator']:
            team = Team.query.filter_by(representative_id=current_user.id).first()
            if not team:
                return jsonify({'error': 'Unauthorized'}), 403
            member_ids = [m.id for m in TeamMember.query.filter_by(team_id=team.id).all()]
            query = License.query.filter(License.member_id.in_(member_ids)) if member_ids else License.query.filter_by(id=None)
            licenses = query.all()
            return jsonify({
                'message': 'Licenses retrieved successfully',
                'total': len(licenses),
                'licenses': [l.to_dict() for l in licenses],
            }), 200

        member_id = request.args.get('member_id', type=int)
        team_id = request.args.get('team_id', type=int)
        season_id = request.args.get('season_id', type=int)
        is_valid = request.args.get('is_valid')

        query = License.query

        if member_id:
            query = query.filter_by(member_id=member_id)

        if team_id:
            member_ids = [m.id for m in TeamMember.query.filter_by(team_id=team_id).all()]
            if member_ids:
                query = query.filter(License.member_id.in_(member_ids))
            else:
                return jsonify({'message': 'Licenses retrieved successfully', 'total': 0, 'licenses': []}), 200

        if season_id:
            query = query.filter_by(season_id=season_id)

        if is_valid is not None:
            query = query.filter_by(is_valid=is_valid.lower() == 'true')

        licenses = query.all()

        return jsonify({
            'message': 'Licenses retrieved successfully',
            'total': len(licenses),
            'licenses': [l.to_dict() for l in licenses],
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@license.route('/season/<int:season_id>/team/<int:team_id>', methods=['GET'])
@jwt_required()
def get_team_season_licenses(season_id, team_id):
    try:
        season = Season.query.get(season_id)
        if not season:
            return jsonify({'error': 'Season not found'}), 404

        member_ids = [
            m.id for m in TeamMember.query.filter_by(team_id=team_id, role='player').all()
        ]

        if member_ids:
            licenses = License.query.filter(
                License.member_id.in_(member_ids),
                License.season_id == season_id,
            ).all()
        else:
            licenses = []

        active_season, active_label = _active_season_label()

        resp = make_response(jsonify({
            'message': 'Licenses retrieved successfully',
            'total': len(licenses),
            'licenses': [l.to_dict() for l in licenses],
        }))
        resp.headers['X-Active-Season'] = active_label
        return resp, 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@license.route('/team/<int:team_id>/generate', methods=['POST'])
@jwt_required()
def generate_team_licenses(team_id):
    try:
        user = get_authorized_user()
        if user.role not in ['super_admin', 'admin_competition']:
            return jsonify({'error': 'Unauthorized'}), 403

        t = Team.query.get(team_id)
        if not t:
            return jsonify({'error': 'Team not found'}), 404

        data = request.get_json(silent=True) or {}

        season_id = data.get('season_id')
        if season_id:
            season = Season.query.get(season_id)
            if not season:
                return jsonify({'error': 'Season not found'}), 404
        else:
            season, _ = _active_season_label()
            if not season:
                return jsonify({'error': 'No active season found. Licenses can only be generated for an active season.'}), 409
            season_id = season.id

        # Vérification saison terminée
        err = _check_season_closed(season)
        if err:
            return jsonify(err), 409

        season_label = season.label

        if 'issue_date' in data:
            issue_date = datetime.fromisoformat(data['issue_date'])
        elif season:
            issue_date = datetime(season.start_date.year, season.start_date.month, season.start_date.day)
        else:
            issue_date = datetime.utcnow()

        if 'expiry_date' in data:
            expiry_date = datetime.fromisoformat(data['expiry_date'])
        elif season:
            expiry_date = datetime(season.end_date.year, season.end_date.month, season.end_date.day)
        else:
            now = datetime.utcnow()
            expiry_date = datetime(now.year, 12, 31)

        if expiry_date <= issue_date:
            return jsonify({'error': 'expiry_date must be after issue_date'}), 400

        players = TeamMember.query.filter_by(team_id=team_id, role='player', is_active=True).all()
        if not players:
            return jsonify({'message': 'No active players in this team', 'created': [], 'skipped': []}), 200

        created = []
        skipped = []

        for player in players:
            existing = License.query.filter_by(member_id=player.id, season_id=season_id).first()
            license_number = f"OL-{season_label}-{player.team_id:03d}-{player.id:03d}"

            if existing:
                if existing.is_valid:
                    skipped.append({'member_id': player.id, 'reason': 'license already active for this season'})
                    continue

                if existing.license_number != license_number:
                    if License.query.filter_by(license_number=license_number).first():
                        skipped.append({'member_id': player.id, 'reason': f'license number conflict: {license_number}'})
                        continue
                    existing.license_number = license_number

                existing.is_valid = True
                existing.issue_date = issue_date
                existing.expiry_date = expiry_date
                if 'document_url' in data:
                    existing.document_url = data.get('document_url')
                db.session.flush()
                created.append(existing.to_dict())
                continue

            if License.query.filter_by(license_number=license_number).first():
                skipped.append({'member_id': player.id, 'reason': f'license number conflict: {license_number}'})
                continue

            lic = License(
                member_id=player.id,
                season_id=season_id,
                license_number=license_number,
                issue_date=issue_date,
                expiry_date=expiry_date,
            )
            db.session.add(lic)
            db.session.flush()
            created.append(lic.to_dict())

        db.session.commit()
        return jsonify({
            'message': f'{len(created)} license(s) generated',
            'created': created,
            'skipped': skipped,
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@license.route('/<int:license_id>', methods=['GET'])
@jwt_required()
def get_license(license_id):
    try:
        license_obj = License.query.get(license_id)
        if not license_obj:
            return jsonify({'error': 'License not found'}), 404
        return jsonify({'message': 'License retrieved successfully', 'license': license_obj.to_dict()}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@license.route('/<int:license_id>/validate', methods=['POST'])
@jwt_required()
def validate_license(license_id):
    try:
        user = get_authorized_user()

        if user.role not in ['super_admin', 'admin_competition']:
            return jsonify({'error': 'Unauthorized'}), 403

        license_obj = License.query.get(license_id)
        if not license_obj:
            return jsonify({'error': 'License not found'}), 404

        if license_obj.expiry_date < datetime.utcnow():
            return jsonify({'error': 'License has expired'}), 400

        license_obj.is_valid = True
        db.session.commit()

        return jsonify({'message': 'License validated successfully', 'license': license_obj.to_dict()}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@license.route('/<int:license_id>/invalidate', methods=['POST'])
@jwt_required()
def invalidate_license(license_id):
    try:
        user = get_authorized_user()

        if user.role not in ['super_admin', 'admin_competition']:
            return jsonify({'error': 'Unauthorized'}), 403

        license_obj = License.query.get(license_id)
        if not license_obj:
            return jsonify({'error': 'License not found'}), 404

        license_obj.is_valid = False
        db.session.commit()

        return jsonify({'message': 'License invalidated successfully', 'license': license_obj.to_dict()}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@license.route('/<int:license_id>', methods=['PUT'])
@jwt_required()
def renew_license(license_id):
    try:
        user = get_authorized_user()

        if user.role not in ['super_admin', 'admin_competition']:
            return jsonify({'error': 'Unauthorized'}), 403

        license_obj = License.query.get(license_id)
        if not license_obj:
            return jsonify({'error': 'License not found'}), 404

        # Vérification saison terminée
        season = Season.query.get(license_obj.season_id) if license_obj.season_id else None
        err = _check_season_closed(season)
        if err:
            return jsonify(err), 409

        data = request.get_json()

        if 'expiry_date' in data:
            new_expiry = datetime.fromisoformat(data['expiry_date'])
            if new_expiry <= datetime.utcnow():
                return jsonify({'error': 'New expiry date must be in the future'}), 400
            license_obj.expiry_date = new_expiry
            license_obj.is_valid = True

        if 'document_url' in data:
            license_obj.document_url = data['document_url']

        db.session.commit()
        return jsonify({'message': 'License updated', 'license': license_obj.to_dict()}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@license.route('/<int:license_id>/export', methods=['GET'])
@jwt_required()
def export_license(license_id):
    try:
        user = get_authorized_user()
        if user.role not in ['super_admin', 'admin_competition']:
            return jsonify({'error': 'Unauthorized'}), 403

        license_obj = License.query.get(license_id)
        if not license_obj:
            return jsonify({'error': 'License not found'}), 404

        from olibo.license.export_service import LicenseExportService
        zip_bytes = LicenseExportService().export_single_zip(license_id)

        response = make_response(zip_bytes)
        response.headers['Content-Type'] = 'application/zip'
        response.headers['Content-Disposition'] = (
            f'attachment; filename="{license_obj.license_number}.zip"'
        )
        return response

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@license.route('/team/<int:team_id>/export', methods=['GET'])
@jwt_required()
def export_team_licenses(team_id):
    try:
        user = get_authorized_user()
        if user.role not in ['super_admin', 'admin_competition']:
            return jsonify({'error': 'Unauthorized'}), 403

        team = Team.query.get(team_id)
        if not team:
            return jsonify({'error': 'Team not found'}), 404

        from olibo.license.export_service import LicenseExportService
        zip_bytes = LicenseExportService().export_team_zip(team_id)

        safe_name = team.name.replace(' ', '_').replace('/', '-')
        response = make_response(zip_bytes)
        response.headers['Content-Type'] = 'application/zip'
        response.headers['Content-Disposition'] = (
            f'attachment; filename="licences_{safe_name}.zip"'
        )
        return response

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@license.route('/<int:license_id>', methods=['DELETE'])
@jwt_required()
def delete_license(license_id):
    try:
        user = get_authorized_user()

        if user.role != 'super_admin':
            return jsonify({'error': 'Only super admin can delete licenses'}), 403

        license_obj = License.query.get(license_id)
        if not license_obj:
            return jsonify({'error': 'License not found'}), 404

        member = license_obj.member
        if member:
            member.license_number = None

        db.session.delete(license_obj)
        db.session.commit()

        return '', 204

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
