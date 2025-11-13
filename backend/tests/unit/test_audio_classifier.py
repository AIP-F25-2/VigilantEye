import numpy as np
import pytest

from src.ai_modules.audio_classifier import AudioClassificationError, AudioClassifierService
from src.config.constants import AudioCategory, UrgencyLevel
from src.utils.model_manager import ModelManager


@pytest.fixture(autouse=True)
def reset_audio_classifier_singleton():
    AudioClassifierService._instance = None
    yield
    AudioClassifierService._instance = None


@pytest.fixture
def sample_audio_path(tmp_path):
    """Create a dummy audio file path for testing."""
    audio_file = tmp_path / "test_audio.wav"
    audio_file.write_bytes(b"dummy audio data")
    return str(audio_file)


@pytest.fixture
def mock_yamnet_model(mocker):
    """Mock YAMNet model."""
    mock_model = mocker.Mock()
    # Create mock scores array: 3 segments, 521 classes
    scores = np.zeros((3, 521))
    # Set high scores for gunshot (class 0) and alarm (class 1) in first segment
    scores[0, 0] = 0.92  # gunshot
    scores[0, 1] = 0.85  # alarm
    # Set medium score for speech in second segment
    scores[1, 2] = 0.75  # speech
    # Set low scores in third segment
    scores[2, 3] = 0.3  # below threshold

    mock_model.return_value = (
        mocker.Mock(numpy=lambda: scores),  # scores
        mocker.Mock(),  # embeddings
        mocker.Mock(),  # spectrogram
    )
    return mock_model


def test_load_models_success(mocker):
    """Test successful YAMNet model loading."""
    mocker.patch.object(
        ModelManager,
        "download_yamnet_model",
        return_value=("models_cache/yamnet/model.h5", None),
    )
    mock_model = mocker.Mock()
    mock_model.class_names = [f"class_{i}" for i in range(521)]
    mocker.patch("tensorflow_hub.load", return_value=mock_model)
    mocker.patch("tensorflow_hub.resolve", return_value="mock_path")

    service = AudioClassifierService()
    service._load_models()

    assert service.yamnet_model is mock_model
    assert service._models_loaded is True


def test_load_models_yamnet_unavailable(mocker):
    """Test graceful degradation when YAMNet download fails."""
    mocker.patch.object(
        ModelManager,
        "download_yamnet_model",
        return_value=(None, RuntimeError("download failure")),
    )

    service = AudioClassifierService()
    service._load_models()

    assert service.yamnet_model is None
    assert service._models_loaded is True


def test_classify_audio_success(mocker, sample_audio_path, mock_yamnet_model):
    """Test successful audio classification."""
    mocker.patch("soundfile.read", return_value=(np.random.randn(16000 * 3), 16000))
    mocker.patch("librosa.to_mono", return_value=np.random.randn(16000 * 3))
    mocker.patch("librosa.resample", return_value=np.random.randn(16000 * 3))

    service = AudioClassifierService()
    service._models_loaded = True
    service.yamnet_model = mock_yamnet_model
    service.yamnet_class_names = [f"class_{i}" for i in range(521)]
    # Set class names for testing
    service.yamnet_class_names[0] = "Gunshot, gunfire"
    service.yamnet_class_names[1] = "Alarm"
    service.yamnet_class_names[2] = "Speech"

    result, error = service.classify_audio(sample_audio_path)

    assert error is None
    assert len(result["detected_sounds"]) > 0
    # Check that gunshot is detected with critical urgency
    gunshot_sounds = [s for s in result["detected_sounds"] if "Gunshot" in s["class_name"]]
    if gunshot_sounds:
        assert gunshot_sounds[0]["urgency_level"] == UrgencyLevel.CRITICAL
    assert result["urgency_summary"]["max_urgency"] in [UrgencyLevel.CRITICAL, UrgencyLevel.HIGH]


def test_classify_audio_multiple_segments(mocker, sample_audio_path, mock_yamnet_model):
    """Test classification with multiple time segments."""
    mocker.patch("soundfile.read", return_value=(np.random.randn(16000 * 5), 16000))
    mocker.patch("librosa.to_mono", return_value=np.random.randn(16000 * 5))
    mocker.patch("librosa.resample", return_value=np.random.randn(16000 * 5))

    service = AudioClassifierService()
    service._models_loaded = True
    service.yamnet_model = mock_yamnet_model
    service.yamnet_class_names = [f"class_{i}" for i in range(521)]

    result, error = service.classify_audio(sample_audio_path)

    assert error is None
    # Should have sounds from different timestamps
    timestamps = [s["timestamp"] for s in result["detected_sounds"]]
    assert len(set(timestamps)) >= 1  # At least one unique timestamp


