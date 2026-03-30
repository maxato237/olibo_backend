import cloudinary.uploader
import uuid
import os
from datetime import datetime

from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from google.oauth2 import service_account
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

from olibo import db
from olibo.common.enums import RegistrationStatus
from olibo.team.model import TeamMember, Team, TeamRegistration
from olibo.users.model import User

team = Blueprint('team', __name__)

# ─── Helpers ──────────────────────────────────────────────────────────────────

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
MAX_FILE_SIZE = 2 * 1024 * 1024  # 2 MB
MIME_TYPES = {
    'jpg': 'image/jpeg',
    'jpeg': 'image/jpeg',
    'png': 'image/png',
}


def allowed_file(filename: str) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_upload(file, subfolder: str) -> str | None:
    if not file or file.filename == '':
        return None
    if not allowed_file(file.filename):
        return None

    # Vérification taille
    file.seek(0, os.SEEK_END)
    size = file.tell()
    file.seek(0)

    if size > MAX_FILE_SIZE:
        return None

    try:
        result = cloudinary.uploader.upload(
            file,
            folder=subfolder,
            resource_type="image",
            transformation=[
                {"width": 500, "height": 500, "crop": "limit"},
                {"quality": "auto"},
                {"fetch_format": "auto"}
            ]
        )
        return {
            "url": result["secure_url"],
            "public_id": result["public_id"]
        }
    except Exception as e:
        current_app.logger.error(f"Cloudinary upload error: {e}")
        return None

def delete_from_cloudinary(public_id):
    try:
        cloudinary.uploader.destroy(public_id)
    except Exception as e:
        current_app.logger.error(f"Cloudinary delete error: {e}")

# --- helpers utilisateur / équipe ---
def get_authorized_user() -> 'User':
    return User.query.get(get_jwt_identity())


def is_team_manager(user: 'User', t: 'Team') -> bool:
    return t.captain_id == user.id or user.role == 'super_admin'

# ==========================================
# TEAM ROUTES
# ==========================================


@team.route('', methods=['POST'])
@jwt_required()
def create_team():
    # try:
        if 'name' not in request.form or not request.form['name'].strip():
            return jsonify({'error': 'Team name is required'}), 400

        if Team.query.filter_by(name=request.form['name']).first():
            return jsonify({'error': 'Team name already exists'}), 409

        #LOGO
        logo = request.files.get('logo')
        logo_path = None

        if logo and logo.filename:
            logo_path = save_upload(logo, 'logos')

        new_team = Team(
            name=request.form['name'],
            logo=logo_path['url'] if logo_path else None,
            logo_public_id=logo_path['public_id'] if logo_path else None,
            representative_id=request.form.get('representative', type=int),
            description=request.form.get('description'),
            captain_id=request.form.get('captain_id', type=int),
            coach_id=request.form.get('coach_id', type=int),
            is_registered=request.form.get('is_registered', 'false').lower() == 'true',
        )

        db.session.add(new_team)
        db.session.flush()

        errors = _add_members_from_form(request.form, request.files, new_team.id)

        if errors:
            db.session.rollback()
            return jsonify({'error': 'Invalid member data', 'details': errors}), 400

        db.session.commit()

        return jsonify({
            'message': 'Team created successfully',
            'team': new_team.to_dict(),
        }), 201

    # except Exception as e:
    #     db.session.rollback()
    #     print("ERROR:", e)
    #     return jsonify({'error': str(e)}), 500

