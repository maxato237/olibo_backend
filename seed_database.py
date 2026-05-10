"""
OLIBO LEAGUE - SCRIPT DE SEED COMPLET (VERSION MISE À JOUR)
Génère des données de test pour développement et testing
Placer ce fichier à la racine du projet
"""

import sys
import os
import random
from datetime import datetime, timedelta, date
from faker import Faker
from werkzeug.security import generate_password_hash

# Ajoute le répertoire courant au path Python
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Importe l'app en PREMIER
from olibo import create_app, db

fake = Faker('fr_FR')

# ==========================================
# CONFIGURATION
# ==========================================

TEAMS_COUNT = 9
MEMBERS_PER_TEAM = 15          # joueurs + staff par équipe
COMPETITIONS_COUNT = 3
MATCHES_COUNT = 100
MATCH_SHEETS_COUNT = 100
MATCH_EVENTS_COUNT = 200
VOTES_COUNT = 100
PAYMENTS_COUNT = 100
INCIDENT_REPORTS_COUNT = 50
MEDIA_COUNT = 100
NEWS_COUNT = 100

# ==========================================
# IMAGES QUI MARCHENT VRAIMENT
# ==========================================

def player_photo_url(seed: str) -> str:
    """Photo de personne via picsum (toujours disponible)."""
    return f"https://picsum.photos/seed/{seed}/200/200"

def team_logo_url(seed: str) -> str:
    """Logo d'équipe carré."""
    return f"https://picsum.photos/seed/logo_{seed}/300/300"

def news_image_url(seed: str) -> str:
    return f"https://picsum.photos/seed/news_{seed}/800/400"

def media_image_url(seed: str) -> str:
    return f"https://picsum.photos/seed/media_{seed}/800/600"

def license_doc_url(member_id: int) -> str:
    return f"https://picsum.photos/seed/license_{member_id}/400/600"

# ==========================================
# HELPER FUNCTIONS
# ==========================================

def create_users():
    """Crée les utilisateurs de tous les rôles."""
    print("Creating users...")
    from olibo.users.model import User

    users = []
    roles_list = [
        'super_admin',
        'admin_competition',
        'operator',
        'referee',
        'commissioner',
        'team_manager',
        'coach',
    ]

    # Préfixe téléphone Cameroun
    def make_phone(index: int) -> str:
        return f"+237{6}{random.randint(50000000, 99999999)}{index:02d}"[:16]

    for role in roles_list:
        count = 1 if role == 'super_admin' else 2
        for i in range(count):
            user = User(
                email=f'{role}_{i}@olibo.com',
                password_hash=generate_password_hash('password123'),
                first_name=fake.first_name(),
                last_name=fake.last_name(),
                phone=f'+2376{random.randint(10000, 99999)}{role[:2]}{i}',
                role=role,
                is_active=True,
            )
            db.session.add(user)
            users.append(user)

    db.session.commit()
    print(f"✓ Created {len(users)} users (staff)")
    return users


def create_teams(users):
    """Crée les équipes."""
    print("Creating teams...")
    from olibo.team.model import Team

    team_names = [
        "FC Yaoundé United",
        "Cameroon Warriors",
        "Panthers FC",
        "Eagles Team",
        "Diamonds United",
        "Golden Stars",
        "Phoenix FC",
        "Legends United",
        "Victory Squad",
    ]

    reps = [u for u in users if u.role in ['operator', 'team_captain']]

    teams = []
    for i, name in enumerate(team_names[:TEAMS_COUNT]):
        slug = name.replace(' ', '_').lower()
        team_obj = Team(
            name=name,
            logo=team_logo_url(slug),
            logo_public_id=None,
            description=fake.sentence(),
            representative_id=reps[i % len(reps)].id if reps else None,
        )
        db.session.add(team_obj)
        teams.append(team_obj)

    db.session.commit()
    print(f"✓ Created {len(teams)} teams")
    return teams


