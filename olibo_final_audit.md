# Audit Final — Olibo League
> Frontend + Backend + Cross-check · Avril 2026
> Document de référence unique pour atteindre 100%

---

## Légende
- 🔴 Cassé — erreur garantie en production
- 🟠 Bug silencieux — fonctionne en apparence mais données fausses ou flux incomplet
- 🟡 Dette technique — fragile, maintenabilité réduite
- 🗑️ Fichier mort — à supprimer
- ✅ Correct

---

# PARTIE 1 — BACKEND

---

## Module Auth `/api/auth`

### 🔴 Import mort — logout plante en production
```python
# ACTUEL
from contextvars import Token
Token.query.filter_by(user_id=user_id).delete()  # AttributeError

# CORRECTION
from olibo.auth.model import Token
```

### 🔴 Register accepte n'importe quel rôle — faille de sécurité
```python
# ACTUEL — n'importe qui peut se créer super_admin
user = User(role=data['role'])

# CORRECTION
SELF_REGISTER_ROLES = ['team_captain', 'coach', 'spectator']
if data['role'] not in SELF_REGISTER_ROLES:
    return jsonify({'error': 'Invalid role for self-registration'}), 403
```

### 🔴 Pas de rate limiting sur /login — brute force possible
```python
# Installer flask-limiter et ajouter :
@auth.route('/login', methods=['POST'])
@limiter.limit("5 per minute")
def login():
```

### 🟠 check-superadmin ne retourne pas admin_competition_exists
Le `SetupService` Angular attend ce champ. Sans lui, `setupComplete` est toujours `false`.
```python
# CORRECTION
superadmin = User.query.filter_by(role='super_admin').first()
admin = User.query.filter_by(role='admin_competition').first()
return jsonify({
    'exists': superadmin is not None,
    'admin_competition_exists': admin is not None,
}), 200
```

### 🟠 check-superadmin — try/except commenté
```python
# Décommenter le bloc try/except dans check_superadmin()
```

### 🟠 setup-complete utilise POST — devrait être GET
```python
@auth.route('/setup-complete', methods=['GET'])
def setup_complete():
```

### 🟠 refresh_token utilise l'access token au lieu du refresh token
```python
# ACTUEL — @jwt_required() valide l'access token pour se rafraîchir
# CORRECTION — séparer les durées + utiliser refresh token dédié
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=2)
app.config['JWT_REFRESH_TOKEN_EXPIRES'] = timedelta(days=30)

# login() : générer les deux tokens
refresh_token = create_refresh_token(identity=str(user.id))
return jsonify({'access_token': ..., 'refresh_token': ..., 'user': ...})

# refresh route :
@auth.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh_token():
    user_id = get_jwt_identity()
    new_token = create_access_token(identity=user_id, ...)
    return jsonify({'access_token': new_token}), 200
```

### 🟡 Rôle non validé contre enum à l'inscription
```python
from olibo.common.enums import UserRole
valid_roles = [r.value for r in UserRole]
if data['role'] not in valid_roles:
    return jsonify({'error': f'Invalid role'}), 400
```

### 🟡 Endpoint manquant — GET /auth/me
```python
@auth.route('/me', methods=['GET'])
@jwt_required()
def get_me():
    user = User.query.get(get_jwt_identity())
    if not user:
        return jsonify({'error': 'User not found'}), 404
    return jsonify({'user': user.to_dict()}), 200
```

---

## Module Users `/api/users`

### 🔴 Rôle 'admin' inexistant dans les contrôles
```python
# ACTUEL
if current_user.role not in ['super_admin', 'admin']:
# CORRECTION
if current_user.role not in ['super_admin', 'admin_competition']:
```

### 🟠 GET / accessible à tous les utilisateurs authentifiés
```python
if current_user.role not in ['super_admin', 'admin_competition', 'operator']:
    return jsonify({'error': 'Unauthorized'}), 403
```

