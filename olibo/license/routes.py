from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from olibo import db
from olibo.license.model import License
from olibo.team.model import TeamMember
from olibo.users.model import User

license = Blueprint('license', __name__)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def get_authorized_user() -> User:
    return User.query.get(get_jwt_identity())


# ==========================================
# LICENSE ROUTES
# ==========================================


@license.route('', methods=['POST'])
@jwt_required()
def create_license():
    try:
        user = get_authorized_user()

        if user.role not in ['super_admin', 'admin_competition']:
            return jsonify({'error': 'Unauthorized'}), 403

        data = request.get_json()

        if not all(k in data for k in ['member_id', 'license_number', 'issue_date', 'expiry_date']):
            return jsonify({'error': 'Missing required fields: member_id, license_number, issue_date, expiry_date'}), 400

        member = TeamMember.query.get(data['member_id'])
        if not member:
            return jsonify({'error': 'Member not found'}), 404

        if not member.is_player:
            return jsonify({'error': 'Licenses can only be issued to players'}), 400

        if License.query.filter_by(license_number=data['license_number']).first():
            return jsonify({'error': 'License number already exists'}), 409

        if License.query.filter_by(member_id=data['member_id']).first():
            return jsonify({'error': 'This member already has a license'}), 409

        issue_date = datetime.fromisoformat(data['issue_date'])
        expiry_date = datetime.fromisoformat(data['expiry_date'])

        if expiry_date <= issue_date:
            return jsonify({'error': 'expiry_date must be after issue_date'}), 400

        license_obj = License(
            member_id=data['member_id'],
            license_number=data['license_number'],
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
        member_id = request.args.get('member_id', type=int)
        team_id   = request.args.get('team_id', type=int)   # ← filtre ajouté
        is_valid  = request.args.get('is_valid')

        query = License.query

        if member_id:
            query = query.filter_by(member_id=member_id)

        if team_id:
            # Récupère tous les member_ids appartenant à cette équipe
            member_ids = [
                m.id for m in TeamMember.query.filter_by(team_id=team_id).all()
            ]
            if member_ids:
                query = query.filter(License.member_id.in_(member_ids))
            else:
                # Équipe sans membres → aucune licence possible
                return jsonify({
                    'message': 'Licenses retrieved successfully',
                    'total': 0,
                    'licenses': [],
                }), 200

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

        db.session.delete(license_obj)
        db.session.commit()

        return jsonify({'message': 'License deleted successfully'}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500