def create_members(teams):
    """
    Crée les membres de chaque équipe (TeamMember).
    Chaque équipe reçoit des joueurs + du staff.
    Retourne la liste des membres joueurs uniquement (pour licences, événements…).
    """
    print("Creating team members...")
    from olibo.team.model import TeamMember

    positions = [
        'GK', 'CB', 'RCB', 'LCB', 'RB', 'LB', 'RWB', 'LWB',
        'CDM', 'CM', 'CAM', 'RM', 'LM', 'BOX_TO_BOX',
        'RW', 'LW', 'ST', 'CF', 'SECOND_STRIKER', 'FALSE_9',
    ]
    nationalities = [
        ('CMR', 'Cameroun'), ('SEN', 'Sénégal'), ('CIV', "Côte d'Ivoire"),
        ('GHA', 'Ghana'), ('NGA', 'Nigeria'), ('MLI', 'Mali'), ('GUI', 'Guinée'),
        ('MAR', 'Maroc'), ('ALG', 'Algérie'),
    ]
    feet = ['Droit', 'Gauche', 'Ambidextre']
    categories = ['Senior', 'Junior', 'Espoir', 'Cadet', 'Minime']
    non_unique_staff = ['fitness_coach', 'doctor', 'physiotherapist', 'other']

    all_members = []
    all_players = []

    for team_idx, team_obj in enumerate(teams):
        # --- Joueurs ---
        for p in range(11):          # 11 joueurs minimum
            jersey = p + 1
            seed   = f"team{team_obj.id}_player{p}"
            nat_code, nat_label = random.choice(nationalities)
            member = TeamMember(
                team_id=team_obj.id,
                role='player',
                first_name=fake.first_name(),
                last_name=fake.last_name(),
                birth_date=date(
                    random.randint(1990, 2005),
                    random.randint(1, 12),
                    random.randint(1, 28),
                ),
                photo=player_photo_url(seed),
                photo_public_id=None,
                position=random.choice(positions),
                jersey_number=jersey,
                nationality=nat_code,
                nationality_label=nat_label,
                preferred_foot=random.choice(feet),
                height_cm=random.randint(165, 195),
                weight_kg=random.randint(60, 90),
                gender=random.choice(['M', 'F']),
                category=random.choice(categories),
                is_captain=(p == 0),   # le joueur n°1 est capitaine
                is_active=True,
            )
            db.session.add(member)
            all_members.append(member)
            all_players.append(member)

        # --- Staff (4 membres) : 1 coach + 1 assistant + 2 rôles non-uniques ---
        staff_roles_for_team = ['coach', 'assistant_coach'] + random.sample(non_unique_staff, 2)
        for s, staff_role in enumerate(staff_roles_for_team):
            seed = f"team{team_obj.id}_staff{s}"
            nat_code, nat_label = random.choice(nationalities)
            member = TeamMember(
                team_id=team_obj.id,
                role=staff_role,
                first_name=fake.first_name(),
                last_name=fake.last_name(),
                photo=player_photo_url(seed),
                photo_public_id=None,
                nationality=nat_code,
                nationality_label=nat_label,
                gender=random.choice(['M', 'F']),
                is_active=True,
            )
            db.session.add(member)
            all_members.append(member)

    db.session.commit()
    print(f"✓ Created {len(all_members)} team members ({len(all_players)} players)")
    return all_players   # on retourne uniquement les joueurs


def create_licenses(players, seasons=None):
    """Crée les licences pour les joueurs (TeamMember avec role='player')."""
    print("Creating licenses...")
    from olibo.license.model import License

    active_season = next((s for s in seasons if s.is_active), None) if seasons else None
    season_label = active_season.label if active_season else str(datetime.utcnow().year)
    season_id = active_season.id if active_season else None

    licenses = []
    for member in players:
        license_number = f"OL-{season_label}-{member.team_id:03d}-{member.id:03d}"
        member.license_number = license_number
        lic = License(
            member_id=member.id,
            season_id=season_id,
            license_number=license_number,
            issue_date=datetime.utcnow() - timedelta(days=365),
            expiry_date=datetime.utcnow() + timedelta(days=180),
            is_valid=True,
            document_url=license_doc_url(member.id),
        )
        db.session.add(lic)
        licenses.append(lic)

    db.session.commit()
    print(f"✓ Created {len(licenses)} licenses")
    return licenses


def create_seasons():
    """Crée les saisons sportives."""
    print("Creating seasons...")
    from olibo.season.model import Season

    seasons_data = [
        {
            'name': 'Saison 2024/25',
            'label': '2024/25',
            'start_date': date(2024, 8, 1),
            'end_date': date(2025, 6, 30),
            'is_active': False,
        },
        {
            'name': 'Saison 2025/26',
            'label': '2025/26',
            'start_date': date(2025, 8, 1),
            'end_date': date(2026, 6, 30),
            'is_active': True,
        },
    ]

    seasons = []
    for s in seasons_data:
        season = Season(**s)
        db.session.add(season)
        seasons.append(season)

    db.session.commit()
    print(f"✓ Created {len(seasons)} seasons")
    return seasons