### 🟠 GET /:id accessible à tous
```python
if current_user.id != user_id and current_user.role not in ['super_admin', 'admin_competition']:
    return jsonify({'error': 'Unauthorized'}), 403
```

### 🟠 Changement de mot de passe sans vérification de l'ancien
```python
if 'password' in data:
    if current_user.role != 'super_admin':
        old_pw = data.get('old_password')
        if not old_pw or not check_password_hash(user.password_hash, old_pw):
            return jsonify({'error': 'Current password required'}), 400
    user.password_hash = generate_password_hash(data['password'])
```

### 🟡 Pagination manquante sur GET /
```python
page = request.args.get('page', 1, type=int)
per_page = min(request.args.get('per_page', 20, type=int), 100)
pagination = query.paginate(page=page, per_page=per_page, error_out=False)
return jsonify({'users': [...], 'total': pagination.total, 'pages': pagination.pages})
```

---

## Module Teams `/api/team`

### 🔴 create_team sans @jwt_required()
```python
@team.route('', methods=['POST'])
@jwt_required()
def create_team():
```

### 🔴 Imports Google Drive morts — peuvent planter si packages absents
```python
# Supprimer ces 4 lignes dans team/routes.py :
from google.oauth2 import service_account
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
```

### 🟠 create_team et get_all_teams — try/except commentés
Décommenter les blocs try/except dans les deux routes.

### 🟠 remove_member ne supprime pas la photo Cloudinary
```python
if member.photo_public_id:
    delete_from_cloudinary(member.photo_public_id)
db.session.delete(member)
```

### 🟠 validate_registration ne vérifie pas le statut courant
```python
if registration.status == RegistrationStatus.VALIDATED.value:
    return jsonify({'error': 'Already validated'}), 409
if registration.status == RegistrationStatus.REJECTED.value:
    return jsonify({'error': 'Cannot validate a rejected registration'}), 409
```

### 🟠 Soumission d'inscription sans contrôle nombre minimum de joueurs
```python
MIN_PLAYERS = 7
player_count = TeamMember.query.filter_by(team_id=team_id, role='player').count()
if player_count < MIN_PLAYERS:
    return jsonify({'error': f'Minimum {MIN_PLAYERS} players required'}), 400
```

### 🟡 is_team_manager trop restrictif
```python
def is_team_manager(user, t):
    admin_roles = {'super_admin', 'admin_competition', 'operator'}
    return t.captain_id == user.id or user.role in admin_roles
```

### 🟡 Endpoint manquant — GET /:id/registration
```python
@team.route('/<int:team_id>/registration', methods=['GET'])
@jwt_required()
def get_team_registration(team_id):
    ...
```

---

## Module Competition `/api/competition`

### 🟠 Pas de validation end_date > start_date
```python
if end <= start:
    return jsonify({'error': 'end_date must be after start_date'}), 400
```

### 🟠 Pas de contrôle unicité de la saison
```python
if Competition.query.filter_by(season=data['season']).first():
    return jsonify({'error': 'Season already exists'}), 409
```

### 🟠 delete_competition supprime tout sans vérification
```python
played = Match.query.filter_by(competition_id=comp_id, status='completed').count()
if played > 0:
    return jsonify({'error': f'Cannot delete: {played} matches played'}), 409
```

### 🟡 Endpoint manquant — GET /competition/active
```python
@competition.route('/active', methods=['GET'])
def get_active_competition():
    comp = Competition.query.filter_by(is_active=True).first()
    return jsonify({'competition': comp.to_dict() if comp else None}), 200
```

### 🟡 Une seule compétition active à la fois non garantie
```python
# Dans create et update, si is_active=True :
Competition.query.filter(Competition.id != comp_id).update({'is_active': False})
```

---

## Module Match Sheet `/api/match_sheet`

### 🔴 Recalcul classement non déclenché après match
Voir section Ranking.

