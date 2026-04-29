# Audit Backend — Olibo League
> Révision module par module · Avril 2026

---

## Légende
- 🔴 Bug / faille de sécurité — à corriger immédiatement
- 🟠 Problème fonctionnel — endpoint incomplet ou incohérent
- 🟡 Amélioration — robustesse, maintenabilité
- ✅ Correct — ne pas toucher

---

## 1. Auth (`/api/auth`)

### État global : 60% — fondations OK, sécurité insuffisante

### Problèmes

#### 🔴 Register accepte n'importe quel rôle en input libre
```python
# ACTUEL — n'importe qui peut se déclarer super_admin
user = User(role=data['role'])

# CORRECTION
ALLOWED_SELF_REGISTER_ROLES = ['team_captain', 'coach', 'spectator']

if data['role'] not in ALLOWED_SELF_REGISTER_ROLES:
    return jsonify({'error': 'Invalid role for self-registration'}), 403
```

#### 🔴 Import mort + bug sur logout
```python
# ACTUEL — Token importé depuis contextvars (faux), logout va planter
from contextvars import Token
Token.query.filter_by(user_id=user_id).delete()  # ← AttributeError à l'exécution

# CORRECTION — importer depuis le bon module
from olibo.auth.model import Token
```

#### 🔴 Pas de protection brute-force sur /login
Aucune limitation de tentatives. Avec un username connu (téléphone), mot de passe crackable par force brute.

```python
# Ajouter flask-limiter
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@auth.route('/login', methods=['POST'])
@limiter.limit("5 per minute")
def login():
    ...
```
Initialiser dans `create_app()` : `limiter.init_app(app)`

#### 🟠 refresh_token utilise le même access token
Un access token ne devrait pas servir à se rafraîchir lui-même. Il faut un refresh token dédié avec durée longue, et un access token de courte durée.

```python
# Dans create_app(), ajouter :
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=2)  # au lieu de 30 jours
app.config['JWT_REFRESH_TOKEN_EXPIRES'] = timedelta(days=30)

# Dans login(), générer les deux :
access_token = create_access_token(identity=str(user.id), additional_claims={...})
refresh_token = create_refresh_token(identity=str(user.id))

return jsonify({
    'access_token': access_token,
    'refresh_token': refresh_token,
    'user': user.to_dict()
}), 200

# Route refresh — utiliser jwt_required(refresh=True)
@auth.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh_token():
    user_id = get_jwt_identity()
    new_token = create_access_token(identity=user_id, additional_claims={...})
    return jsonify({'access_token': new_token}), 200
```

#### 🟠 setup-complete utilise POST mais c'est une lecture
```python
# CORRECTION — changer en GET
@auth.route('/setup-complete', methods=['GET'])
def setup_complete():
    ...
```

#### 🟠 check-superadmin a son try/except commenté
```python
# ACTUEL — exception non gérée si DB down
@auth.route('/check-superadmin', methods=['GET'])
def check_superadmin():
    # try:  ← commenté
    superadmin = User.query.filter_by(role='super_admin').first()

# CORRECTION
@auth.route('/check-superadmin', methods=['GET'])
def check_superadmin():
    try:
        superadmin = User.query.filter_by(role='super_admin').first()
        return jsonify({'exists': superadmin is not None}), 200
    except Exception as e:
        return jsonify({'error': str(e), 'exists': False}), 500
```

#### 🟡 Pas de validation du rôle contre l'enum
```python
from olibo.common.enums import UserRole

valid_roles = [r.value for r in UserRole]
if data['role'] not in valid_roles:
    return jsonify({'error': f'Invalid role. Allowed: {valid_roles}'}), 400
```

#### 🟡 Endpoint manquant — GET /me
Les clients ont besoin de récupérer le profil de l'utilisateur connecté.
```python
@auth.route('/me', methods=['GET'])
@jwt_required()
def get_me():
    user = User.query.get(get_jwt_identity())
    if not user:
        return jsonify({'error': 'User not found'}), 404
    return jsonify({'user': user.to_dict()}), 200
```

