import cloudinary.uploader
import os
from datetime import datetime

from flask import Blueprint, request, jsonify, current_app
from sqlalchemy.orm import joinedload
from flask_jwt_extended import jwt_required, get_jwt_identity

from olibo import db
from olibo.common.enums import RegistrationStatus
from olibo.common.helpers import get_authorized_user
from olibo.team.model import TeamMember, Team, TeamRegistration
from olibo.users.model import User

team = Blueprint('team', __name__)

# ─── Helpers ──────────────────────────────────────────────────────────────────

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
MAX_FILE_SIZE = 2 * 1024 * 1024  # 2 MB
MIN_PLAYERS = 7


def allowed_file(filename: str) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_upload(file, subfolder: str):
    if not file or file.filename == '':
        return None
    if not allowed_file(file.filename):
        return None

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


def is_team_manager(user, t):
    admin_roles = {'super_admin', 'admin_competition', 'operator', 'team_manager'}
    return t.representative_id == user.id or user.role in admin_roles


UNIQUE_ROLES = {'coach', 'assistant_coach', 'manager'}
_UNIQUE_ROLE_LABELS = {'coach': 'coach', 'assistant_coach': 'coach adjoint', 'manager': 'manager'}


def _validate_member_constraints(team_id, role, jersey_number, is_captain, exclude_member_id=None):
    q = TeamMember.query.filter(TeamMember.team_id == team_id)
    if exclude_member_id:
        q = q.filter(TeamMember.id != exclude_member_id)

    if role in UNIQUE_ROLES:
        if q.filter(TeamMember.role == role).first():
            return f"Cette équipe a déjà un {_UNIQUE_ROLE_LABELS[role]}"

    if is_captain:
        if q.filter(TeamMember.is_captain == True).first():
            return "Cette équipe a déjà un capitaine"

    if role == 'player' and jersey_number is not None:
        if q.filter(TeamMember.role == 'player', TeamMember.jersey_number == jersey_number).first():
            return f"Le numéro de dossard {jersey_number} est déjà attribué"

    return None


# ==========================================
# TEAM ROUTES
# ==========================================


@team.route('', methods=['POST'])
@jwt_required()
def create_team():
    try:
        user = get_authorized_user()
        if user.role not in ['super_admin', 'admin_competition', 'team_manager']:
            return jsonify({'error': 'Unauthorized'}), 403

        if 'name' not in request.form or not request.form['name'].strip():
            return jsonify({'error': 'Team name is required'}), 400

        if Team.query.filter_by(name=request.form['name']).first():
            return jsonify({'error': 'Team name already exists'}), 409

        logo = request.files.get('logo')
        logo_path = None

        if logo and logo.filename:
            logo_path = save_upload(logo, 'logos')

        is_admin = user.role in ['super_admin', 'admin_competition']

        new_team = Team(
            name=request.form['name'],
            logo=logo_path['url'] if logo_path else None,
            logo_public_id=logo_path['public_id'] if logo_path else None,
            representative_id= user.id,
            description=request.form.get('description'),
        )

        db.session.add(new_team)
        db.session.flush()

        errors = _add_members_from_form(request.form, request.files, new_team.id)

        if errors:
            db.session.rollback()
            return jsonify({'error': 'Invalid member data', 'details': errors}), 400

        reg_status = RegistrationStatus.VALIDATED.value if is_admin else RegistrationStatus.PENDING.value
        registration = TeamRegistration(
            team_id=new_team.id,
            status=reg_status,
            validated_by_id=user.id if is_admin else None,
            validation_date=datetime.utcnow() if is_admin else None,
        )
        db.session.add(registration)

        db.session.commit()

        return jsonify({
            'message': 'Team created successfully',
            'team': new_team.to_dict(),
        }), 201

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Create team error: {e}")
        return jsonify({'error': 'Server error'}), 500


