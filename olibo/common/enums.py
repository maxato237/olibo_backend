from enum import Enum

class UserRole(Enum):
    SUPER_ADMIN = "super_admin"
    ADMIN_COMPETITION = "admin_competition"
    OPERATOR = "operator"
    REFEREE = "referee"
    COMMISSIONER = "commissioner"
    TEAM_CAPTAIN = "team_captain"
    COACH = "coach"
    PLAYER = "player"
    SPECTATOR = "spectator"
    JOURNALIST = "journalist"

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

class PaymentStatus(Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"
