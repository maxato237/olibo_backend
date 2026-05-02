# Prompt Claude Code — Implémentation Olibo League
> À placer à la racine du projet (dossier contenant `backend/` et `src/`)
> Lancer : `claude` depuis ce dossier

---

Tu es un tech lead senior fullstack. Tu vas implémenter les corrections et améliorations du projet Olibo League à partir du fichier `olibo_final_audit.md`.

## Structure du projet
```
/
├── backend/          ← Flask API
│   ├── app.py
│   ├── olibo/
│   │   ├── auth/routes.py
│   │   ├── users/routes.py
│   │   ├── team/routes.py
│   │   ├── competition/routes.py
│   │   ├── match_sheet/routes.py
│   │   ├── ranking/routes.py + utilities.py (à créer)
│   │   ├── voting/routes.py
│   │   ├── license/routes.py
│   │   └── common/enums.py + helpers.py (à créer)
│   └── config.py
└── src/              ← Angular frontend
    └── app/
        ├── services/
        │   ├── authService/auth.service.ts
        │   ├── userService/user.service.ts
        │   ├── teamService/team.service.ts
        │   ├── licenceService/license.service.ts
        │   └── enumService/enum.service.ts
        ├── guards/auth.guard.ts
        ├── interceptors/auth.interceptor.ts
        └── pages/
            ├── dashboard/
            ├── users/users.form/
            └── teams/manage/team.form/
```

## Méthode de travail

1. **Lis d'abord `olibo_final_audit.md` en entier**
2. Lis les fichiers sources concernés AVANT de les modifier
3. Travaille sprint par sprint dans cet ordre exact
4. Après chaque fichier modifié, résume ce que tu as changé
5. Ne modifie jamais ce qui n'est pas dans l'audit
6. Si tu créés un fichier, annonce-le explicitement
7. Ne refactorise pas au-delà du scope demandé

---

## SPRINT 1 — Sécurité & Bugs bloquants

### Étape 1.1 — config.py (backend)
- Lire `backend/olibo/config.py`
- Remplacer **toutes** les valeurs hardcodées par `os.environ.get()`
- Ajouter `load_dotenv()` en tête de fichier
- Créer `.env.example` avec les clés (sans valeurs) à la racine de `backend/`
- Ajouter `.env` au `.gitignore` si pas déjà présent

### Étape 1.2 — auth/routes.py (backend)
Lire le fichier entier, puis appliquer dans l'ordre :
- Corriger l'import `Token` (`from contextvars import Token` → `from olibo.auth.model import Token`)
- Bloquer les rôles sensibles sur `/register` (seuls `team_captain`, `coach`, `spectator` autorisés)
- Décommenter le try/except dans `check_superadmin`
- Ajouter `admin_competition_exists` à la réponse de `check-superadmin`
- Passer `setup-complete` de POST à GET
- Valider le rôle contre `UserRole` enum à l'inscription
- Ajouter `GET /me` endpoint

### Étape 1.3 — app.py (backend)
- Entourer `app.run()` dans `if __name__ == '__main__':`

### Étape 1.4 — users/routes.py (backend)
- Corriger `'admin'` → `'admin_competition'` dans tous les contrôles de rôle

### Étape 1.5 — team/routes.py (backend)
- Ajouter `@jwt_required()` sur `create_team`
- Supprimer les 4 imports Google Drive (google.oauth2, google_auth_oauthlib, googleapiclient x2)
- Décommenter les blocs try/except dans `create_team` et `get_all_teams`

### Étape 1.6 — Services Angular (frontend)
Pour chacun de ces 4 fichiers :
- `src/app/services/teamService/team.service.ts`
- `src/app/services/userService/user.service.ts`
- `src/app/services/licenceService/license.service.ts`
- `src/app/services/enumService/enum.service.ts`

Appliquer :
1. Supprimer la méthode `httpOption()` entière
2. Supprimer le `@Inject(PLATFORM_ID)` et l'import `isPlatformBrowser` s'ils ne servent qu'à `httpOption()`
3. Retirer le deuxième paramètre `this.httpOption()` de tous les appels `http.get/post/put/delete`

### Étape 1.7 — app.routes.ts (frontend)
- Ajouter `canActivate: [AuthGuard]` sur le path `mon-espace`
- Importer `AuthGuard` si pas déjà importé