### Checklist Auth
- [ ] Bloquer les rôles sensibles sur `/register`
- [ ] Corriger l'import `Token`
- [ ] Ajouter `flask-limiter` sur `/login`
- [ ] Séparer access token (2h) et refresh token (30j)
- [ ] Passer `setup-complete` en GET
- [ ] Décommenter le try/except de `check-superadmin`
- [ ] Valider le rôle contre l'enum
- [ ] Ajouter `GET /me`

---

## 2. Users (`/api/users`)

### État global : 75% — CRUD OK, contrôles d'accès à affiner

### Problèmes

#### 🔴 Rôle 'admin' inexistant dans les contrôles
```python
# ACTUEL — 'admin' n'existe pas dans UserRole
if current_user.role not in ['super_admin', 'admin']:

# CORRECTION
if current_user.role not in ['super_admin', 'admin_competition']:
```

#### 🟠 get_all_users accessible à tous les utilisateurs authentifiés
N'importe quel joueur connecté peut lister tous les comptes. À restreindre.

```python
@users.route('', methods=['GET'])
@jwt_required()
def get_all_users():
    current_user = get_authorized_user()
    
    # Seuls les admins peuvent lister tous les utilisateurs
    if current_user.role not in ['super_admin', 'admin_competition', 'operator']:
        return jsonify({'error': 'Unauthorized'}), 403
    ...
```

#### 🟠 get_user accessible à tous — aucune restriction
Un joueur peut récupérer le profil de n'importe quel autre utilisateur (email, téléphone, rôle).

```python
@users.route('/<int:user_id>', methods=['GET'])
@jwt_required()
def get_user(user_id):
    current_user = get_authorized_user()
    
    # Un user peut voir son propre profil, les admins peuvent voir tous
    if current_user.id != user_id and current_user.role not in ['super_admin', 'admin_competition']:
        return jsonify({'error': 'Unauthorized'}), 403
    ...
```

#### 🟠 update_user permet le changement de mot de passe sans vérifier l'ancien
```python
# ACTUEL — n'importe qui peut changer son mot de passe sans confirmation
if 'password' in data:
    user.password_hash = generate_password_hash(data['password'])

# CORRECTION — exiger l'ancien mot de passe sauf si super_admin
if 'password' in data:
    if current_user.role != 'super_admin':
        old_password = data.get('old_password')
        if not old_password or not check_password_hash(user.password_hash, old_password):
            return jsonify({'error': 'Current password is required and must be correct'}), 400
    user.password_hash = generate_password_hash(data['password'])
```

#### 🟡 Pas de pagination sur get_all_users
Avec 500+ participants, le GET sans pagination va charger toute la table.

```python
@users.route('', methods=['GET'])
@jwt_required()
def get_all_users():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    per_page = min(per_page, 100)  # cap max
    
    # ... filtres ...
    
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    
    return jsonify({
        'users': [u.to_dict() for u in pagination.items],
        'total': pagination.total,
        'page': page,
        'pages': pagination.pages,
        'per_page': per_page
    }), 200
```

#### 🟡 Endpoint manquant — GET /users/me/profile
Distinct de `/auth/me`, ce endpoint pourrait exposer des informations enrichies (équipe, etc.)

#### 🟡 Validation du rôle à l'update
```python
if 'role' in data and current_user.role == 'super_admin':
    role_value = data['role']['value'] if isinstance(data['role'], dict) else data['role']
    valid_roles = [r.value for r in UserRole]
    if role_value not in valid_roles:
        return jsonify({'error': 'Invalid role'}), 400
    user.role = role_value
```