def _add_members_from_form(form, files, team_id: int) -> list[str]:
    """
    Parse les champs membres depuis le FormData et les insère en base.
    Retourne une liste d'erreurs (vide = succès).
    """
    errors = []
    index = 0

    while f'members[{index}][role]' in form or f'members[{index}][first_name]' in form:
        prefix = f'members[{index}]'

        first_name = form.get(f'{prefix}[first_name]', '').strip()
        last_name = form.get(f'{prefix}[last_name]', '').strip()
        role = form.get(f'{prefix}[role]', 'player').strip()

        if not first_name or not last_name:
            errors.append(f"Membre {index} : prénom et nom obligatoires.")
            index += 1
            continue

        # Photo
        photo_file = files.get(f'{prefix}[photo]')
        photo_path = save_upload(photo_file, 'members') if photo_file else None

        # Date de naissance
        birth_date = None
        raw_date = form.get(f'{prefix}[birth_date]', '').strip()
        if raw_date:
            try:
                birth_date = datetime.strptime(raw_date, '%Y-%m-%d').date()
            except ValueError:
                errors.append(f"Membre {index} : format de date invalide (YYYY-MM-DD attendu).")

        # ⚠️ Correction : on récupère "jersey" et non "jersey_number"
        jersey_raw = form.get(f'{prefix}[jersey]', '').strip()
        jersey_number = int(jersey_raw) if jersey_raw.isdigit() else None

        # Position (seulement pour player)
        position = form.get(f'{prefix}[position]', '').strip() or None

        member = TeamMember(
            team_id=team_id,
            role=role,
            first_name=first_name,
            last_name=last_name,
            birth_date=birth_date if role == 'player' else None,
            photo=photo_path['url'] if photo_path else None,
            photo_public_id=photo_path['public_id'] if photo_path else None,
            position=position if role == 'player' else None,
            jersey_number=jersey_number if role == 'player' else None,
        )

        db.session.add(member)
        index += 1

    return errors

@team.route('', methods=['GET'])
def get_all_teams():
    # try:
        teams = Team.query.all()
        return jsonify({
            'message': 'Teams retrieved successfully',
            'total': len(teams),
            'teams': [t.to_dict() for t in teams],
        }), 200
    # except Exception as e:
    #     return jsonify({'error': str(e)}), 500


