import numpy as np
import pytest

from src.ai_modules.speech_to_text import SpeechToTextError, SpeechToTextService
from src.utils.model_manager import ModelManager


@pytest.fixture(autouse=True)
def reset_speech_to_text_singleton():
    SpeechToTextService._instance = None
    yield
    SpeechToTextService._instance = None


@pytest.fixture
def sample_audio_path(tmp_path):
    """Create a dummy audio file path for testing."""
    audio_file = tmp_path / "test_audio.wav"
    audio_file.write_bytes(b"dummy audio data")
    return str(audio_file)


@pytest.fixture
def mock_whisper_model(mocker):
    """Mock Whisper model."""
    mock_model = mocker.Mock()
    mock_model.transcribe.return_value = {
        "text": "This is a test transcription",
        "segments": [
            {"text": "This is a test", "start": 0.0, "end": 2.0, "no_speech_prob": 0.1},
            {"text": "transcription", "start": 2.0, "end": 4.0, "no_speech_prob": 0.05},
        ],
        "language": "en",
        "language_prob": 0.95,
    }
    return mock_model


def test_load_models_success(mocker):
    """Test successful Whisper model loading."""
    mocker.patch.object(
        ModelManager,
        "download_whisper_model",
        return_value=("models_cache/whisper/base.pt", None),
    )
    mock_model = mocker.Mock()
    mocker.patch("whisper.load_model", return_value=mock_model)

    service = SpeechToTextService()
    service._load_models()

    assert service.whisper_model is mock_model
    assert service._models_loaded is True


def test_load_models_whisper_unavailable(mocker):
    """Test graceful degradation when Whisper download fails."""
    mocker.patch.object(
        ModelManager,
        "download_whisper_model",
        return_value=(None, RuntimeError("download failure")),
    )

    service = SpeechToTextService()
    service._load_models()

    assert service.whisper_model is None
    assert service._models_loaded is True


def test_transcribe_audio_success(mocker, sample_audio_path, mock_whisper_model):
    """Test successful audio transcription."""
    mocker.patch("librosa.load", return_value=(np.random.randn(16000 * 3), 16000))
    mocker.patch.object(SpeechToTextService, "_reduce_noise", return_value=np.random.randn(16000 * 3))
    mocker.patch.object(
        SpeechToTextService,
        "_detect_speaker_changes",
        return_value=[
            {"text": "This is a test", "start": 0.0, "end": 2.0, "speaker_id": 1},
            {"text": "transcription", "start": 2.0, "end": 4.0, "speaker_id": 1},
        ],
    )

    service = SpeechToTextService()
    service._models_loaded = True
    service.whisper_model = mock_whisper_model

    result, error = service.transcribe_audio(sample_audio_path)

    assert error is None
    assert result["transcription"] == "This is a test transcription"
    assert result["language"] == "en"
    assert len(result["segments"]) == 2
    assert result["segments"][0]["speaker_id"] == 1


def test_transcribe_audio_with_threat_keywords(mocker, sample_audio_path, mock_whisper_model):
    """Test transcription with threat keyword detection."""
    mock_whisper_model.transcribe.return_value = {
        "text": "I have a gun and need help",
        "segments": [{"text": "I have a gun and need help", "start": 0.0, "end": 3.0, "no_speech_prob": 0.1}],
        "language": "en",
        "language_prob": 0.9,
    }

    mocker.patch("librosa.load", return_value=(np.random.randn(16000 * 3), 16000))
    mocker.patch.object(SpeechToTextService, "_reduce_noise", return_value=np.random.randn(16000 * 3))
    mocker.patch.object(
        SpeechToTextService,
        "_detect_speaker_changes",
        return_value=[{"text": "I have a gun and need help", "start": 0.0, "end": 3.0, "speaker_id": 1}],
    )

    service = SpeechToTextService()
    service._models_loaded = True
    service.whisper_model = mock_whisper_model

    result, error = service.transcribe_audio(sample_audio_path)

    assert error is None
    assert "gun" in result["threat_keywords"]
    assert "help" in result["threat_keywords"]


def test_transcribe_audio_with_profanity(mocker, sample_audio_path, mock_whisper_model):
    """Test transcription with profanity detection."""
    mock_whisper_model.transcribe.return_value = {
        "text": "This is a badword1 test",
        "segments": [{"text": "This is a badword1 test", "start": 0.0, "end": 2.0, "no_speech_prob": 0.1}],
        "language": "en",
        "language_prob": 0.9,
    }

    mocker.patch("librosa.load", return_value=(np.random.randn(16000 * 3), 16000))
    mocker.patch.object(SpeechToTextService, "_reduce_noise", return_value=np.random.randn(16000 * 3))
    mocker.patch.object(
        SpeechToTextService,
        "_detect_speaker_changes",
        return_value=[{"text": "This is a badword1 test", "start": 0.0, "end": 2.0, "speaker_id": 1}],
    )

    service = SpeechToTextService()
    service.profanity_keywords = ["badword1", "badword2"]
    service._models_loaded = True
    service.whisper_model = mock_whisper_model

    result, error = service.transcribe_audio(sample_audio_path)

    assert error is None
    assert result["profanity_detected"] is True
    assert "badword1" in result["profanity_keywords"]