### 🟠 fill_match_sheet passe directement en COMPLETED — pas d'état in_progress
```python
# Dans fill_match_sheet : status → IN_PROGRESS
match.status = MatchStatus.IN_PROGRESS.value

# Nouvelle route close_match :
@match_sheet.route('/matches/<int:match_id>/close', methods=['POST'])
@jwt_required()
def close_match(match_id):
    match.status = MatchStatus.COMPLETED.value
    db.session.commit()
    from olibo.ranking.utilities import recalculate_rankings
    recalculate_rankings(match.competition_id)
    return jsonify({'message': 'Match closed'}), 200
```

### 🟠 event_type non validé
```python
VALID_EVENTS = {'goal', 'assist', 'yellow_card', 'red_card', 'substitution'}
if data['event_type'] not in VALID_EVENTS:
    return jsonify({'error': f'Invalid event_type'}), 400
```

### 🟠 Minute non validée
```python
if not isinstance(minute, int) or not (0 <= minute <= 130):
    return jsonify({'error': 'Minute must be 0-130'}), 400
```

### 🟠 Modification feuille déjà validée non bloquée
```python
if sheet and sheet.is_validated:
    return jsonify({'error': 'Sheet already validated'}), 409
```

### 🟡 Endpoints manquants
```
GET  /matches/:id/sheet
DELETE /matches/:id/events/:event_id
PUT  /matches/:id
```

---

## Module Ranking `/api/ranking`

### 🔴 update_rankings — corps vide, la fonction n'existe pas
Créer `olibo/ranking/utilities.py` :

```python
def recalculate_rankings(competition_id: int) -> None:
    completed_matches = Match.query.filter_by(
        competition_id=competition_id,
        status=MatchStatus.COMPLETED.value
    ).all()

    stats = {}

    def init_team(tid):
        if tid not in stats:
            stats[tid] = {'matches_played':0,'wins':0,'draws':0,'losses':0,
                          'goals_for':0,'goals_against':0}

    for match in completed_matches:
        h, a = match.home_team_id, match.away_team_id
        hg, ag = match.home_team_goals, match.away_team_goals
        init_team(h); init_team(a)
        stats[h]['matches_played'] += 1; stats[a]['matches_played'] += 1
        stats[h]['goals_for'] += hg;    stats[h]['goals_against'] += ag
        stats[a]['goals_for'] += ag;    stats[a]['goals_against'] += hg
        if hg > ag:
            stats[h]['wins'] += 1;  stats[a]['losses'] += 1
        elif hg == ag:
            stats[h]['draws'] += 1; stats[a]['draws'] += 1
        else:
            stats[a]['wins'] += 1;  stats[h]['losses'] += 1

    for s in stats.values():
        s['points'] = s['wins'] * 3 + s['draws']
        s['goal_difference'] = s['goals_for'] - s['goals_against']

    sorted_teams = sorted(stats.items(),
        key=lambda x: (x[1]['points'], x[1]['goal_difference'], x[1]['goals_for']),
        reverse=True)

    for position, (team_id, s) in enumerate(sorted_teams, start=1):
        ranking = Ranking.query.filter_by(
            competition_id=competition_id, team_id=team_id).first()
        if ranking:
            for k, v in s.items():
                setattr(ranking, k, v)
            ranking.position = position
        else:
            db.session.add(Ranking(competition_id=competition_id,
                                   team_id=team_id, position=position, **s))
    db.session.commit()
```

---

## Module Voting `/api/voting`

### 🟠 vote_type non validé
```python
valid = [v.value for v in VoteType]
if data['vote_type'] not in valid:
    return jsonify({'error': 'Invalid vote_type'}), 400
```

### 🟠 Pas de vérification compétition active
```python
if not competition.is_active:
    return jsonify({'error': 'Voting only allowed for active competitions'}), 400
```

### 🟠 matchday obligatoire pour player_of_day
```python
if data['vote_type'] == 'player_of_day' and not data.get('matchday'):
    return jsonify({'error': 'matchday required for player_of_day'}), 400
```