def test_classify_audio_low_confidence_filtered(mocker, sample_audio_path, mock_yamnet_model):
    """Test that low-confidence sounds are filtered out."""
    mocker.patch("soundfile.read", return_value=(np.random.randn(16000 * 3), 16000))
    mocker.patch("librosa.to_mono", return_value=np.random.randn(16000 * 3))
    mocker.patch("librosa.resample", return_value=np.random.randn(16000 * 3))

    service = AudioClassifierService()
    service.audio_confidence_threshold = 0.5
    service._models_loaded = True
    service.yamnet_model = mock_yamnet_model
    service.yamnet_class_names = [f"class_{i}" for i in range(521)]

    result, error = service.classify_audio(sample_audio_path)

    assert error is None
    # All detected sounds should have confidence >= threshold
    for sound in result["detected_sounds"]:
        assert sound["confidence"] >= service.audio_confidence_threshold


def test_classify_audio_max_sounds_limit(mocker, sample_audio_path, mock_yamnet_model):
    """Test that max_sounds_per_segment limit is enforced."""
    # Create scores with 10 high-confidence sounds in first segment
    scores = np.zeros((1, 521))
    for i in range(10):
        scores[0, i] = 0.9  # All high confidence

    mock_model = mocker.Mock()
    mock_model.return_value = (
        mocker.Mock(numpy=lambda: scores),
        mocker.Mock(),
        mocker.Mock(),
    )

    mocker.patch("soundfile.read", return_value=(np.random.randn(16000 * 3), 16000))
    mocker.patch("librosa.to_mono", return_value=np.random.randn(16000 * 3))
    mocker.patch("librosa.resample", return_value=np.random.randn(16000 * 3))

    service = AudioClassifierService()
    service.max_sounds_per_segment = 5
    service._models_loaded = True
    service.yamnet_model = mock_model
    service.yamnet_class_names = [f"class_{i}" for i in range(521)]

    result, error = service.classify_audio(sample_audio_path)

    assert error is None
    # Should only return top 5 sounds per segment
    first_segment_sounds = [s for s in result["detected_sounds"] if s["timestamp"] == 0.0]
    assert len(first_segment_sounds) <= service.max_sounds_per_segment


def test_classify_audio_critical_urgency(mocker, sample_audio_path, mock_yamnet_model):
    """Test classification of critical urgency sounds."""
    scores = np.zeros((1, 521))
    scores[0, 0] = 0.92  # gunshot
    scores[0, 1] = 0.88  # explosion
    scores[0, 2] = 0.85  # scream

    mock_model = mocker.Mock()
    mock_model.return_value = (
        mocker.Mock(numpy=lambda: scores),
        mocker.Mock(),
        mocker.Mock(),
    )

    mocker.patch("soundfile.read", return_value=(np.random.randn(16000 * 3), 16000))
    mocker.patch("librosa.to_mono", return_value=np.random.randn(16000 * 3))
    mocker.patch("librosa.resample", return_value=np.random.randn(16000 * 3))

    service = AudioClassifierService()
    service._models_loaded = True
    service.yamnet_model = mock_model
    service.yamnet_class_names = ["Gunshot, gunfire", "Explosion", "Screaming"] + [f"class_{i}" for i in range(3, 521)]

    result, error = service.classify_audio(sample_audio_path)

    assert error is None
    assert result["urgency_summary"]["max_urgency"] == UrgencyLevel.CRITICAL
    assert result["urgency_summary"]["critical_count"] > 0


def test_classify_audio_high_urgency(mocker, sample_audio_path, mock_yamnet_model):
    """Test classification of high urgency sounds."""
    scores = np.zeros((1, 521))
    scores[0, 0] = 0.90  # alarm
    scores[0, 1] = 0.85  # siren
    scores[0, 2] = 0.88  # glass breaking

    mock_model = mocker.Mock()
    mock_model.return_value = (
        mocker.Mock(numpy=lambda: scores),
        mocker.Mock(),
        mocker.Mock(),
    )

    mocker.patch("soundfile.read", return_value=(np.random.randn(16000 * 3), 16000))
    mocker.patch("librosa.to_mono", return_value=np.random.randn(16000 * 3))
    mocker.patch("librosa.resample", return_value=np.random.randn(16000 * 3))

    service = AudioClassifierService()
    service._models_loaded = True
    service.yamnet_model = mock_model
    service.yamnet_class_names = ["Alarm", "Siren", "Glass"] + [f"class_{i}" for i in range(3, 521)]

    result, error = service.classify_audio(sample_audio_path)

    assert error is None
    assert result["urgency_summary"]["max_urgency"] == UrgencyLevel.HIGH
    assert result["urgency_summary"]["high_count"] > 0


