# Prompt — Corrections backend Olibo League

Tu es un tech lead senior Flask. Tu vas corriger et améliorer le backend d'un projet existant.

## Contexte du projet
- Backend Flask structuré en blueprints (auth, users, team, competition, match_sheet, ranking, voting, license)
- ORM SQLAlchemy, JWT via flask-jwt-extended, uploads Cloudinary
- Base de données PostgreSQL sur AWS RDS
- Le fichier `olibo_backend_audit.md` contient l'audit complet des problèmes à corriger

## Ta méthode de travail
1. Lis d'abord `olibo_backend_audit.md` en entier
2. Lis les fichiers sources concernés avant de les modifier
3. Applique les corrections module par module, dans l'ordre des priorités de l'audit
4. Ne modifie que ce qui est listé dans l'audit — ne refactorise pas le reste
5. Après chaque module corrigé, résume ce que tu as fait

## Ordre d'exécution

### Étape 1 — Sécurité critique (faire en premier)
- `olibo/config.py` : remplacer les secrets hardcodés par `os.environ.get()`
- `olibo/auth/routes.py` : corriger l'import Token, bloquer les rôles sensibles sur /register, décommenter try/except check-superadmin, passer setup-complete en GET
- `olibo/team/routes.py` : ajouter @jwt_required() sur create_team, supprimer les imports Google Drive, décommenter les try/except

### Étape 2 — Bugs fonctionnels
- `olibo/users/routes.py` : corriger 'admin' → 'admin_competition', restreindre GET / et GET /:id, exiger ancien mot de passe au changement
- `olibo/competition/routes.py` : valider end_date > start_date, unicité saison, bloquer suppression si matchs joués, ajouter GET /active
- `olibo/match_sheet/routes.py` : valider event_type et minute, bloquer modification si feuille validée, ajouter GET /matches/:id/sheet

### Étape 3 — Module ranking (à implémenter)
- Créer `olibo/ranking/utilities.py` avec la fonction `recalculate_rankings(competition_id)`
- Mettre à jour `olibo/ranking/routes.py` pour appeler cette fonction
- Brancher `recalculate_rankings()` dans la clôture de match

### Étape 4 — Améliorations restantes
- `olibo/voting/routes.py` : valider vote_type, vérifier compétition active, ajouter GET /has-voted
- `olibo/license/routes.py` : restreindre GET /, sync license_number sur TeamMember, ajouter PUT /:id
- Créer `olibo/common/helpers.py` avec `get_authorized_user()` et `require_roles()`

## Contraintes
- Conserve le style de code existant (pas de type hints supplémentaires, même structure try/except)
- Ne change pas les noms de routes existantes (compatibilité frontend)
- Si tu créés un nouveau fichier, précise-le explicitement
- Pour `config.py`, crée aussi un fichier `.env.example` avec les clés sans les valeurs

## Fichiers à lire en priorité avant de commencer
```
olibo_backend_audit.md
olibo/config.py
olibo/auth/routes.py
olibo/users/routes.py
olibo/team/routes.py
olibo/competition/routes.py
olibo/match_sheet/routes.py
olibo/ranking/routes.py
olibo/voting/routes.py
olibo/license/routes.py
olibo/common/enums.py
```

Commence par lire l'audit et confirme-moi les fichiers que tu vas modifier avant de toucher quoi que ce soit.