def create_competitions(seasons=None):
    """Crée les compétitions liées à la saison active."""
    print("Creating competitions...")
    from olibo.competition.model import Competition
    from olibo.common.enums import CompetitionType

    active_season = next((s for s in seasons if s.is_active), seasons[-1]) if seasons else None

    comps_data = [
        {
            'name': 'Championnat Élite',
            'competition_type': CompetitionType.LEAGUE,
            'is_active': True,
            'ranking_rules': {
                'preset': 'ligue_1',
                'tiebreaker_order': ['points', 'head_to_head', 'goal_difference', 'goals_for', 'fair_play'],
            },
        },
        {
            'name': 'Coupe Nationale',
            'competition_type': CompetitionType.LEAGUE,
            'is_active': True,
            'ranking_rules': {
                'preset': 'classique',
                'tiebreaker_order': ['points', 'goal_difference', 'goals_for', 'clean_sheets'],
            },
        },
    ]

    competitions = []
    for data in comps_data:
        start_date = datetime.utcnow() - timedelta(days=random.randint(60, 120))
        competition = Competition(
            name=data['name'],
            description=fake.sentence(),
            start_date=start_date,
            end_date=start_date + timedelta(days=150),
            season=active_season.label if active_season else '2025/26',
            season_id=active_season.id if active_season else None,
            is_active=data['is_active'],
            competition_type=data['competition_type'],
            ranking_rules=data['ranking_rules'],
        )
        db.session.add(competition)
        competitions.append(competition)

    db.session.commit()
    print(f"✓ Created {len(competitions)} competitions")
    return competitions


def create_matches(competitions, teams, users):
    """Crée les matchs."""
    print("Creating matches...")
    from olibo.match_sheet.model import Match
    from olibo.common.enums import MatchStatus

    matches  = []
    referees = [u for u in users if u.role in ['referee', 'commissioner']]

    for comp in competitions:
        per_comp = MATCHES_COUNT // len(competitions)
        for _ in range(per_comp):
            home_team = random.choice(teams)
            away_team = random.choice([t for t in teams if t.id != home_team.id])

            match_date = comp.start_date + timedelta(days=random.randint(0, 100))
            status     = random.choice([MatchStatus.COMPLETED.value, MatchStatus.SCHEDULED.value])

            match = Match(
                competition_id=comp.id,
                season_id=comp.season_id,
                home_team_id=home_team.id,
                away_team_id=away_team.id,
                scheduled_date=match_date,
                status=status,
                home_team_goals=random.randint(0, 5) if status == MatchStatus.COMPLETED.value else None,
                away_team_goals=random.randint(0, 5) if status == MatchStatus.COMPLETED.value else None,
                matchday=random.randint(1, 30),
                location=fake.city(),
                referee_id=random.choice(referees).id if referees else None,
            )
            db.session.add(match)
            matches.append(match)

    db.session.commit()
    print(f"✓ Created {len(matches)} matches")
    return matches


def create_match_sheets(matches, users):
    """Crée les feuilles de match."""
    print("Creating match sheets...")
    from olibo.match_sheet.model import MatchSheet

    match_sheets = []
    referees = [u for u in users if u.role in ['referee', 'commissioner']]
    admins   = [u for u in users if u.role == 'admin_competition']

    for match in matches[:MATCH_SHEETS_COUNT]:
        sheet = MatchSheet(
            match_id=match.id,
            filled_by_id=random.choice(referees).id if referees else users[0].id,
            validated_by_id=random.choice(admins).id if admins else None,
            is_validated=random.random() > 0.3,
            notes=fake.sentence(),
            filled_at=match.scheduled_date,
            validated_at=match.scheduled_date + timedelta(days=1) if random.random() > 0.5 else None,
        )
        db.session.add(sheet)
        match_sheets.append(sheet)

    db.session.commit()
    print(f"✓ Created {len(match_sheets)} match sheets")
    return match_sheets


