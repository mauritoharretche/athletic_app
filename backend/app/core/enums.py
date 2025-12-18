import enum


class UserRole(str, enum.Enum):
    ATHLETE = "ATHLETE"
    COACH = "COACH"


class SessionType(str, enum.Enum):
    RODAJE = "RODAJE"
    PASADAS = "PASADAS"
    FARTLEK = "FARTLEK"
    CUESTAS = "CUESTAS"
    FUERZA = "FUERZA"
    TECNICA = "TECNICA"
    COMPETENCIA = "COMPETENCIA"
    DESCANSO = "DESCANSO"


class InviteStatus(str, enum.Enum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    DECLINED = "DECLINED"