def _add_members_from_form(form, files, team_id: int):
    errors = []
    index = 0
    seen_unique_roles = set()
    seen_jersey_numbers = set()
    captain_seen = False

    while f'members[{index}][role]' in form or f'members[{index}][first_name]' in form:
        prefix = f'members[{index}]'

        first_name = form.get(f'{prefix}[first_name]', '').strip()
        last_name = form.get(f'{prefix}[last_name]', '').strip()
        role = form.get(f'{prefix}[role]', 'player').strip()

        if not first_name or not last_name:
            errors.append(f"Membre {index} : prénom et nom obligatoires.")
            index += 1
            continue

        jersey_raw = form.get(f'{prefix}[jersey]', '').strip()
        jersey_number = int(jersey_raw) if jersey_raw.isdigit() else None
        is_captain_raw = form.get(f'{prefix}[is_captain]', 'false').lower() == 'true'

        if role in UNIQUE_ROLES and role in seen_unique_roles:
            errors.append(f"Membre {index} : cette équipe a déjà un {_UNIQUE_ROLE_LABELS[role]} dans cette liste.")
            index += 1
            continue
        if is_captain_raw and captain_seen:
            errors.append(f"Membre {index} : un capitaine est déjà désigné dans cette liste.")
            index += 1
            continue
        if role == 'player' and jersey_number is not None and jersey_number in seen_jersey_numbers:
            errors.append(f"Membre {index} : le numéro de dossard {jersey_number} est déjà attribué dans cette liste.")
            index += 1
            continue

        if role in UNIQUE_ROLES:
            seen_unique_roles.add(role)
        if is_captain_raw:
            captain_seen = True
        if role == 'player' and jersey_number is not None:
            seen_jersey_numbers.add(jersey_number)

        photo_file = files.get(f'{prefix}[photo]')
        photo_path = save_upload(photo_file, 'members') if photo_file else None

        birth_date = None
        raw_date = form.get(f'{prefix}[birth_date]', '').strip()
        if raw_date:
            try:
                birth_date = datetime.strptime(raw_date, '%Y-%m-%d').date()
            except ValueError:
                errors.append(f"Membre {index} : format de date invalide (YYYY-MM-DD attendu).")

        position = form.get(f'{prefix}[position]', '').strip() or None

        height_raw = form.get(f'{prefix}[height_cm]', '').strip()
        weight_raw = form.get(f'{prefix}[weight_kg]', '').strip()

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
            nationality=form.get(f'{prefix}[nationality]', '').strip() or None,
            nationality_label=form.get(f'{prefix}[nationality_label]', '').strip() or None,
            preferred_foot=form.get(f'{prefix}[preferred_foot]', '').strip() or None,
            height_cm=int(height_raw) if height_raw.isdigit() else None,
            weight_kg=int(weight_raw) if weight_raw.isdigit() else None,
            gender=form.get(f'{prefix}[gender]', '').strip() or None,
            category=form.get(f'{prefix}[category]', '').strip() or None,
            is_captain=is_captain_raw,
        )

        db.session.add(member)
        index += 1

    return errors


def _unset_team_captain(team_id: int, exclude_member_id: int = None):
    """Retire le brassard de tous les membres de l'équipe sauf celui exclu."""
    q = TeamMember.query.filter_by(team_id=team_id, is_captain=True)
    if exclude_member_id:
        q = q.filter(TeamMember.id != exclude_member_id)
    q.update({'is_captain': False})