def create_match_events(matches, players):
    """
    Crée les événements de match.
    Les joueurs sont maintenant des TeamMember, filtrés par team_id.
    """
    print("Creating match events...")
    from olibo.match_sheet.model import MatchEvent

    events     = []
    event_types = ['goal', 'assist', 'yellow_card', 'red_card', 'substitution']

    for _ in range(min(MATCH_EVENTS_COUNT, len(matches) * 2)):
        match = random.choice(matches)
        # Récupère les joueurs des deux équipes du match
        eligible = [
            p for p in players
            if p.team_id in (match.home_team_id, match.away_team_id)
        ]
        if not eligible:
            continue

        player   = random.choice(eligible)
        evt_type = random.choice(event_types)

        event = MatchEvent(
            match_id=match.id,
            member_id=player.id,               # ← member_id (TeamMember)
            event_type=evt_type,
            minute=random.randint(1, 90),
            card_type=random.choice(['yellow', 'red']) if 'card' in evt_type else None,
            notes=fake.sentence() if random.random() > 0.7 else None,
        )
        db.session.add(event)
        events.append(event)

    db.session.commit()
    print(f"✓ Created {len(events)} match events")
    return events


def create_rankings(competitions, teams):
    """Crée les classements avec tous les champs du modèle."""
    print("Creating rankings...")
    from olibo.ranking.model import Ranking

    rankings = []
    for comp in competitions:
        shuffled = list(teams)
        random.shuffle(shuffled)
        for pos, team_obj in enumerate(shuffled, 1):
            wins          = random.randint(0, 15)
            draws         = random.randint(0, 6)
            losses        = random.randint(0, 10)
            goals_for     = random.randint(5, 60)
            goals_against = random.randint(5, 50)
            ranking = Ranking(
                competition_id=comp.id,
                team_id=team_obj.id,
                position=pos,
                matches_played=wins + draws + losses,
                wins=wins,
                draws=draws,
                losses=losses,
                goals_for=goals_for,
                goals_against=goals_against,
                goal_difference=goals_for - goals_against,
                points=wins * 3 + draws,
                yellow_cards=random.randint(0, 30),
                red_cards=random.randint(0, 5),
                clean_sheets=random.randint(0, wins),
            )
            db.session.add(ranking)
            rankings.append(ranking)

    db.session.commit()
    print(f"✓ Created {len(rankings)} rankings")
    return rankings


def create_votes(competitions, players, users):
    """Crée les votes."""
    print("Creating votes...")
    from olibo.voting.model import Vote

    votes      = []
    vote_types = ['player_of_day', 'player_of_competition']

    for _ in range(VOTES_COUNT):
        try:
            vote = Vote(
                voter_id=random.choice(users).id,
                member_id=random.choice(players).id,   # ← member_id
                competition_id=random.choice(competitions).id,
                vote_type=random.choice(vote_types),
                matchday=random.randint(1, 30) if random.random() > 0.5 else None,
            )
            db.session.add(vote)
            votes.append(vote)
        except Exception:
            db.session.rollback()
            continue

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()

    print(f"✓ Created {len(votes)} votes")
    return votes


def create_vote_results(competitions, players):
    """Crée les résultats de votes."""
    print("Creating vote results...")
    from olibo.voting.model import VoteResult

    results    = []
    vote_types = ['player_of_day', 'player_of_competition']

    for comp in competitions:
        for vote_type in vote_types:
            sample = random.sample(players, min(10, len(players)))
            for member in sample:
                result = VoteResult(
                    member_id=member.id,               # ← member_id
                    competition_id=comp.id,
                    vote_type=vote_type,
                    matchday=random.randint(1, 30) if vote_type == 'player_of_day' else None,
                    vote_count=random.randint(1, 50),
                )
                db.session.add(result)
                results.append(result)

    db.session.commit()
    print(f"✓ Created {len(results)} vote results")
    return results


def create_payments(users, teams):
    """Crée les paiements."""
    print("Creating payments...")
    from olibo.payment.model import Payment
    from olibo.common.enums import PaymentStatus

    payments        = []
    payment_types   = ['registration_fee', 'other']
    payment_methods = ['card', 'mobile_money', 'bank_transfer']

    for i in range(PAYMENTS_COUNT):
        payment = Payment(
            user_id=random.choice(users).id,
            team_id=random.choice(teams).id,
            amount=round(random.uniform(10000, 100000), 2),
            currency='XAF',
            payment_type=random.choice(payment_types),
            status=random.choice([
                PaymentStatus.PENDING.value,
                PaymentStatus.COMPLETED.value,
                PaymentStatus.FAILED.value,
            ]),
            transaction_id=f'TXN-{i:06d}-{random.randint(1000, 9999)}',
            payment_method=random.choice(payment_methods),
            proof_url=media_image_url(f'payment_{i}'),
        )
        db.session.add(payment)
        payments.append(payment)

    db.session.commit()
    print(f"✓ Created {len(payments)} payments")
    return payments