def test_classify_audio_no_suspicious_sounds(mocker, sample_audio_path, mock_yamnet_model):
    """Test classification with only ambient sounds."""
    scores = np.zeros((1, 521))
    scores[0, 0] = 0.80  # music
    scores[0, 1] = 0.75  # speech
    scores[0, 2] = 0.70  # birds

    mock_model = mocker.Mock()
    mock_model.return_value = (
        mocker.Mock(numpy=lambda: scores),
        mocker.Mock(),
        mocker.Mock(),
    )

    mocker.patch("soundfile.read", return_value=(np.random.randn(16000 * 3), 16000))
    mocker.patch("librosa.to_mono", return_value=np.random.randn(16000 * 3))
    mocker.patch("librosa.resample", return_value=np.random.randn(16000 * 3))

    service = AudioClassifierService()
    service._models_loaded = True
    service.yamnet_model = mock_model
    service.yamnet_class_names = ["Music", "Speech", "Birds"] + [f"class_{i}" for i in range(3, 521)]

    result, error = service.classify_audio(sample_audio_path)

    assert error is None
    assert result["urgency_summary"]["max_urgency"] == UrgencyLevel.LOW


def test_estimate_ambient_noise_high(mocker):
    """Test ambient noise estimation for high noise."""
    service = AudioClassifierService()
    # Create high-energy audio
    audio = np.random.randn(16000 * 3) * 0.2  # High amplitude
    sr = 16000

    mocker.patch("librosa.feature.rms", return_value=np.array([[0.15] * 100]))  # High RMS

    noise_level = service._estimate_ambient_noise(audio, sr)

    assert noise_level == "high"


def test_estimate_ambient_noise_low(mocker):
    """Test ambient noise estimation for low noise."""
    service = AudioClassifierService()
    # Create low-energy audio
    audio = np.random.randn(16000 * 3) * 0.01  # Low amplitude
    sr = 16000

    mocker.patch("librosa.feature.rms", return_value=np.array([[0.005] * 100]))  # Low RMS

    noise_level = service._estimate_ambient_noise(audio, sr)

    assert noise_level in ["low", "very_low"]


def test_map_class_to_urgency_gunshot():
    """Test urgency mapping for gunshot."""
    service = AudioClassifierService()

    urgency, category = service._map_class_to_urgency("Gunshot, gunfire")

    assert urgency == UrgencyLevel.CRITICAL
    assert category == AudioCategory.VIOLENCE


def test_map_class_to_urgency_alarm():
    """Test urgency mapping for alarm."""
    service = AudioClassifierService()

    urgency, category = service._map_class_to_urgency("Alarm")

    assert urgency == UrgencyLevel.MEDIUM
    assert category == AudioCategory.ALERT


def test_map_class_to_urgency_unknown():
    """Test urgency mapping for unknown class."""
    service = AudioClassifierService()

    urgency, category = service._map_class_to_urgency("Unknown sound")

    assert urgency == UrgencyLevel.LOW
    assert category == AudioCategory.AMBIENT


def test_calculate_urgency_summary():
    """Test urgency summary calculation."""
    service = AudioClassifierService()
    detected_sounds = [
        {"urgency_level": UrgencyLevel.CRITICAL},
        {"urgency_level": UrgencyLevel.CRITICAL},
        {"urgency_level": UrgencyLevel.HIGH},
        {"urgency_level": UrgencyLevel.HIGH},
        {"urgency_level": UrgencyLevel.HIGH},
        {"urgency_level": UrgencyLevel.MEDIUM},
    ]

    summary = service._calculate_urgency_summary(detected_sounds)

    assert summary["max_urgency"] == UrgencyLevel.CRITICAL
    assert summary["critical_count"] == 2
    assert summary["high_count"] == 3
    assert summary["medium_count"] == 1
    assert summary["total_sounds"] == 6


def test_build_urgency_mappings():
    """Test urgency mappings structure."""
    service = AudioClassifierService()

    mappings = service._build_urgency_mappings()

    assert "Gunshot, gunfire" in mappings
    assert mappings["Gunshot, gunfire"]["urgency"] == UrgencyLevel.CRITICAL
    assert mappings["Alarm"]["urgency"] == UrgencyLevel.MEDIUM
    assert mappings["Screaming"]["urgency"] == UrgencyLevel.HIGH
    assert "urgency" in mappings["Gunshot, gunfire"]
    assert "category" in mappings["Gunshot, gunfire"]


def test_fallback_classification():
    """Test fallback classification when YAMNet unavailable."""
    service = AudioClassifierService()
    service.yamnet_model = None

    result = service._fallback_classification()

    assert len(result["detected_sounds"]) == 0
    assert result["confidence"] == 0.0
    assert result["urgency_summary"]["max_urgency"] == UrgencyLevel.LOW


def test_classify_audio_file_not_found(mocker):
    """Test error handling for non-existent audio file."""
    service = AudioClassifierService()
    service._models_loaded = True
    service.yamnet_model = mocker.Mock()

    mocker.patch("soundfile.read", side_effect=FileNotFoundError("File not found"))

    result, error = service.classify_audio("nonexistent.wav")

    assert error is not None
    assert isinstance(error, AudioClassificationError)