@team.route('', methods=['GET'])
def get_all_teams():
    try:
        teams = Team.query.options(joinedload(Team.registration)).all()
        result = []
        for t in teams:
            data = t.to_dict()
            data['registration'] = t.registration.to_dict() if t.registration else None
            result.append(data)
        return jsonify({
            'message': 'Teams retrieved successfully',
            'total': len(result),
            'teams': result,
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@team.route('/my-teams', methods=['GET'])
@jwt_required()
def get_my_teams():
    try:
        user = get_authorized_user()
        admin_roles = {'super_admin', 'admin_competition', 'operator'}

        query = Team.query.options(joinedload(Team.registration))
        if user.role not in admin_roles:
            query = query.filter_by(representative_id=user.id)

        teams = query.all()
        result = []
        for t in teams:
            data = t.to_dict()
            data['registration'] = t.registration.to_dict() if t.registration else None
            result.append(data)

        return jsonify({
            'message': 'Teams retrieved successfully',
            'total': len(result),
            'teams': result,
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@team.route('/<int:team_id>', methods=['GET'])
def get_team(team_id):
    try:
        t = (
            Team.query
            .options(joinedload(Team.registration))
            .filter_by(id=team_id)
            .first()
        )
        if not t:
            return jsonify({'error': 'Team not found'}), 404
        data = t.to_dict()
        data['registration'] = t.registration.to_dict() if t.registration else None
        return jsonify({'message': 'Team retrieved successfully', 'team': data}), 200
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

        logo_file = request.files.get('logo')
        if logo_file:
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
        return '', 204

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


# ==========================================
# MEMBER ROUTES
# ==========================================


@team.route('/<int:team_id>/members', methods=['POST'])
@jwt_required()
def add_member(team_id):
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

        is_captain = form.get('is_captain', 'false').lower() == 'true'
        jersey_number = form.get('jersey_number', type=int) if role == 'player' else None

        error = _validate_member_constraints(team_id, role, jersey_number, is_captain)
        if error:
            return jsonify({'error': error}), 409

        birth_date = None
        raw_date = form.get('birth_date', '').strip()
        if raw_date:
            try:
                birth_date = datetime.strptime(raw_date, '%Y-%m-%d').date()
            except ValueError:
                return jsonify({'error': 'Invalid birth_date format, expected YYYY-MM-DD'}), 400

        photo_path = save_upload(request.files.get('photo'), 'members')

        if is_captain:
            _unset_team_captain(team_id)

        member = TeamMember(
            team_id=team_id,
            role=role,
            first_name=first_name,
            last_name=last_name,
            birth_date=birth_date if role == 'player' else None,
            photo=photo_path['url'] if photo_path else None,
            photo_public_id=photo_path['public_id'] if photo_path else None,
            position=form.get('position', '').strip() or None if role == 'player' else None,
            jersey_number=jersey_number,
            nationality=form.get('nationality', '').strip() or None,
            nationality_label=form.get('nationality_label', '').strip() or None,
            preferred_foot=form.get('preferred_foot', '').strip() or None,
            height_cm=form.get('height_cm', type=int),
            weight_kg=form.get('weight_kg', type=int),
            gender=form.get('gender', '').strip() or None,
            category=form.get('category', '').strip() or None,
            is_captain=is_captain,
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

        role_filter = request.args.get('role')
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
    # try:
        user = get_authorized_user()
        t = Team.query.get(team_id)
        member = TeamMember.query.get(member_id)

        if not t or not member:
            return jsonify({'error': 'Team or member not found'}), 404
        if member.team_id != team_id:
            return jsonify({'error': 'Member not in this team'}), 400
        if not is_team_manager(user, t):
            return jsonify({'error': 'Unauthorized'}), 403

        if member.photo_public_id:
            delete_from_cloudinary(member.photo_public_id)

        db.session.delete(member)
        db.session.commit()
        return '', 204


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

        new_jersey = member.jersey_number
        if role == 'player' and 'jersey_number' in form:
            new_jersey = int(form['jersey_number']) if form['jersey_number'].strip() else None
        elif role != 'player':
            new_jersey = None

        new_is_captain = form['is_captain'].lower() == 'true' if 'is_captain' in form else member.is_captain

        error = _validate_member_constraints(team_id, role, new_jersey, new_is_captain, exclude_member_id=member_id)
        if error:
            return jsonify({'error': error}), 409

        if 'first_name' in form:
            member.first_name = form['first_name'].strip()
        if 'last_name' in form:
            member.last_name = form['last_name'].strip()

        member.role = role

        if role == 'player':
            if 'position' in form:
                member.position = form['position'].strip() or None
            if 'jersey_number' in form:
                member.jersey_number = new_jersey
            if 'birth_date' in form and form['birth_date'].strip():
                try:
                    member.birth_date = datetime.strptime(form['birth_date'].strip(), '%Y-%m-%d').date()
                except ValueError:
                    return jsonify({'error': 'Invalid birth_date format, expected YYYY-MM-DD'}), 400
        else:
            member.position = None
            member.jersey_number = None
            member.birth_date = None

        if 'nationality' in form:
            member.nationality = form['nationality'].strip() or None
        if 'nationality_label' in form:
            member.nationality_label = form['nationality_label'].strip() or None
        if 'preferred_foot' in form:
            member.preferred_foot = form['preferred_foot'].strip() or None
        if 'height_cm' in form:
            member.height_cm = int(form['height_cm']) if form['height_cm'].strip() else None
        if 'weight_kg' in form:
            member.weight_kg = int(form['weight_kg']) if form['weight_kg'].strip() else None
        if 'gender' in form:
            member.gender = form['gender'].strip() or None
        if 'category' in form:
            member.category = form['category'].strip() or None
        if 'is_captain' in form:
            new_val = form['is_captain'].lower() == 'true'
            if new_val:
                _unset_team_captain(team_id, exclude_member_id=member_id)
            member.is_captain = new_val

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


@team.route('/<int:team_id>/members/<int:member_id>/set_captain', methods=['POST'])
@jwt_required()
def set_captain(team_id, member_id):
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

        _unset_team_captain(team_id)
        member.is_captain = True
        member.updated_at = datetime.utcnow()
        db.session.commit()

        return jsonify({'message': 'Captain set successfully', 'member': member.to_dict()}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


# ==========================================
# REGISTRATION ROUTES
# ==========================================


def _generate_team_licenses(team_id: int):
    """Génère les licences manquantes pour tous les joueurs actifs d'une équipe."""
    from olibo.license.model import License
    from olibo.season.model import Season
    active_season = Season.query.filter_by(is_active=True).first()
    if not active_season:
        current_app.logger.warning('No active season found: skipping license generation')
        return

    season_label = active_season.label
    season_id = active_season.id

    issue_date = datetime(
        active_season.start_date.year,
        active_season.start_date.month,
        active_season.start_date.day,
    )
    expiry_date = datetime(
        active_season.end_date.year,
        active_season.end_date.month,
        active_season.end_date.day,
    )

    players = TeamMember.query.filter_by(team_id=team_id, role='player', is_active=True).all()
    for player in players:
        license_number = f"OL-{season_label}-{team_id:03d}-{player.id:03d}"
        existing = License.query.filter_by(member_id=player.id, season_id=season_id).first()

        if existing:
            if existing.is_valid:
                continue
            if existing.license_number != license_number:
                if License.query.filter_by(license_number=license_number).first():
                    continue
                existing.license_number = license_number
            existing.is_valid = True
            existing.issue_date = issue_date
            existing.expiry_date = expiry_date
            continue

        if License.query.filter_by(license_number=license_number).first():
            continue

        db.session.add(License(
            member_id=player.id,
            season_id=season_id,
            license_number=license_number,
            issue_date=issue_date,
            expiry_date=expiry_date,
        ))


@team.route('/<int:team_id>/registration', methods=['GET'])
@jwt_required()
def get_team_registration(team_id):
    try:
        user = get_authorized_user()
        t = Team.query.get(team_id)

        if not t:
            return jsonify({'error': 'Team not found'}), 404
        if not is_team_manager(user, t):
            return jsonify({'error': 'Unauthorized'}), 403

        registration = TeamRegistration.query.filter_by(team_id=team_id).first()
        if not registration:
            return jsonify({'message': 'No registration found', 'registration': None}), 200

        return jsonify({'registration': registration.to_dict()}), 200

    except Exception as e:
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


@team.route('/registrations/<int:reg_id>/status', methods=['PATCH'])
@jwt_required()
def update_registration_status(reg_id):
    try:
        user = get_authorized_user()
        if user.role not in ['super_admin', 'admin_competition', 'operator']:
            return jsonify({'error': 'Unauthorized'}), 403

        registration = TeamRegistration.query.get(reg_id)
        if not registration:
            return jsonify({'error': 'Registration not found'}), 404

        data = request.get_json(silent=True) or {}
        new_status = data.get('status')
        valid_statuses = [s.value for s in RegistrationStatus]
        if new_status not in valid_statuses:
            return jsonify({'error': f'Invalid status. Must be one of: {valid_statuses}'}), 400

        t = registration.team

        if new_status == RegistrationStatus.VALIDATED.value:
            registration.status = RegistrationStatus.VALIDATED.value
            registration.validated_by_id = user.id
            registration.validation_date = datetime.utcnow()
            registration.rejection_reason = None
            _generate_team_licenses(t.id)

        elif new_status == RegistrationStatus.REJECTED.value:
            registration.status = RegistrationStatus.REJECTED.value
            registration.validated_by_id = user.id
            registration.validation_date = datetime.utcnow()
            registration.rejection_reason = data.get('rejection_reason')

        elif new_status == RegistrationStatus.PENDING.value:
            registration.status = RegistrationStatus.PENDING.value
            registration.validated_by_id = None
            registration.validation_date = None
            registration.rejection_reason = None

        db.session.commit()
        return jsonify({
            'message': 'Registration status updated successfully',
            'registration': registration.to_dict(),
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@team.route('/registrations/<int:reg_id>/validate', methods=['POST'])
@jwt_required()
def validate_registration(reg_id):
    # try:
        user = get_authorized_user()
        if user.role not in ['super_admin', 'admin_competition', 'operator']:
            return jsonify({'error': 'Unauthorized'}), 403

        registration = TeamRegistration.query.get(reg_id)
        if not registration:
            return jsonify({'error': 'Registration not found'}), 404

        if registration.status == RegistrationStatus.VALIDATED.value:
            return jsonify({'error': 'Registration already validated'}), 409

        registration.status = RegistrationStatus.VALIDATED.value
        registration.validated_by_id = user.id
        registration.validation_date = datetime.utcnow()
        registration.rejection_reason = None

        t = registration.team
        _generate_team_licenses(t.id)

        db.session.commit()
        return jsonify({
            'message': 'Registration validated successfully',
            'registration': registration.to_dict(),
        }), 200

    # except Exception as e:
    #     db.session.rollback()
    #     return jsonify({'error': str(e)}), 500


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