def create_incident_reports(matches, players, users):
    """Crée les rapports d'incidents."""
    print("Creating incident reports...")
    from olibo.incident_report.model import IncidentReport

    reports        = []
    incident_types = ['violent_conduct', 'unsporting_behavior', 'verbal_abuse', 'equipment_issue']
    severities     = ['low', 'medium', 'high']
    statuses       = ['reported', 'under_review', 'resolved']
    referees       = [u for u in users if u.role in ['referee', 'commissioner']]

    for _ in range(INCIDENT_REPORTS_COUNT):
        match = random.choice(matches)
        report = IncidentReport(
            match_id=match.id,
            reporter_id=random.choice(referees).id if referees else users[0].id,
            member_id=random.choice(players).id if random.random() > 0.3 else None,  # ← member_id
            incident_type=random.choice(incident_types),
            description=fake.paragraph(),
            minute=random.randint(1, 90),
            severity=random.choice(severities),
            status=random.choice(statuses),
            resolution=fake.sentence() if random.random() > 0.5 else None,
        )
        db.session.add(report)
        reports.append(report)

    db.session.commit()
    print(f"✓ Created {len(reports)} incident reports")
    return reports


def create_media(users):
    """Crée les fichiers média."""
    print("Creating media...")
    from olibo.media.model import Media

    media_list = []
    file_types = ['image', 'video']

    for i in range(MEDIA_COUNT):
        media = Media(
            title=fake.sentence(),
            description=fake.paragraph(),
            file_url=media_image_url(str(i)),
            file_type=random.choice(file_types),
            uploaded_by_id=random.choice(users).id,
            is_published=random.random() > 0.3,
        )
        db.session.add(media)
        media_list.append(media)

    db.session.commit()
    print(f"✓ Created {len(media_list)} media files")
    return media_list


def create_news(users, competitions):
    """Crée les actualités."""
    print("Creating news...")
    from olibo.announcements.model import News

    news_list  = []
    authors    = [u for u in users if u.role in ['admin_competition', 'operator']]

    for i in range(NEWS_COUNT):
        news = News(
            title=fake.sentence(),
            content=fake.paragraph(nb_sentences=5),
            author_id=random.choice(authors).id if authors else None,
            competition_id=random.choice(competitions).id if competitions else None,
            featured_image=news_image_url(str(i)),
            is_published=random.random() > 0.2,
            published_at=(
                datetime.utcnow() - timedelta(days=random.randint(0, 60))
                if random.random() > 0.3 else None
            ),
        )
        db.session.add(news)
        news_list.append(news)

    db.session.commit()
    print(f"✓ Created {len(news_list)} news articles")
    return news_list


def create_notifications(users):
    """Crée les notifications."""
    print("Creating notifications...")
    from olibo.notification.model import Notification

    notifications      = []
    notification_types = [
        'match_scheduled', 'match_result', 'registration_validated',
        'payment_confirmed', 'incident_reported',
    ]

    for _ in range(50):
        notification = Notification(
            user_id=random.choice(users).id,
            title=fake.sentence(),
            message=fake.paragraph(),
            notification_type=random.choice(notification_types),
            is_read=random.random() > 0.5,
        )
        db.session.add(notification)
        notifications.append(notification)

    db.session.commit()
    print(f"✓ Created {len(notifications)} notifications")
    return notifications


def create_team_registrations(teams, users):
    """Crée les demandes d'inscription d'équipe."""
    print("Creating team registrations...")
    from olibo.team.model import TeamRegistration
    from olibo.common.enums import RegistrationStatus

    registrations = []
    admins        = [u for u in users if u.role in ['super_admin', 'admin_competition']]

    for team_obj in teams:
        status = random.choice([
            RegistrationStatus.PENDING.value,
            RegistrationStatus.VALIDATED.value,
            RegistrationStatus.REJECTED.value,
        ])
        validated_by_id  = random.choice(admins).id if admins and status != RegistrationStatus.PENDING.value else None
        validation_date  = datetime.utcnow() - timedelta(days=random.randint(1, 30)) if validated_by_id else None

        reg = TeamRegistration(
            team_id=team_obj.id,
            status=status,
            submission_date=datetime.utcnow() - timedelta(days=random.randint(31, 60)),
            validation_date=validation_date,
            validated_by_id=validated_by_id,
            rejection_reason=fake.sentence() if status == RegistrationStatus.REJECTED.value else None,
        )
        db.session.add(reg)
        registrations.append(reg)

    db.session.commit()
    print(f"✓ Created {len(registrations)} team registrations")
    return registrations


