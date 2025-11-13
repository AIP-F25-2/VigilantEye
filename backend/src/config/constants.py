class UserRole:
    STAFF = "staff"
    ADMIN = "admin"


class TicketStatus:
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"


class TicketPriority:
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ThreatLevel:
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    CRITICAL = "critical"
    NONE = "none"


class ObjectCategory:
    WEAPON = "weapon"
    SHARP_OBJECT = "sharp_object"
    BLUNT_WEAPON = "blunt_weapon"
    BAG = "bag"
    TOOL = "tool"
    VEHICLE = "vehicle"
    ELECTRONICS = "electronics"
    CONTAINER = "container"
    COMMON_OBJECT = "common_object"


class SceneType:
    INDOOR = "indoor"
    OUTDOOR = "outdoor"
    UNKNOWN = "unknown"


class LightingCondition:
    BRIGHT = "bright"
    DIM = "dim"
    DARK = "dark"
    NIGHT = "night"


class WeatherCondition:
    CLEAR = "clear"
    RAINY = "rainy"
    FOGGY = "foggy"
    SNOWY = "snowy"
    UNKNOWN = "unknown"


class CrowdDensity:
    EMPTY = "empty"
    SPARSE = "sparse"
    MODERATE = "moderate"
    CROWDED = "crowded"


class VideoStatus:
    UPLOADING = "uploading"
    PROCESSING = "processing"
    READY = "ready"
    ANALYZING = "analyzing"
    ANALYZED = "analyzed"
    ERROR = "error"


class AnalysisResult:
    CLEAN = "clean"
    SUSPICIOUS = "suspicious"
    ERROR = "error"


class EvidenceType:
    FRAME = "frame"
    AUDIO = "audio"
    VIDEO = "video"


SUPPORTED_VIDEO_FORMATS = ["mp4", "avi", "mov", "mkv"]
SUPPORTED_IMAGE_FORMATS = ["jpg", "jpeg", "png"]
SUPPORTED_AUDIO_FORMATS = ["wav", "mp3", "aac"]


class UrgencyLevel:
    """Urgency levels for detected audio events."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class AudioCategory:
    """Categories for detected audio events."""

    VIOLENCE = "violence"
    DISTRESS = "distress"
    ALERT = "alert"
    BREAKING = "breaking"
    IMPACT = "impact"
    ANIMAL = "animal"
    VEHICLE = "vehicle"
    MOVEMENT = "movement"
    COMMUNICATION = "communication"
    AMBIENT = "ambient"


class RecommendedAction:
    """Recommended actions for ticket handling."""

    ALERT = "alert"
    MONITOR = "monitor"
    ESCALATE = "escalate"
    IGNORE = "ignore"


class AmbientNoiseLevel:
    """Ambient noise level classifications."""

    VERY_LOW = "very_low"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"


class ResponseCode:
    SUCCESS = 200
    CREATED = 201
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404
    CONFLICT = 409
    INTERNAL_ERROR = 500


class TelegramCallbackAction:
    """Telegram callback button actions."""

    ACKNOWLEDGE = "acknowledge"
    CLOSE = "close"
    ESCALATE = "escalate"
    VIEW_DETAILS = "view_details"


class AlertTemplate:
    """Alert template names."""

    ALERT = "alert"
    ESCALATION = "escalation"
    CONFIRMATION = "confirmation"
