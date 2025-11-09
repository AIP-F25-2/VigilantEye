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
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


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


class ResponseCode:
    SUCCESS = 200
    CREATED = 201
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404
    CONFLICT = 409
    INTERNAL_ERROR = 500