def test_transcribe_audio_no_speech(mocker, sample_audio_path, mock_whisper_model):
    """Test transcription with no speech (silence or noise only)."""
    mock_whisper_model.transcribe.return_value = {
        "text": "",
        "segments": [],
        "language": "en",
        "language_prob": 0.5,
    }

    mocker.patch("librosa.load", return_value=(np.random.randn(16000 * 3), 16000))
    mocker.patch.object(SpeechToTextService, "_reduce_noise", return_value=np.random.randn(16000 * 3))

    service = SpeechToTextService()
    service._models_loaded = True
    service.whisper_model = mock_whisper_model

    result, error = service.transcribe_audio(sample_audio_path)

    assert error is None
    assert result["transcription"] == ""
    assert len(result["segments"]) == 0


def test_transcribe_audio_non_english(mocker, sample_audio_path, mock_whisper_model):
    """Test transcription with non-English language."""
    mock_whisper_model.transcribe.return_value = {
        "text": "Hola mundo",
        "segments": [{"text": "Hola mundo", "start": 0.0, "end": 2.0, "no_speech_prob": 0.1}],
        "language": "es",
        "language_prob": 0.9,
    }

    mocker.patch("librosa.load", return_value=(np.random.randn(16000 * 3), 16000))
    mocker.patch.object(SpeechToTextService, "_reduce_noise", return_value=np.random.randn(16000 * 3))
    mocker.patch.object(
        SpeechToTextService,
        "_detect_speaker_changes",
        return_value=[{"text": "Hola mundo", "start": 0.0, "end": 2.0, "speaker_id": 1}],
    )

    service = SpeechToTextService()
    service._models_loaded = True
    service.whisper_model = mock_whisper_model

    result, error = service.transcribe_audio(sample_audio_path)

    assert error is None
    assert result["language"] == "es"
    assert result["transcription"] == "Hola mundo"


def test_reduce_noise(mocker):
    """Test noise reduction preprocessing."""
    service = SpeechToTextService()
    audio = np.random.randn(16000 * 3)
    sr = 16000

    mocker.patch("librosa.effects.preemphasis", return_value=audio)
    mocker.patch("librosa.effects.trim", return_value=(audio, None))
    mocker.patch("librosa.util.normalize", return_value=audio)

    processed = service._reduce_noise(audio, sr)

    assert processed is not None
    assert len(processed) == len(audio)


def test_detect_speaker_changes(mocker):
    """Test speaker change detection."""
    service = SpeechToTextService()
    audio = np.random.randn(16000 * 5)
    sr = 16000
    segments = [
        {"text": "First segment", "start": 0.0, "end": 2.0},
        {"text": "Second segment", "start": 2.5, "end": 4.5},
    ]

    mocker.patch("librosa.effects.split", return_value=[(0, 16000 * 2), (16000 * 3, 16000 * 5)])

    result = service._detect_speaker_changes(audio, sr, segments)

    assert len(result) == 2
    assert "speaker_id" in result[0]
    assert result[0]["speaker_id"] >= 1


def test_detect_keywords_found():
    """Test keyword detection when keywords are found."""
    service = SpeechToTextService()
    text = "I heard a gunshot and someone yelling for help"
    keywords = ["gun", "help", "fire"]

    matched = service._detect_keywords(text, keywords)

    assert "gun" in matched
    assert "help" in matched


def test_detect_keywords_case_insensitive():
    """Test case-insensitive keyword matching."""
    service = SpeechToTextService()
    text = "HELP ME PLEASE"
    keywords = ["help"]

    matched = service._detect_keywords(text, keywords)

    assert "help" in matched


def test_detect_keywords_whole_word_only():
    """Test whole-word keyword matching."""
    service = SpeechToTextService()
    text = "I helped my friend"
    keywords = ["help"]

    matched = service._detect_keywords(text, keywords)

    # "helped" should not match "help" (whole word only)
    assert "help" not in matched or len(matched) == 0


def test_fallback_transcription():
    """Test fallback transcription when Whisper unavailable."""
    service = SpeechToTextService()
    service.whisper_model = None

    result = service._fallback_transcription()

    assert result["transcription"] == ""
    assert result["confidence"] == 0.0
    assert result["language"] == "unknown"


def test_transcribe_audio_file_not_found(mocker):
    """Test error handling for non-existent audio file."""
    service = SpeechToTextService()
    service._models_loaded = True
    service.whisper_model = mocker.Mock()

    mocker.patch("librosa.load", side_effect=FileNotFoundError("File not found"))

    result, error = service.transcribe_audio("nonexistent.wav")

    assert error is not None
    assert isinstance(error, SpeechToTextError)


def test_transcribe_audio_invalid_format(mocker):
    """Test error handling for invalid audio format."""
    service = SpeechToTextService()
    service._models_loaded = True
    service.whisper_model = mocker.Mock()

    mocker.patch("librosa.load", side_effect=Exception("Unsupported format"))

    result, error = service.transcribe_audio("invalid.xyz")

    assert error is not None
    assert isinstance(error, SpeechToTextError)