### Étape 1.8 — auth.interceptor.ts (frontend)
- Corriger `router.navigate(['/login'])` → `router.navigate(['/auth/login'])`

### Étape 1.9 — auth.guard.ts (frontend)
Dans `PublicGuard.canActivate()`, remplacer les 4 redirections vers des routes fantômes :
```typescript
this.router.navigate(['/mon-espace/mon-tableau-bord']);
```
(même route pour tous les rôles pour l'instant)

### Étape 1.10 — team.form.component.ts (frontend)
- Lire `src/app/pages/teams/manage/team.form/team.form.component.ts`
- Dans `onSubmit()`, après l'append de `description`, ajouter :
  ```typescript
  if (rawValue.captain_id) formData.append('captain_id', String(rawValue.captain_id));
  if (rawValue.coach_id)   formData.append('coach_id',   String(rawValue.coach_id));
  ```
- Ajouter la méthode privée `formatDateForApi(date: any): string`
- L'utiliser pour `birth_date` dans l'itération des membres

### Étape 1.11 — team.list.component.ts (frontend)
- Lire `src/app/pages/teams/manage/team.list/team.list.component.ts`
- Ajouter `formatDateForApi(date: any): string` (même implémentation)
- Utiliser cette méthode pour tous les `fd.append('birth_date', ...)` dans le fichier

### Étape 1.12 — users.form.component.html (frontend)
- Lire `src/app/pages/users/users.form/users.form.component.html`
- Trouver le `<p-select formControlName="role">` et ajouter `optionValue="value"`

---

## SPRINT 2 — Complétude fonctionnelle

### Étape 2.1 — Créer olibo/common/helpers.py (backend)
Créer ce fichier avec :
- `get_authorized_user()` — récupère l'utilisateur courant depuis JWT
- `require_roles(*roles)` — décorateur de vérification de rôle

### Étape 2.2 — Créer olibo/ranking/utilities.py (backend)
Créer avec la fonction `recalculate_rankings(competition_id: int)` complète
(implémentation complète dans `olibo_final_audit.md` section Module Ranking)

### Étape 2.3 — ranking/routes.py (backend)
- Importer et appeler `recalculate_rankings` dans le POST `/`
- Retourner les rankings recalculés dans la réponse

### Étape 2.4 — match_sheet/routes.py (backend)
- Dans `fill_match_sheet` : changer status en `IN_PROGRESS` au lieu de `COMPLETED`
- Créer route `POST /matches/:id/close` qui : passe en COMPLETED + appelle `recalculate_rankings`
- Valider `event_type` contre `{'goal', 'assist', 'yellow_card', 'red_card', 'substitution'}`
- Valider `minute` entre 0 et 130
- Bloquer modification si `sheet.is_validated == True`
- Ajouter `GET /matches/:id/sheet`

### Étape 2.5 — competition/routes.py (backend)
- Valider `end_date > start_date` dans create et update
- Vérifier unicité de la saison à la création
- Bloquer `delete` si des matchs ont été joués (status=completed)
- Ajouter `GET /active` (public, sans JWT)
- Garantir une seule compétition active à la fois dans create/update

### Étape 2.6 — voting/routes.py (backend)
- Valider `vote_type` contre `VoteType` enum
- Vérifier que la compétition est active
- Rendre `matchday` obligatoire pour `player_of_day`
- Ajouter `GET /has-voted`

### Étape 2.7 — license/routes.py (backend)
- Restreindre `GET /` selon le rôle (admins voient tout, capitaine voit son équipe)
- Synchroniser `member.license_number` à la création et suppression de licence

### Étape 2.8 — users/routes.py (backend)
- Restreindre `GET /` aux admins uniquement
- Restreindre `GET /:id` à l'utilisateur lui-même ou aux admins
- Exiger l'ancien mot de passe pour le changement (sauf super_admin)
- Ajouter pagination sur `GET /`

### Étape 2.9 — Supprimer fichiers morts (frontend)
Supprimer dans cet ordre (vérifier avant qu'aucun import actif n'existe) :
1. `src/app/pages/service/` (dossier entier)
2. `src/app/pages/empty/empty.ts`
3. `src/app/pages/pages.routes.ts`
4. `src/assets/demo/` (dossier entier)
5. Les 5 widgets dashboard : `recentsaleswidget.ts`, `revenuestreamwidget.ts`, `bestsellingwidget.ts`, `notificationswidget.ts`, `statswidget.ts`

Pour chaque suppression, vérifier et corriger les imports cassés dans `dashboard.ts`.

### Étape 2.10 — Créer les services manquants (frontend)
Créer dans `src/app/services/` :

**competitionService/competition.service.ts**
```typescript
// Méthodes : getActive(), getAll(), getById(id), create(data), update(id, data), delete(id)
// URL : environment.api + '/competition'
```

**matchService/match.service.ts**
```typescript
// Méthodes : getAll(filters?), getById(id), getSheet(matchId), create(data),
//            addEvent(matchId, event), closeMatch(matchId)
// URL : environment.api + '/match_sheet'
```

**rankingService/ranking.service.ts**
```typescript
// Méthodes : getByCompetition(competitionId), recalculate(competitionId)
// URL : environment.api + '/ranking'
```

**votingService/voting.service.ts**
```typescript
// Méthodes : castVote(data), hasVoted(voteType, compId, matchday?), getResults(compId)
// URL : environment.api + '/voting'
```

### Étape 2.11 — Corrections mineures app.routes.ts (frontend)
- Déplacer routes `admin/articles/new` et `admin/articles/edit/:id` dans les children de `mon-espace`
- Corriger `équipes` → `equipes` et `règlement` → `reglement`
- Supprimer le `loadChildren` vers `pages.routes.ts` (supprimé à l'étape 2.9)

### Étape 2.12 — dashboard.ts (frontend)
- Supprimer le flag `show = false` et le `@if (show)` qui entoure les widgets
- Supprimer l'image SVG de maintenance
- Supprimer les imports des 5 widgets e-commerce
- Laisser un template minimal avec un message "Dashboard en cours de développement" jusqu'au Sprint 3

---

## SPRINT 3 — Dashboard Olibo (exécuter séparément)

### Étape 3.1 — Créer les 5 widgets Olibo

Pour chaque widget, créer un fichier dans `src/app/pages/dashboard/components/` :

**kpis.widget.ts**
- 4 cards : Équipes inscrites, Matchs joués, Joueurs licenciés, Votes actifs
- Sources : CompetitionService + MatchService + LicenseService
- Style : conserver les couleurs et icônes PrimeNG, changer les libellés et données

**matchs-recent.widget.ts**
- `p-table` avec les 5 derniers matchs joués
- Colonnes : Équipe domicile | Score | Équipe extérieure | Journée | Date
- Source : `MatchService.getAll({status: 'completed', limit: 5})`

**classement.widget.ts**
- Tableau top 5 du classement compétition active
- Colonnes : Pos | Équipe | Pts | J | G | N | P | GD
- Source : `RankingService.getByCompetition(competitionId)`

**stats-matchday.widget.ts**
- Bar chart `p-chart` buts par journée (home vs away)
- Source : `MatchService.getAll({competition_id: id})`
- Couleurs : primary Olibo pour home, secondary pour away

**derniers-evenements.widget.ts**
- Liste des 10 derniers événements de match (buts, cartons)
- Format : icône type événement + description + heure
- Source : `MatchService` (événements récents)

### Étape 3.2 — dashboard.ts final
- Importer et déclarer les 5 nouveaux widgets
- Injecter `CompetitionService` pour charger la compétition active
- Passer `competitionId` aux widgets via `@Input()`
- Gérer l'état "aucune compétition active" avec un message approprié

### Étape 3.3 — app.menu.ts
- Restructurer le menu en 4 sections : Tableau de bord | Compétition | Équipes & Joueurs | Administration
- Conditionner la section Administration aux rôles `['super_admin', 'admin_competition']`
- Injecter `AuthService` pour lire le rôle courant

### Étape 3.4 — app.topbar.ts
- Injecter `AuthService`
- Afficher `currentUser$ | async` : prénom, nom et badge rôle
- Lier le bouton logout à `authService.logout()`

---

## Règles de travail

- Lis toujours le fichier AVANT de le modifier
- Annonce chaque fichier créé ou supprimé
- Conserve le style de code existant (pas de type hints supplémentaires en Python, même structure try/except)
- Ne change pas les noms de routes Flask existantes
- Si tu dois ajouter un import, vérifie qu'il n'existe pas déjà
- Pour chaque sprint, confirme la liste des fichiers impactés avant de commencer

**Commence par lire `olibo_final_audit.md`, puis liste-moi les fichiers que tu vas toucher en Sprint 1 avant de commencer.**