@team.route('/<int:team_id>', methods=['GET'])
def get_team(team_id):
    try:
        t = Team.query.get(team_id)
        if not t:
            return jsonify({'error': 'Team not found'}), 404
        return jsonify({'message': 'Team retrieved successfully', 'team': t.to_dict()}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@team.route('/<int:team_id>', methods=['PUT'])
@jwt_required()
def update_team(team_id):
    try:
        user = get_authorized_user()
        t = Team.query.get(team_id)

        if not t:
            return jsonify({'error': 'Team not found'}), 404
        if not is_team_manager(user, t):
            return jsonify({'error': 'Unauthorized'}), 403

        data = request.form if request.form else request.get_json(silent=True) or {}

        if 'name' in data:
            new_name = data['name']
            if new_name != t.name and Team.query.filter_by(name=new_name).first():
                return jsonify({'error': 'Team name already exists'}), 409
            t.name = new_name

        if 'description' in data:
            t.description = data['description']

        if 'is_registered' in data:
            val = data['is_registered']
            t.is_registered = val if isinstance(val, bool) else str(val).lower() == 'true'

        # -------- LOGO UPDATE --------
        logo_file = request.files.get('logo')
        if logo_file:

            # Supprimer ancien logo si existe
            if t.logo_public_id:
                delete_from_cloudinary(t.logo_public_id)

            upload_result = save_upload(logo_file, 'logos')

            if upload_result:
                t.logo = upload_result["url"]
                t.logo_public_id = upload_result["public_id"]

        t.updated_at = datetime.utcnow()
        db.session.commit()

        return jsonify({
            'message': 'Team updated successfully',
            'team': t.to_dict()
        }), 200

    except Exception as e:
        current_app.logger.error(f"Update team error: {e}")
        return jsonify({'error': 'Server error'}), 500


@team.route('/<int:team_id>', methods=['DELETE'])
@jwt_required()
def delete_team(team_id):
    try:
        user = get_authorized_user()
        if user.role != 'super_admin':
            return jsonify({'error': 'Only super admin can delete teams'}), 403

        t = Team.query.get(team_id)
        if not t:
            return jsonify({'error': 'Team not found'}), 404

        db.session.delete(t)
        db.session.commit()
        return jsonify({'message': 'Team deleted successfully'}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


# ==========================================
# MEMBER ROUTES
# ==========================================


@team.route('/<int:team_id>/members', methods=['POST'])
@jwt_required()
def add_member(team_id):
    """Ajoute un seul membre à une équipe existante (multipart/form-data)."""
    try:
        user = get_authorized_user()
        t = Team.query.get(team_id)

        if not t:
            return jsonify({'error': 'Team not found'}), 404
        if not is_team_manager(user, t):
            return jsonify({'error': 'Unauthorized'}), 403

        form = request.form
        first_name = form.get('first_name', '').strip()
        last_name = form.get('last_name', '').strip()
        role = form.get('role', 'player').strip()

        if not first_name or not last_name:
            return jsonify({'error': 'first_name and last_name are required'}), 400

        license_number = form.get('license_number', '').strip() or None
        if license_number and TeamMember.query.filter_by(license_number=license_number).first():
            return jsonify({'error': 'License number already used'}), 409

        birth_date = None
        raw_date = form.get('birth_date', '').strip()
        if raw_date:
            try:
                birth_date = datetime.strptime(raw_date, '%Y-%m-%d').date()
            except ValueError:
                return jsonify({'error': 'Invalid birth_date format, expected YYYY-MM-DD'}), 400

        photo_path = save_upload(request.files.get('photo'), 'members')

        member = TeamMember(
            team_id=team_id,
            role=role,
            first_name=first_name,
            last_name=last_name,
            birth_date=birth_date if role == 'player' else None,
            photo=photo_path['url'] if photo_path else None,
            photo_public_id=photo_path['public_id'] if photo_path else None,
            position=form.get('position', '').strip() or None if role == 'player' else None,
            jersey_number=form.get('jersey_number', type=int) if role == 'player' else None,
            license_number=license_number if role == 'player' else None,
        )
        db.session.add(member)
        db.session.commit()

        return jsonify({'message': 'Member added successfully', 'member': member.to_dict()}), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@team.route('/<int:team_id>/members', methods=['GET'])
def get_team_members(team_id):
    try:
        t = Team.query.get(team_id)
        if not t:
            return jsonify({'error': 'Team not found'}), 404

        role_filter = request.args.get('role')  # ?role=player
        query = TeamMember.query.filter_by(team_id=team_id)
        if role_filter:
            query = query.filter_by(role=role_filter)

        members = query.all()
        return jsonify({
            'message': 'Members retrieved successfully',
            'total': len(members),
            'members': [m.to_dict() for m in members],
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@team.route('/<int:team_id>/members/<int:member_id>', methods=['DELETE'])
@jwt_required()
def remove_member(team_id, member_id):
    try:
        user = get_authorized_user()
        t = Team.query.get(team_id)
        member = TeamMember.query.get(member_id)

        if not t or not member:
            return jsonify({'error': 'Team or member not found'}), 404
        if member.team_id != team_id:
            return jsonify({'error': 'Member not in this team'}), 400
        if not is_team_manager(user, t):
            return jsonify({'error': 'Unauthorized'}), 403

        db.session.delete(member)
        db.session.commit()
        return jsonify({'message': 'Member removed successfully'}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@team.route('/<int:team_id>/members/<int:member_id>', methods=['PUT'])
@jwt_required()
def update_member(team_id, member_id):
    try:
        user = get_authorized_user()
        t = Team.query.get(team_id)
        member = TeamMember.query.get(member_id)

        if not t:
            return jsonify({'error': 'Team not found'}), 404
        if not member or member.team_id != team_id:
            return jsonify({'error': 'Member not found in this team'}), 404
        if not is_team_manager(user, t):
            return jsonify({'error': 'Unauthorized'}), 403

        form = request.form
        role = form.get('role', member.role).strip()

        if 'first_name' in form:
            member.first_name = form['first_name'].strip()
        if 'last_name' in form:
            member.last_name = form['last_name'].strip()

        member.role = role

        # Champs joueur
        if role == 'player':
            if 'position' in form:
                member.position = form['position'].strip() or None
            if 'jersey_number' in form:
                member.jersey_number = int(form['jersey_number']) if form['jersey_number'] else None
            if 'birth_date' in form and form['birth_date'].strip():
                try:
                    member.birth_date = datetime.strptime(form['birth_date'].strip(), '%Y-%m-%d').date()
                except ValueError:
                    return jsonify({'error': 'Invalid birth_date format, expected YYYY-MM-DD'}), 400
        else:
            # Si le rôle change et n'est plus joueur, on vide les champs sportifs
            member.position = None
            member.jersey_number = None
            member.birth_date = None

        # Photo
        photo_file = request.files.get('photo')
        if photo_file:
            path = save_upload(photo_file, 'members')
            if path:
                member.photo = path['url']
                member.photo_public_id = path['public_id']

        member.updated_at = datetime.utcnow()
        db.session.commit()

        return jsonify({'message': 'Member updated successfully', 'member': member.to_dict()}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# ==========================================
# REGISTRATION ROUTES
# ==========================================


@team.route('/<int:team_id>/registration', methods=['POST'])
@jwt_required()
def submit_registration(team_id):
    try:
        user = get_authorized_user()
        t = Team.query.get(team_id)

        if not t:
            return jsonify({'error': 'Team not found'}), 404
        if not is_team_manager(user, t):
            return jsonify({'error': 'Unauthorized'}), 403

        if TeamRegistration.query.filter_by(team_id=team_id).first():
            return jsonify({'error': 'Team already has a registration'}), 409

        data = request.get_json(silent=True) or {}
        registration = TeamRegistration(
            team_id=team_id,
            documents_submitted=data.get('documents'),
        )
        db.session.add(registration)
        db.session.commit()

        return jsonify({
            'message': 'Registration submitted successfully',
            'registration': registration.to_dict(),
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@team.route('/registrations', methods=['GET'])
@jwt_required()
def get_all_registrations():
    try:
        user = get_authorized_user()
        if user.role not in ['super_admin', 'admin_competition', 'operator']:
            return jsonify({'error': 'Unauthorized'}), 403

        status = request.args.get('status')
        query = TeamRegistration.query
        if status:
            query = query.filter_by(status=status)

        registrations = query.all()
        return jsonify({
            'message': 'Registrations retrieved successfully',
            'total': len(registrations),
            'registrations': [r.to_dict() for r in registrations],
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@team.route('/registrations/<int:reg_id>', methods=['GET'])
@jwt_required()
def get_registration(reg_id):
    try:
        registration = TeamRegistration.query.get(reg_id)
        if not registration:
            return jsonify({'error': 'Registration not found'}), 404
        return jsonify({
            'message': 'Registration retrieved successfully',
            'registration': registration.to_dict(),
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@team.route('/registrations/<int:reg_id>/validate', methods=['POST'])
@jwt_required()
def validate_registration(reg_id):
    try:
        user = get_authorized_user()
        if user.role not in ['super_admin', 'admin_competition', 'operator']:
            return jsonify({'error': 'Unauthorized'}), 403

        registration = TeamRegistration.query.get(reg_id)
        if not registration:
            return jsonify({'error': 'Registration not found'}), 404

        registration.status = RegistrationStatus.VALIDATED.value
        registration.validated_by_id = user.id
        registration.validation_date = datetime.utcnow()

        t = registration.team
        t.is_registered = True
        t.registration_date = datetime.utcnow()

        db.session.commit()
        return jsonify({
            'message': 'Registration validated successfully',
            'registration': registration.to_dict(),
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@team.route('/registrations/<int:reg_id>/reject', methods=['POST'])
@jwt_required()
def reject_registration(reg_id):
    try:
        user = get_authorized_user()
        if user.role not in ['super_admin', 'admin_competition', 'operator']:
            return jsonify({'error': 'Unauthorized'}), 403

        registration = TeamRegistration.query.get(reg_id)
        if not registration:
            return jsonify({'error': 'Registration not found'}), 404

        data = request.get_json(silent=True) or {}
        registration.status = RegistrationStatus.REJECTED.value
        registration.validated_by_id = user.id
        registration.validation_date = datetime.utcnow()
        registration.rejection_reason = data.get('reason')

        db.session.commit()
        return jsonify({
            'message': 'Registration rejected successfully',
            'registration': registration.to_dict(),
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500