### Checklist Users
- [ ] Corriger `'admin'` → `'admin_competition'`
- [ ] Restreindre `GET /` aux admins
- [ ] Restreindre `GET /:id` à l'utilisateur lui-même ou admins
- [ ] Exiger l'ancien mot de passe pour le changement
- [ ] Ajouter pagination
- [ ] Valider le rôle contre l'enum à l'update

---

## 3. Teams (`/api/team`)

### État global : 80% — le module le plus avancé, quelques trous

### Problèmes

#### 🔴 create_team sans @jwt_required()
N'importe qui (non authentifié) peut créer une équipe.

```python
# ACTUEL — pas de décorateur JWT
@team.route('', methods=['POST'])
def create_team():

# CORRECTION
@team.route('', methods=['POST'])
@jwt_required()
def create_team():
    user = get_authorized_user()
    if user.role not in ['super_admin', 'admin_competition', 'team_captain']:
        return jsonify({'error': 'Unauthorized'}), 403
    ...
```

#### 🔴 create_team et get_all_teams ont leurs try/except commentés
En production, une exception non catchée retourne une stacktrace HTML de Flask (fuite d'information).

```python
# Décommenter et nettoyer les blocs try/except dans les deux routes
@team.route('', methods=['POST'])
@jwt_required()
def create_team():
    try:
        ...
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Create team error: {e}")
        return jsonify({'error': 'Server error'}), 500
```

#### 🔴 Imports Google Drive inutilisés — dead code + dépendances inutiles
```python
# ACTUEL — imports jamais utilisés, alourdit l'app et peut planter si pas installé
from google.oauth2 import service_account
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

# CORRECTION — supprimer ces 4 lignes
```

#### 🟠 remove_member ne supprime pas la photo sur Cloudinary
Fuite de stockage à chaque suppression de membre.

```python
@team.route('/<int:team_id>/members/<int:member_id>', methods=['DELETE'])
@jwt_required()
def remove_member(team_id, member_id):
    ...
    # Avant db.session.delete(member) :
    if member.photo_public_id:
        delete_from_cloudinary(member.photo_public_id)
    
    db.session.delete(member)
    db.session.commit()
```

#### 🟠 validate_registration ne vérifie pas le statut courant
On peut re-valider une inscription déjà rejetée.

```python
@team.route('/registrations/<int:reg_id>/validate', methods=['POST'])
@jwt_required()
def validate_registration(reg_id):
    ...
    if registration.status == RegistrationStatus.VALIDATED.value:
        return jsonify({'error': 'Registration already validated'}), 409
    
    if registration.status == RegistrationStatus.REJECTED.value:
        return jsonify({'error': 'Cannot validate a rejected registration. Create a new one.'}), 409
    ...
```

#### 🟠 Soumission d'inscription sans vérification du nombre minimum de joueurs
```python
@team.route('/<int:team_id>/registration', methods=['POST'])
@jwt_required()
def submit_registration(team_id):
    ...
    MIN_PLAYERS = 7  # à ajuster selon le règlement Olibo
    player_count = TeamMember.query.filter_by(team_id=team_id, role='player').count()
    if player_count < MIN_PLAYERS:
        return jsonify({
            'error': f'Team must have at least {MIN_PLAYERS} players to register. Current: {player_count}'
        }), 400
    ...
```

#### 🟡 is_team_manager trop restrictif
L'`admin_competition` et l'`operator` devraient pouvoir gérer les équipes aussi.

```python
# ACTUEL
def is_team_manager(user, t):
    return t.captain_id == user.id or user.role == 'super_admin'

# CORRECTION
def is_team_manager(user, t):
    admin_roles = {'super_admin', 'admin_competition', 'operator'}
    return t.captain_id == user.id or user.role in admin_roles
```

#### 🟡 Endpoint manquant — GET /team/:id/registration
Pour qu'un capitaine puisse consulter l'état de son inscription sans passer par la liste admin.

```python
@team.route('/<int:team_id>/registration', methods=['GET'])
@jwt_required()
def get_team_registration(team_id):
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
```

### Checklist Teams
- [ ] Ajouter `@jwt_required()` sur `create_team`
- [ ] Décommenter les try/except
- [ ] Supprimer les imports Google Drive
- [ ] Supprimer photo Cloudinary sur `remove_member`
- [ ] Vérifier statut avant validation d'inscription
- [ ] Ajouter contrôle nombre minimum de joueurs
- [ ] Élargir `is_team_manager`
- [ ] Ajouter `GET /:id/registration`

---

## 4. Competition (`/api/competition`)

### État global : 85% — propre, quelques validations métier manquantes

### Problèmes

#### 🟠 Pas de validation end_date > start_date
```python
start = datetime.fromisoformat(data['start_date'])
end   = datetime.fromisoformat(data['end_date'])

if end <= start:
    return jsonify({'error': 'end_date must be after start_date'}), 400

competition = Competition(start_date=start, end_date=end, ...)
```

#### 🟠 Pas de contrôle d'unicité sur le numéro de saison
Deux compétitions pour la même saison peuvent coexister silencieusement.

```python
if Competition.query.filter_by(season=data['season']).first():
    return jsonify({'error': f"A competition for season {data['season']} already exists"}), 409
```

#### 🟠 delete_competition supprime en cascade sans avertissement
Supprimer une compétition efface tous les matchs, feuilles de match et classements. Il faut au moins vérifier si elle a des matchs joués.

```python
from olibo.match_sheet.model import Match

played_matches = Match.query.filter_by(
    competition_id=comp_id, 
    status='completed'
).count()

if played_matches > 0:
    return jsonify({
        'error': f'Cannot delete a competition with {played_matches} played matches. Archive it instead.'
    }), 409
```

#### 🟡 Endpoint manquant — GET /competition/active
Le frontend a besoin de récupérer la compétition en cours sans connaître l'ID.

```python
@competition.route('/active', methods=['GET'])
def get_active_competition():
    try:
        comp = Competition.query.filter_by(is_active=True).first()
        if not comp:
            return jsonify({'message': 'No active competition', 'competition': None}), 200
        return jsonify({'competition': comp.to_dict()}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
```

#### 🟡 Pas de protection contre plusieurs compétitions actives simultanément
```python
# Dans create_competition et update_competition :
if data.get('is_active', True):
    Competition.query.filter(Competition.id != comp_id).update({'is_active': False})
```

### Checklist Competition
- [ ] Valider `end_date > start_date`
- [ ] Unicité de la saison
- [ ] Bloquer suppression si matchs joués
- [ ] Ajouter `GET /active`
- [ ] Une seule compétition active à la fois

---

## 5. Match Sheet (`/api/match_sheet`)

### État global : 70% — structure solide, logique métier incomplète

### Problèmes

#### 🔴 fill_match_sheet passe directement en COMPLETED
Le match saute l'état `in_progress`. Impossible de modifier le score pendant le match.

```python
# ACTUEL
match.status = MatchStatus.COMPLETED.value

# CORRECTION — distinguer saisie en cours et clôture
# Dans fill_match_sheet : passer en in_progress
match.status = MatchStatus.IN_PROGRESS.value

# Ajouter une route dédiée pour clôturer
@match_sheet.route('/matches/<int:match_id>/close', methods=['POST'])
@jwt_required()
def close_match(match_id):
    user = get_authorized_user()
    if user.role not in ['referee', 'commissioner']:
        return jsonify({'error': 'Unauthorized'}), 403
    
    match = Match.query.get(match_id)
    if not match or match.status != MatchStatus.IN_PROGRESS.value:
        return jsonify({'error': 'Match is not in progress'}), 400
    
    match.status = MatchStatus.COMPLETED.value
    db.session.commit()
    
    # Déclencher le recalcul du classement
    from olibo.ranking.utilities import recalculate_rankings
    recalculate_rankings(match.competition_id)
    
    return jsonify({'message': 'Match closed', 'match': match.to_dict()}), 200
```

#### 🔴 Recalcul du classement non déclenché après clôture du match
Voir section Ranking ci-dessous.

#### 🟠 event_type non validé contre les valeurs autorisées
```python
# ACTUEL — n'importe quelle chaîne acceptée
event = MatchEvent(event_type=data['event_type'], ...)

# CORRECTION
VALID_EVENT_TYPES = {'goal', 'assist', 'yellow_card', 'red_card', 'substitution'}
if data['event_type'] not in VALID_EVENT_TYPES:
    return jsonify({'error': f"Invalid event_type. Allowed: {list(VALID_EVENT_TYPES)}"}), 400
```

#### 🟠 Minute non validée
```python
minute = data['minute']
if not isinstance(minute, int) or minute < 0 or minute > 130:
    return jsonify({'error': 'Minute must be an integer between 0 and 130'}), 400
```

#### 🟠 Modification d'une feuille déjà validée non bloquée
```python
# Dans fill_match_sheet et add_match_event
sheet = MatchSheet.query.filter_by(match_id=match_id).first()
if sheet and sheet.is_validated:
    return jsonify({'error': 'Match sheet is already validated and cannot be modified'}), 409
```

#### 🟠 Endpoints manquants
```
GET  /api/match_sheet/matches/:id/sheet       — lire la feuille de match
DELETE /api/match_sheet/matches/:id/events/:event_id  — corriger un événement
PUT  /api/match_sheet/matches/:id             — modifier date/heure/lieu d'un match
```

```python
# Exemple GET sheet
@match_sheet.route('/matches/<int:match_id>/sheet', methods=['GET'])
def get_match_sheet(match_id):
    match = Match.query.get(match_id)
    if not match:
        return jsonify({'error': 'Match not found'}), 404
    
    sheet = MatchSheet.query.filter_by(match_id=match_id).first()
    events = MatchEvent.query.filter_by(match_id=match_id).order_by(MatchEvent.minute).all()
    
    return jsonify({
        'match': match.to_dict(),
        'sheet': sheet.to_dict() if sheet else None,
        'events': [e.to_dict() for e in events]
    }), 200
```

### Checklist Match Sheet
- [ ] Séparer `in_progress` et `completed`
- [ ] Déclencher `recalculate_rankings` à la clôture
- [ ] Valider `event_type` contre enum
- [ ] Valider la minute (0–130)
- [ ] Bloquer modification si feuille validée
- [ ] Ajouter `GET /matches/:id/sheet`
- [ ] Ajouter `DELETE /matches/:id/events/:event_id`
- [ ] Ajouter `PUT /matches/:id` (update planification)

---

## 6. Ranking (`/api/ranking`)

### État global : 25% — modèle OK, logique métier inexistante

### Problème principal

#### 🔴 update_rankings est vide — le cœur du module n'existe pas

Créer le fichier `olibo/ranking/utilities.py` :

```python
# olibo/ranking/utilities.py
from olibo import db
from olibo.ranking.model import Ranking
from olibo.match_sheet.model import Match
from olibo.common.enums import MatchStatus


def recalculate_rankings(competition_id: int) -> None:
    """
    Recalcule et persiste le classement complet d'une compétition
    à partir de tous les matchs terminés.
    Appelé après chaque clôture de match.
    """
    completed_matches = Match.query.filter_by(
        competition_id=competition_id,
        status=MatchStatus.COMPLETED.value
    ).all()

    # Agréger les stats par équipe
    stats: dict[int, dict] = {}

    def init_team(team_id):
        if team_id not in stats:
            stats[team_id] = {
                'matches_played': 0, 'wins': 0, 'draws': 0,
                'losses': 0, 'goals_for': 0, 'goals_against': 0
            }

    for match in completed_matches:
        h, a = match.home_team_id, match.away_team_id
        hg, ag = match.home_team_goals, match.away_team_goals

        init_team(h)
        init_team(a)

        stats[h]['matches_played'] += 1
        stats[a]['matches_played'] += 1
        stats[h]['goals_for']      += hg
        stats[h]['goals_against']  += ag
        stats[a]['goals_for']      += ag
        stats[a]['goals_against']  += hg

        if hg > ag:
            stats[h]['wins']   += 1
            stats[a]['losses'] += 1
        elif hg == ag:
            stats[h]['draws'] += 1
            stats[a]['draws'] += 1
        else:
            stats[a]['wins']   += 1
            stats[h]['losses'] += 1

    # Calculer points et goal difference
    for team_id, s in stats.items():
        s['points']          = s['wins'] * 3 + s['draws']
        s['goal_difference'] = s['goals_for'] - s['goals_against']

    # Trier : points DESC, goal_difference DESC, goals_for DESC
    sorted_teams = sorted(
        stats.items(),
        key=lambda x: (x[1]['points'], x[1]['goal_difference'], x[1]['goals_for']),
        reverse=True
    )

    # Upsert dans la table rankings
    for position, (team_id, s) in enumerate(sorted_teams, start=1):
        ranking = Ranking.query.filter_by(
            competition_id=competition_id,
            team_id=team_id
        ).first()

        if ranking:
            ranking.position        = position
            ranking.matches_played  = s['matches_played']
            ranking.wins            = s['wins']
            ranking.draws           = s['draws']
            ranking.losses          = s['losses']
            ranking.goals_for       = s['goals_for']
            ranking.goals_against   = s['goals_against']
            ranking.goal_difference = s['goal_difference']
            ranking.points          = s['points']
        else:
            ranking = Ranking(
                competition_id=competition_id,
                team_id=team_id,
                position=position,
                **s
            )
            db.session.add(ranking)

    db.session.commit()
```

Mettre à jour `routes.py` :
```python
from olibo.ranking.utilities import recalculate_rankings

@ranking.route('', methods=['POST'])
@jwt_required()
def update_rankings():
    user = User.query.get(get_jwt_identity())
    if user.role not in ['super_admin', 'admin_competition', 'operator']:
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.get_json()
    if 'competition_id' not in data:
        return jsonify({'error': 'competition_id is required'}), 400
    
    competition = Competition.query.get(data['competition_id'])
    if not competition:
        return jsonify({'error': 'Competition not found'}), 404
    
    recalculate_rankings(data['competition_id'])
    
    rankings = Ranking.query.filter_by(
        competition_id=data['competition_id']
    ).order_by(Ranking.position).all()
    
    return jsonify({
        'message': 'Rankings recalculated successfully',
        'rankings': [r.to_dict() for r in rankings]
    }), 200
```

### Checklist Ranking
- [ ] Créer `utilities.py` avec `recalculate_rankings()`
- [ ] Brancher l'appel dans `close_match` (match_sheet)
- [ ] Mettre à jour le `POST /` pour appeler `recalculate_rankings`
- [ ] Ajouter `GET /ranking/competition/:id/team/:team_id` pour les stats individuelles

---

## 7. Voting (`/api/voting`)

### État global : 80% — logique solide, quelques validations manquantes

### Problèmes

#### 🟠 vote_type non validé contre l'enum
```python
from olibo.common.enums import VoteType

valid_vote_types = [v.value for v in VoteType]
if data['vote_type'] not in valid_vote_types:
    return jsonify({'error': f"Invalid vote_type. Allowed: {valid_vote_types}"}), 400
```

#### 🟠 Pas de vérification que la compétition est active
```python
if not competition.is_active:
    return jsonify({'error': 'Voting is only allowed for active competitions'}), 400
```

#### 🟠 matchday obligatoire pour player_of_day
```python
if data['vote_type'] == 'player_of_day' and not data.get('matchday'):
    return jsonify({'error': 'matchday is required for player_of_day votes'}), 400
```

#### 🟠 VoteResult orphelin si vote_count tombe à 0
```python
# Dans delete_vote, après décrémentation :
if result and result.vote_count <= 0:
    db.session.delete(result)
```

#### 🟡 Endpoint manquant — GET /voting/has-voted
Le frontend doit savoir si l'utilisateur courant a déjà voté pour désactiver le bouton.

```python
@voting.route('/has-voted', methods=['GET'])
@jwt_required()
def has_voted():
    voter_id    = get_jwt_identity()
    vote_type   = request.args.get('vote_type')
    comp_id     = request.args.get('competition_id', type=int)
    matchday    = request.args.get('matchday', type=int)

    existing = Vote.query.filter_by(
        voter_id=voter_id,
        vote_type=vote_type,
        competition_id=comp_id,
        matchday=matchday
    ).first()

    return jsonify({'has_voted': existing is not None}), 200
```

### Checklist Voting
- [ ] Valider `vote_type` contre enum
- [ ] Vérifier compétition active
- [ ] `matchday` obligatoire pour `player_of_day`
- [ ] Supprimer `VoteResult` si `vote_count <= 0`
- [ ] Ajouter `GET /has-voted`

---

## 8. License (`/api/license`)

### État global : 85% — bien structuré, accès à affiner

### Problèmes

#### 🟠 get_all_licenses accessible à tous les utilisateurs authentifiés
```python
@license.route('', methods=['GET'])
@jwt_required()
def get_all_licenses():
    current_user = get_authorized_user()
    
    # Restreindre aux admins sauf si filtre par équipe gérée par l'utilisateur
    if current_user.role not in ['super_admin', 'admin_competition', 'operator']:
        # Un capitaine peut voir les licences de son équipe seulement
        team = Team.query.filter_by(captain_id=current_user.id).first()
        if not team:
            return jsonify({'error': 'Unauthorized'}), 403
        # Forcer le filtre sur son équipe
        # ... reste du code avec team_id forcé
```

#### 🟠 Sync licence_number entre License et TeamMember
Le champ `license_number` existe à la fois dans `TeamMember` et dans `License`. À la création d'une licence, mettre à jour le membre.

```python
# Dans create_license, après db.session.add(license_obj) :
member.license_number = data['license_number']
db.session.commit()

# Dans delete_license :
member = license_obj.member
member.license_number = None
db.session.delete(license_obj)
db.session.commit()
```

#### 🟡 Endpoint manquant — PUT /:id pour renouveler une licence
```python
@license.route('/<int:license_id>', methods=['PUT'])
@jwt_required()
def renew_license(license_id):
    user = get_authorized_user()
    if user.role not in ['super_admin', 'admin_competition']:
        return jsonify({'error': 'Unauthorized'}), 403
    
    license_obj = License.query.get(license_id)
    if not license_obj:
        return jsonify({'error': 'License not found'}), 404
    
    data = request.get_json()
    
    if 'expiry_date' in data:
        new_expiry = datetime.fromisoformat(data['expiry_date'])
        if new_expiry <= datetime.utcnow():
            return jsonify({'error': 'New expiry date must be in the future'}), 400
        license_obj.expiry_date = new_expiry
        license_obj.is_valid = True  # réactivation automatique
    
    if 'document_url' in data:
        license_obj.document_url = data['document_url']
    
    db.session.commit()
    return jsonify({'message': 'License updated', 'license': license_obj.to_dict()}), 200
```

### Checklist License
- [ ] Restreindre `GET /` selon le rôle
- [ ] Synchroniser `member.license_number` à la création et suppression
- [ ] Ajouter `PUT /:id` pour le renouvellement

---

## 9. Problèmes transversaux

### 🔴 Secrets hardcodés dans config.py
```python
# ACTUEL — ne jamais committer ça
SECRET_KEY = 'PO2RxQLMzAMAnIZfRYbVtR8yfPPbfBSJ'
SECRET_JWT_KEY = "0ee06252f7b14d3ea2463pf9d4s65j41"
cloudinary.config(api_secret="aqkZ0jmkoM8Fgle15nZFMmZDpTY")
```

```python
# CORRECTION — utiliser les variables d'environnement + .env local
import os
from dotenv import load_dotenv
load_dotenv()

SECRET_KEY = os.environ['SECRET_KEY']
SECRET_JWT_KEY = os.environ['JWT_SECRET_KEY']

cloudinary.config(
    cloud_name=os.environ['CLOUDINARY_CLOUD_NAME'],
    api_key=os.environ['CLOUDINARY_API_KEY'],
    api_secret=os.environ['CLOUDINARY_API_SECRET']
)
```

Créer un `.env` local (à mettre dans `.gitignore`) et configurer les variables dans Render/Railway/AWS.

### 🔴 app.py contient app.run() dans le fichier principal
```python
# ACTUEL — dangereux en prod, Gunicorn ignore cette ligne mais c'est trompeur
app.run(host='127.0.0.1', debug=True, port=8000)

# CORRECTION
if __name__ == '__main__':
    app.run(host='127.0.0.1', debug=True, port=8000)
```

### 🟠 get_authorized_user() dupliqué dans chaque blueprint
Chaque module redéfinit la même fonction. À centraliser.

```python
# olibo/common/helpers.py
from flask_jwt_extended import get_jwt_identity
from olibo.users.model import User

def get_authorized_user():
    return User.query.get(get_jwt_identity())

def require_roles(*roles):
    """Decorator factory pour la vérification de rôle."""
    from functools import wraps
    from flask import jsonify
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            user = get_authorized_user()
            if not user or user.role not in roles:
                return jsonify({'error': 'Unauthorized'}), 403
            return f(*args, **kwargs)
        return decorated
    return decorator
```

Utilisation :
```python
from olibo.common.helpers import get_authorized_user, require_roles

@team.route('', methods=['POST'])
@jwt_required()
@require_roles('super_admin', 'admin_competition', 'team_captain')
def create_team():
    ...
```

### 🟡 db.create_all() dans create_app — remplacer par les migrations
```python
# ACTUEL — recrée les tables si elles n'existent pas, mais ne gère pas les migrations
with app.app_context():
    db.create_all()

# CORRECTION — supprimer db.create_all() et utiliser flask-migrate
# flask db init  (une seule fois)
# flask db migrate -m "initial"
# flask db upgrade
```

### 🟡 Tous les DELETE devraient retourner 204 No Content
```python
# Convention REST
return '', 204
# au lieu de
return jsonify({'message': 'Deleted successfully'}), 200
```

---

## Récapitulatif des priorités

### Priorité 1 — Sécurité (blocker)
1. `AUTH` — Bloquer les rôles sensibles sur `/register`
2. `AUTH` — Corriger l'import `Token` (logout est cassé)
3. `AUTH` — Rate limiting sur `/login`
4. `TEAM` — Ajouter `@jwt_required()` sur `create_team`
5. `CONFIG` — Sortir tous les secrets vers des variables d'environnement

### Priorité 2 — Fonctionnel (sprint suivant)
6. `RANKING` — Implémenter `recalculate_rankings()` + branchement sur close_match
7. `MATCH_SHEET` — Séparer `in_progress` / `completed`, ajouter `close_match`
8. `MATCH_SHEET` — Valider `event_type` et `minute`
9. `USERS` — Restreindre `GET /` et `GET /:id`
10. `TEAM` — Décommenter les try/except

### Priorité 3 — Amélioration (après livraison V1)
11. `AUTH` — Séparer access/refresh tokens
12. `USERS` — Pagination
13. `COMPETITION` — Compétition active unique
14. `LICENSE` — Sync `license_number` sur `TeamMember`
15. Centraliser `get_authorized_user()` + `require_roles`
16. Passer à `flask-migrate` exclusivement