### 🟡 Endpoint manquant — GET /voting/has-voted
```python
@voting.route('/has-voted', methods=['GET'])
@jwt_required()
def has_voted():
    existing = Vote.query.filter_by(
        voter_id=get_jwt_identity(),
        vote_type=request.args.get('vote_type'),
        competition_id=request.args.get('competition_id', type=int),
        matchday=request.args.get('matchday', type=int)
    ).first()
    return jsonify({'has_voted': existing is not None}), 200
```

---

## Module License `/api/license`

### 🟠 GET / accessible à tous
```python
if current_user.role not in ['super_admin', 'admin_competition', 'operator']:
    team = Team.query.filter_by(captain_id=current_user.id).first()
    if not team:
        return jsonify({'error': 'Unauthorized'}), 403
```

### 🟠 license_number non synchronisé sur TeamMember
```python
# Dans create_license :
member.license_number = data['license_number']
# Dans delete_license :
member.license_number = None
```

### 🟡 Endpoint manquant — PUT /:id (renouvellement)
```python
@license.route('/<int:license_id>', methods=['PUT'])
@jwt_required()
def renew_license(license_id):
    ...
```

---

## Problèmes transversaux Backend

### 🔴 Secrets hardcodés dans config.py
```python
# SUPPRIMER toutes les valeurs en dur, utiliser :
import os
from dotenv import load_dotenv
load_dotenv()

SECRET_KEY = os.environ['SECRET_KEY']
JWT_SECRET_KEY = os.environ['JWT_SECRET_KEY']
cloudinary.config(
    cloud_name=os.environ['CLOUDINARY_CLOUD_NAME'],
    api_key=os.environ['CLOUDINARY_API_KEY'],
    api_secret=os.environ['CLOUDINARY_API_SECRET']
)
# Créer .env.example avec les clés sans valeurs + ajouter .env au .gitignore
```

### 🔴 app.py — app.run() hors guard
```python
# CORRECTION
if __name__ == '__main__':
    app.run(host='127.0.0.1', debug=True, port=8000)
```

### 🟠 get_authorized_user() dupliqué dans chaque blueprint
Créer `olibo/common/helpers.py` :
```python
from flask_jwt_extended import get_jwt_identity
from olibo.users.model import User

def get_authorized_user():
    return User.query.get(get_jwt_identity())

def require_roles(*roles):
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

### 🟡 db.create_all() — migrer vers flask-migrate
```bash
pip install flask-migrate
flask db init
flask db migrate -m "initial"
flask db upgrade
# Supprimer db.create_all() de create_app()
```

---

# PARTIE 2 — FRONTEND

---

## Fichiers à supprimer intégralement 🗑️

```
src/app/pages/service/product.service.ts    ← données e-commerce fictives
src/app/pages/service/customer.service.ts   ← faux clients + appel primefaces.org
src/app/pages/service/icon.service.ts       ← jamais utilisé
src/app/pages/service/country.service.ts    ← jamais utilisé
src/app/pages/service/node.service.ts       ← jamais utilisé
src/app/pages/service/photo.service.ts      ← jamais utilisé
src/app/pages/empty/empty.ts               ← composant placeholder
src/app/pages/pages.routes.ts              ← ne contient que la route empty
src/assets/demo/                            ← styles de démo PrimeNG
```

Dashboard — widgets à remplacer :
```
src/app/pages/dashboard/components/recentsaleswidget.ts    ← e-commerce
src/app/pages/dashboard/components/revenuestreamwidget.ts  ← e-commerce
src/app/pages/dashboard/components/bestsellingwidget.ts    ← e-commerce
src/app/pages/dashboard/components/notificationswidget.ts  ← e-commerce
src/app/pages/dashboard/components/statswidget.ts          ← e-commerce
```

---

## Bugs critiques Frontend 🔴

### 🔴 localStorage key incorrecte dans 4 services → 401 sur tous les appels

`TeamService`, `UserService`, `LicenseService`, `EnumService` lisent tous `localStorage.getItem('token')`.
`AuthService` stocke sous `'access_token'`. Résultat : `Authorization: Bearer null` sur **tous** les appels protégés.

**Solution** : supprimer les méthodes `httpOption()` dans les 4 services. L'`authInterceptor` injecte déjà le bon token automatiquement.

```typescript
// AVANT (dans chaque service)
createTeam(formData: FormData) {
  return this.http.post(`${this.apiUrl}`, formData, this.httpOption());
}

