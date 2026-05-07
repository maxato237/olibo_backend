from enum import Enum


class UserRole(Enum):
    SUPER_ADMIN = "super_admin"
    ADMIN_COMPETITION = "admin_competition"
    OPERATOR = "operator"
    # REFEREE = "referee"
    # COMMISSIONER = "commissioner"
    # TEAM_CAPTAIN = "team_captain"
    TEAM_MANAGER = "team_manager"
    # COACH = "coach"
    # PLAYER = "player"
    # SPECTATOR = "spectator"
    # JOURNALIST = "journalist"


class RegistrationStatus(Enum):
    PENDING = "pending"
    VALIDATED = "validated"
    REJECTED = "rejected"


class MatchStatus(Enum):
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class CardType(Enum):
    YELLOW = "yellow"
    RED = "red"


class VoteType(Enum):
    PLAYER_OF_DAY = "player_of_day"
    PLAYER_OF_COMPETITION = "player_of_competition"


class CompetitionType(Enum):
    LEAGUE = "league"
    CHAMPIONSHIP = "championship"


class PaymentStatus(Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"


# ──────────────────────────────────────────────────────────────────────────────
# Traductions françaises — display-only, jamais stockées en base
# ──────────────────────────────────────────────────────────────────────────────

ROLE_LABELS_FR = {
    "super_admin":        "Super Administrateur",
    "admin_competition":  "Administrateur Compétition",
    "operator":           "Opérateur",
    "referee":            "Arbitre",
    "commissioner":       "Commissaire",
    "team_captain":       "Capitaine d'équipe",
    "team_manager":       "Responsable d'équipe",
    "coach":              "Entraîneur",
    "player":             "Joueur",
    "spectator":          "Spectateur",
    "journalist":         "Journaliste",
}

REGISTRATION_STATUS_LABELS_FR = {
    "pending":   "En attente",
    "validated": "Validé",
    "rejected":  "Rejeté",
}

MATCH_STATUS_LABELS_FR = {
    "scheduled":   "Planifié",
    "in_progress": "En cours",
    "completed":   "Terminé",
    "cancelled":   "Annulé",
}

CARD_TYPE_LABELS_FR = {
    "yellow": "Carton jaune",
    "red":    "Carton rouge",
}

VOTE_TYPE_LABELS_FR = {
    "player_of_day":         "Joueur du jour",
    "player_of_competition": "Joueur de la compétition",
}

COMPETITION_TYPE_LABELS_FR = {
    "league":       "Championnat de ligue",
    "championship": "Championnat",
}

PAYMENT_STATUS_LABELS_FR = {
    "pending":   "En attente",
    "completed": "Complété",
    "failed":    "Échoué",
    "refunded":  "Remboursé",
}

TEAM_MEMBER_ROLE_LABELS_FR = {
    "player":          "Joueur",
    "coach":           "Entraîneur",
    "assistant_coach": "Entraîneur adjoint",
    "fitness_coach":   "Préparateur physique",
    "doctor":          "Médecin",
    "physiotherapist": "Kinésithérapeute",
    "manager":         "Manager",
    "other":           "Autre",
}

MATCH_EVENT_TYPE_LABELS_FR = {
    "goal":         "But",
    "assist":       "Passe décisive",
    "yellow_card":  "Carton jaune",
    "red_card":     "Carton rouge",
    "substitution": "Remplacement",
}

PAYMENT_TYPE_LABELS_FR = {
    "registration_fee": "Frais d'inscription",
    "other":            "Autre",
}


def get_label_fr(labels_dict: dict, value) -> str:
    """Retourne le label FR d'une valeur d'enum, ou la valeur elle-même si inconnue."""
    if value is None:
        return None
    return labels_dict.get(value, value)


class RankingPreset(Enum):
    PREMIER_LEAGUE = "premier_league"
    LIGUE_1        = "ligue_1"
    BUNDESLIGA     = "bundesliga"
    LIGA           = "liga"
    SERIE_A        = "serie_a"
    CUSTOM         = "custom"


RANKING_PRESET_RULES = {
    "premier_league": ["points", "goal_difference", "goals_for", "head_to_head", "fair_play"],
    "ligue_1":        ["points", "head_to_head", "goal_difference", "goals_for", "fair_play"],
    "bundesliga":     ["points", "goal_difference", "goals_for", "head_to_head", "fair_play"],
    "liga":           ["points", "head_to_head", "goal_difference", "goals_for", "fair_play"],
    "serie_a":        ["points", "head_to_head", "goal_difference", "goals_for", "fair_play"],
    "custom":         [],
}

RANKING_PRESET_LABELS_FR = {
    "premier_league": "Premier League",
    "ligue_1":        "Ligue 1",
    "bundesliga":     "Bundesliga",
    "liga":           "Liga",
    "serie_a":        "Serie A",
    "custom":         "Personnalisé",
}

RANKING_TIEBREAKER_LABELS_FR = {
    "points":          "Points",
    "goal_difference": "Différence de buts générale",
    "goals_for":       "Buts marqués",
    "head_to_head":    "Confrontations directes",
    "fair_play":       "Fair-play (cartons)",
    "clean_sheets":    "Clean sheets",
}