# ==========================================
# MAIN SEED FUNCTION
# ==========================================

def seed_database(app):
    """Lance le seed complet de la base de données."""

    with app.app_context():
        print("\n" + "=" * 60)
        print("OLIBO LEAGUE - DATABASE SEEDING")
        print("=" * 60 + "\n")

        try:
            from olibo.users.model import User

            user_count = User.query.count()

            if user_count > 0:
                response = input("⚠️  La base n'est pas vide. Continuer ? (yes/no): ")
                if response.lower() != 'yes':
                    print("Seeding annulé.")
                    return False
                print("Suppression des tables...")
                db.drop_all()

            print("Création des tables...")
            db.create_all()
            print("✓ Tables créées\n")

            # ── Seed dans l'ordre des dépendances ──────────────────────────
            users         = create_users()
            teams         = create_teams(users)
            registrations = create_team_registrations(teams, users)
            players       = create_members(teams)          # retourne uniquement les joueurs
            db_seasons    = create_seasons()
            licenses      = create_licenses(players, seasons=db_seasons)
            competitions  = create_competitions(seasons=db_seasons)
            matches       = create_matches(competitions, teams, users)
            match_sheets  = create_match_sheets(matches, users)
            events        = create_match_events(matches, players)
            rankings      = create_rankings(competitions, teams)
            votes         = create_votes(competitions, players, users)
            vote_results  = create_vote_results(competitions, players)
            payments      = create_payments(users, teams)
            inc_reports   = create_incident_reports(matches, players, users)
            media         = create_media(users)
            news          = create_news(users, competitions)
            notifications = create_notifications(users)

            # ── Résumé ────────────────────────────────────────────────────
            print("\n" + "=" * 60)
            print("SEEDING TERMINÉ - RÉSUMÉ")
            print("=" * 60)
            print(f"✓ Users              : {len(users)}")
            print(f"✓ Teams              : {len(teams)}")
            print(f"✓ Team registrations : {len(registrations)}")
            print(f"✓ Team members       : {sum(1 for _ in players)} players + staff")
            print(f"✓ Licenses           : {len(licenses)}")
            print(f"✓ Seasons            : {len(db_seasons)}")
            print(f"✓ Competitions       : {len(competitions)}")
            print(f"✓ Matches            : {len(matches)}")
            print(f"✓ Match sheets       : {len(match_sheets)}")
            print(f"✓ Match events       : {len(events)}")
            print(f"✓ Rankings           : {len(rankings)}")
            print(f"✓ Votes              : {len(votes)}")
            print(f"✓ Vote results       : {len(vote_results)}")
            print(f"✓ Payments           : {len(payments)}")
            print(f"✓ Incident reports   : {len(inc_reports)}")
            print(f"✓ Media              : {len(media)}")
            print(f"✓ News               : {len(news)}")
            print(f"✓ Notifications      : {len(notifications)}")
            print("=" * 60 + "\n")

            print("🎉 Base de données peuplée avec succès !")
            print("\n📝 Identifiants de test :")
            print("   Login par TÉLÉPHONE (champ 'telephone') + mot de passe")
            print()
            print("   Super admin  : super_admin_0@olibo.com  /  password123")
            print("   Admin comp.  : admin_competition_0@olibo.com  /  password123")
            print("   Opérateur    : operator_0@olibo.com  /  password123")
            print("   Arbitre      : referee_0@olibo.com  /  password123")
            print()
            print("   ⚠️  Le login se fait via le numéro de téléphone, pas l'email.")
            print("       Consultez la table users pour récupérer les numéros générés.")
            print()

            return True

        except Exception as e:
            print(f"\n❌ Erreur pendant le seeding : {str(e)}")
            import traceback
            traceback.print_exc()
            db.session.rollback()
            return False


# ==========================================
# RUN SCRIPT
# ==========================================

if __name__ == '__main__':
    app     = create_app()
    success = seed_database(app)
    sys.exit(0 if success else 1)