// APRÈS
createTeam(formData: FormData) {
  return this.http.post(`${this.apiUrl}`, formData);
}
```

### 🔴 Routes admin sans AuthGuard
```typescript
// CORRECTION — ajouter canActivate sur le bloc parent
{
  path: 'mon-espace',
  component: AppLayout,
  canActivate: [AuthGuard],  // ← ajouter
  children: [...]
}
```

### 🔴 authInterceptor redirige vers '/login' (route inexistante)
```typescript
// AVANT
router.navigate(['/login']);
// APRÈS
router.navigate(['/auth/login']);
```

### 🔴 captain_id et coach_id non envoyés à la création d'équipe
```typescript
// team.form.component.ts — onSubmit(), ajouter :
if (rawValue.captain_id) formData.append('captain_id', String(rawValue.captain_id));
if (rawValue.coach_id)   formData.append('coach_id',   String(rawValue.coach_id));
```

### 🔴 birth_date format incorrect — Date JS au lieu de YYYY-MM-DD
```typescript
// Ajouter dans team.form.component.ts ET team.list.component.ts :
private formatDateForApi(date: any): string {
  if (!date) return '';
  if (date instanceof Date) return date.toISOString().split('T')[0];
  if (typeof date === 'string' && date.includes('T')) return date.split('T')[0];
  return String(date);
}

// Remplacer dans FormData :
formData.append(`members[${index}][birth_date]`, this.formatDateForApi(member.birth_date));
```

### 🔴 PublicGuard redirige vers des routes inexistantes
```typescript
// AVANT — routes fantômes
this.router.navigate(['/admin/dashboard']);
this.router.navigate(['/team/dashboard']);

// APRÈS — dashboard unifié
this.router.navigate(['/mon-espace/mon-tableau-bord']);
```

---

## Bugs silencieux Frontend 🟠

### 🟠 Dashboard figé avec show = false
```typescript
// AVANT
export class Dashboard {
  show = false; // widgets jamais affichés
}
// APRÈS — supprimer le flag, afficher les vrais widgets Olibo
```

### 🟠 p-select rôle envoie l'objet {label, value} au lieu de la string
```html
<!-- users.form.component.html -->
<p-select
  formControlName="role"
  [options]="roles"
  optionLabel="label"
  optionValue="value"   ← ajouter
/>
```

### 🟠 ArticleEditorComponent hors du layout protégé
```typescript
// DÉPLACER dans les children de 'mon-espace' :
{ path: 'articles/new', component: ArticleEditorComponent },
{ path: 'articles/edit/:id', component: ArticleEditorComponent },
```

### 🟠 SetupGuard commentaire inversé (logique correcte, commentaire trompeur)
```typescript
// Corriger le commentaire pour éviter les erreurs futures
const superadminExists = response.exists;
if (!superadminExists) {
  this.router.navigate(['/auth/register_superadmin']); // redirige si ABSENT
  return false;
}
return true; // continue si super admin EXISTE
```

---

## Dette technique Frontend 🟡

### 🟡 Routes avec caractères accentués
```typescript
// AVANT
{ path: 'équipes', component: Teams },
{ path: 'règlement', component: Regulations },
// APRÈS
{ path: 'equipes', component: Teams },
{ path: 'reglement', component: Regulations },
```

### 🟡 Services manquants — modules backend sans service Angular

| Service à créer | Endpoints à câbler |
|---|---|
| `CompetitionService` | GET /active, CRUD compétition |
| `MatchService` | CRUD match, events, close_match |
| `RankingService` | GET classement par compétition |
| `VotingService` | cast vote, has-voted, résultats |

---

## Dashboard — Refonte complète

Remplacer les 5 widgets e-commerce par 5 widgets Olibo.

### Nouveau `dashboard.ts`
```typescript
@Component({
  selector: 'app-dashboard',
  imports: [KpisWidget, MatchsRecentWidget, ClassementWidget,
            StatsMatchdayWidget, DerniersEvenementsWidget],
  template: `
    <div class="grid grid-cols-12 gap-8">
      <app-kpis-widget class="contents" />
      <div class="col-span-12 xl:col-span-7">
        <app-matchs-recent-widget />
      </div>
      <div class="col-span-12 xl:col-span-5">
        <app-classement-widget />
      </div>
      <div class="col-span-12 xl:col-span-6">
        <app-stats-matchday-widget />
      </div>
      <div class="col-span-12 xl:col-span-6">
        <app-derniers-evenements-widget />
      </div>
    </div>
  `
})
export class Dashboard implements OnInit {
  constructor(private competitionService: CompetitionService) {}
  ngOnInit() { /* charger la compétition active */ }
}
```

### Spec des 5 nouveaux widgets

**KpisWidget** — Remplace StatsWidget
```
Source : GET /api/team/registrations?status=validated + GET /api/match_sheet/matches?status=completed + GET /api/license + GET /api/voting/has-voted
Affiche : Équipes inscrites | Matchs joués | Joueurs licenciés | Votes actifs
```

**MatchsRecentWidget** — Remplace RecentSalesWidget
```
Source : GET /api/match_sheet/matches?status=completed&limit=5
Colonnes : Équipe Dom | Score | Équipe Ext | Journée | Date
```

**ClassementWidget** — Remplace BestSellingWidget
```
Source : GET /api/ranking/competition/:id
Affiche : Top 5 — Position | Logo | Équipe | Pts | J | G | N | P | GD
```

**StatsMatchdayWidget** — Remplace RevenueStreamWidget
```
Source : GET /api/match_sheet/matches?competition_id=:id
Chart bar : buts par journée (couleurs primaires Olibo)
```

**DerniersEvenementsWidget** — Remplace NotificationsWidget
```
Source : derniers événements de match (buts, cartons)
Format : "Ahmed K. a marqué pour Étoile FC (23')"
```

---

# PARTIE 3 — CHECKLIST D'EXÉCUTION

## Sprint 1 — Sécurité & Bugs bloquants (priorité absolue)

### Backend
- [ ] `config.py` — sortir tous les secrets vers `.env`
- [ ] `auth/routes.py` — corriger import `Token`
- [ ] `auth/routes.py` — bloquer rôles sensibles sur `/register`
- [ ] `auth/routes.py` — décommenter try/except `check-superadmin`
- [ ] `auth/routes.py` — ajouter `admin_competition_exists` à la réponse
- [ ] `auth/routes.py` — passer `setup-complete` en GET
- [ ] `team/routes.py` — ajouter `@jwt_required()` sur `create_team`
- [ ] `team/routes.py` — supprimer imports Google Drive
- [ ] `team/routes.py` — décommenter try/except
- [ ] `app.py` — mettre `app.run()` dans `if __name__ == '__main__':`
- [ ] `users/routes.py` — corriger `'admin'` → `'admin_competition'`

### Frontend
- [ ] Supprimer `httpOption()` dans `TeamService`, `UserService`, `LicenseService`, `EnumService`
- [ ] `app.routes.ts` — ajouter `canActivate: [AuthGuard]` sur `mon-espace`
- [ ] `auth.interceptor.ts` — corriger redirection `'/login'` → `'/auth/login'`
- [ ] `public.guard.ts` — corriger redirections fantômes
- [ ] `team.form.component.ts` — ajouter `captain_id` et `coach_id` au FormData
- [ ] `team.form.component.ts` — formater `birth_date` en YYYY-MM-DD
- [ ] `team.list.component.ts` — formater `birth_date` en YYYY-MM-DD
- [ ] `users.form.component.html` — ajouter `optionValue="value"` sur p-select rôle

## Sprint 2 — Complétude fonctionnelle

### Backend
- [ ] Créer `olibo/ranking/utilities.py` avec `recalculate_rankings()`
- [ ] `ranking/routes.py` — brancher `recalculate_rankings` dans POST /
- [ ] `match_sheet/routes.py` — séparer `in_progress` / `completed`, créer `close_match`
- [ ] `match_sheet/routes.py` — brancher `recalculate_rankings` sur `close_match`
- [ ] `match_sheet/routes.py` — valider `event_type` et `minute`
- [ ] `match_sheet/routes.py` — bloquer modif feuille validée
- [ ] `match_sheet/routes.py` — ajouter `GET /matches/:id/sheet`
- [ ] `competition/routes.py` — valider `end_date > start_date`
- [ ] `competition/routes.py` — unicité saison
- [ ] `competition/routes.py` — bloquer suppression si matchs joués
- [ ] `competition/routes.py` — ajouter `GET /active`
- [ ] `voting/routes.py` — valider `vote_type`, compétition active, matchday obligatoire
- [ ] `voting/routes.py` — ajouter `GET /has-voted`
- [ ] `license/routes.py` — restreindre GET /, sync `license_number` sur membre
- [ ] `users/routes.py` — restreindre GET / et GET /:id, exiger ancien mot de passe
- [ ] `auth/routes.py` — ajouter `GET /me`

### Frontend
- [ ] Supprimer les 9 fichiers/dossiers morts listés ci-dessus
- [ ] `app.routes.ts` — déplacer routes `admin/articles/*` dans `mon-espace`
- [ ] `app.routes.ts` — corriger routes accentuées (`équipes` → `equipes`)
- [ ] `dashboard.ts` — supprimer flag `show = false`
- [ ] `article-editor` — déplacer dans routes protégées
- [ ] Créer `CompetitionService`, `MatchService`, `RankingService`, `VotingService`

## Sprint 3 — Dashboard Olibo + Améliorations

### Frontend
- [ ] Remplacer les 5 widgets e-commerce par 5 widgets Olibo
- [ ] Brancher les vrais appels API dans chaque widget
- [ ] `app.menu.ts` — restructurer navigation par domaine + conditionner par rôle
- [ ] `app.topbar.ts` — afficher nom + rôle de l'utilisateur connecté

### Backend
- [ ] Créer `olibo/common/helpers.py` avec `get_authorized_user()` + `require_roles()`
- [ ] Remplacer les `get_authorized_user()` dupliqués par l'import centralisé
- [ ] `users/routes.py` — ajouter pagination
- [ ] `competition/routes.py` — garantir une seule compétition active
- [ ] Migrer de `db.create_all()` vers `flask-migrate`
- [ ] Ajouter `flask-limiter` sur `/login`
- [ ] Implémenter séparation access/refresh tokens

---

# Score final projeté

| Module | Actuel | Sprint 1 | Sprint 2 | Sprint 3 |
|---|---|---|---|---|
| Auth | 60% | 85% | 95% | 100% |
| Users | 50% | 75% | 95% | 100% |
| Teams | 40% | 80% | 95% | 100% |
| Competition | 85% | 90% | 100% | 100% |
| Match Sheet | 70% | 70% | 95% | 100% |
| Ranking | 25% | 25% | 100% | 100% |
| Voting | 80% | 80% | 100% | 100% |
| License | 50% | 75% | 100% | 100% |
| Dashboard | 10% | 15% | 20% | 100% |
| Routes/Guards | 55% | 95% | 100% | 100% |
| Services Angular | 60% | 95% | 100% | 100% |

