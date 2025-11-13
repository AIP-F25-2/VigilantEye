"""Unit tests for LLM Analyzer service."""

from datetime import datetime
from unittest.mock import MagicMock, Mock

import pytest

from src.ai_modules.llm_analyzer import LLMAnalysisError, LLMAnalyzerService
from src.utils.model_manager import ModelManager


@pytest.fixture(autouse=True)
def reset_llm_analyzer_singleton():
    """Reset singleton before and after each test."""
    LLMAnalyzerService._instance = None
    yield
    LLMAnalyzerService._instance = None


@pytest.fixture
def sample_ai_outputs():
    """Create sample AI outputs from all 5 modules."""
    return {
        "scene": {
            "scene_type": "outdoor",
            "lighting": "dark",
            "weather": "clear",
            "crowd_density": "sparse",
            "description": "Outdoor parking lot at night",
            "confidence": 0.85,
        },
        "persons": [
            {
                "person_id": "person_123",
                "age": 25,
                "gender": "male",
                "bbox": [100, 100, 200, 300],
                "confidence": 0.89,
                "clothing_description": "Dark jacket, black pants",
            }
        ],
        "objects": {
            "objects": [
                {"class_name": "knife", "threat_level": "high", "confidence": 0.92, "bbox": [150, 150, 180, 200]}
            ],
            "relationships": [
                {
                    "person_id": "person_123",
                    "object_id": "obj_1",
                    "relationship": "holding",
                    "object_threat_level": "high",
                }
            ],
            "threat_summary": {"max_threat_level": "high", "high_threat_count": 1},
        },
        "transcription": {
            "text": "",
            "language": "unknown",
            "threat_keywords": [],
            "profanity_detected": False,
            "confidence": 0.0,
        },
        "audio_events": {
            "detected_sounds": [
                {"class_name": "Glass", "urgency_level": "high", "timestamp": 42.5, "confidence": 0.91}
            ],
            "urgency_summary": {"max_urgency": "high", "high_count": 1},
            "confidence": 0.91,
        },
    }


@pytest.fixture
def mock_ollama_client(mocker):
    """Mock Ollama client."""
    mock_client = MagicMock()
    mock_client.list.return_value = {"models": [{"name": "llama3.2:1b"}]}
    mock_client.generate.return_value = {
        "response": '{"is_suspicious": true, "confidence": 0.92, "threat_level": "high", "reasoning": "Test reasoning", "recommended_action": "alert", "key_factors": ["weapon", "night"]}'
    }
    return mock_client


def test_load_models_success(mocker, mock_ollama_client):
    """Test successful Ollama model loading."""
    mocker.patch.object(ModelManager, "download_ollama_model", return_value=(True, None))
    mocker.patch("ollama.Client", return_value=mock_ollama_client)

    service = LLMAnalyzerService()
    service._load_models()

    assert service.ollama_client is not None
    assert service._models_loaded is True


def test_load_models_ollama_unavailable(mocker):
    """Test graceful degradation when Ollama service unavailable."""
    mocker.patch.object(ModelManager, "download_ollama_model", return_value=(False, ConnectionError("Service unavailable")))

    service = LLMAnalyzerService()
    service._load_models()

    assert service.ollama_client is None
    assert service._models_loaded is True


def test_analyze_situation_suspicious(mocker, sample_ai_outputs, mock_ollama_client):
    """Test LLM analysis of suspicious situation."""
    mocker.patch.object(ModelManager, "download_ollama_model", return_value=(True, None))
    mocker.patch("ollama.Client", return_value=mock_ollama_client)

    service = LLMAnalyzerService()
    service._models_loaded = True
    service.ollama_client = mock_ollama_client

    timestamp = datetime(2024, 1, 15, 22, 30, 0)
    result, error = service.analyze_situation(sample_ai_outputs, timestamp, "Parking Lot")

    assert error is None
    assert result["is_suspicious"] is True
    assert result["threat_level"] == "high"
    assert result["confidence"] == 0.92
    assert "weapon" in result["key_factors"] or "night" in result["key_factors"]


def test_analyze_situation_not_suspicious(mocker, sample_ai_outputs, mock_ollama_client):
    """Test LLM analysis of non-suspicious situation."""
    # Modify outputs to be non-suspicious
    sample_ai_outputs["scene"]["lighting"] = "bright"
    sample_ai_outputs["scene"]["time_of_day"] = "day"
    sample_ai_outputs["objects"]["objects"] = []
    sample_ai_outputs["audio_events"]["detected_sounds"] = []

    mock_ollama_client.generate.return_value = {
        "response": '{"is_suspicious": false, "confidence": 0.88, "threat_level": "low", "reasoning": "Normal activity", "recommended_action": "ignore", "key_factors": ["daytime", "normal"]}'
    }

    mocker.patch.object(ModelManager, "download_ollama_model", return_value=(True, None))
    mocker.patch("ollama.Client", return_value=mock_ollama_client)

    service = LLMAnalyzerService()
    service._models_loaded = True
    service.ollama_client = mock_ollama_client

    timestamp = datetime(2024, 1, 15, 14, 0, 0)
    result, error = service.analyze_situation(sample_ai_outputs, timestamp, "Office")

    assert error is None
    assert result["is_suspicious"] is False
    assert result["threat_level"] == "low"


def test_analyze_situation_below_confidence_threshold(mocker, sample_ai_outputs, mock_ollama_client):
    """Test that low confidence overrides is_suspicious."""
    mock_ollama_client.generate.return_value = {
        "response": '{"is_suspicious": true, "confidence": 0.5, "threat_level": "medium", "reasoning": "Low confidence", "recommended_action": "monitor", "key_factors": ["factor1"]}'
    }

    mocker.patch.object(ModelManager, "download_ollama_model", return_value=(True, None))
    mocker.patch("ollama.Client", return_value=mock_ollama_client)

    service = LLMAnalyzerService()
    service.confidence_threshold = 0.7
    service._models_loaded = True
    service.ollama_client = mock_ollama_client

    timestamp = datetime(2024, 1, 15, 22, 30, 0)
    result, error = service.analyze_situation(sample_ai_outputs, timestamp, "Location")

    assert error is None
    assert result["is_suspicious"] is False  # Overridden due to low confidence
    assert "below threshold" in result["reasoning"].lower() or "confidence" in result["reasoning"].lower()


def test_analyze_situation_invalid_json_retry(mocker, sample_ai_outputs, mock_ollama_client):
    """Test retry logic when LLM returns invalid JSON."""
    # First call returns invalid JSON, second returns valid
    mock_ollama_client.generate.side_effect = [
        {"response": "This is not JSON"},
        {
            "response": '{"is_suspicious": true, "confidence": 0.9, "threat_level": "high", "reasoning": "Valid", "recommended_action": "alert", "key_factors": ["test"]}'
        },
    ]

    mocker.patch.object(ModelManager, "download_ollama_model", return_value=(True, None))
    mocker.patch("ollama.Client", return_value=mock_ollama_client)

    service = LLMAnalyzerService()
    service.max_retries = 2
    service._models_loaded = True
    service.ollama_client = mock_ollama_client

    timestamp = datetime(2024, 1, 15, 22, 30, 0)
    result, error = service.analyze_situation(sample_ai_outputs, timestamp, "Location")

    assert error is None
    assert result["is_suspicious"] is True
    assert mock_ollama_client.generate.call_count == 2  # Retry occurred


def test_analyze_situation_invalid_json_max_retries(mocker, sample_ai_outputs, mock_ollama_client):
    """Test fallback when all retries fail."""
    mock_ollama_client.generate.return_value = {"response": "Invalid JSON every time"}

    mocker.patch.object(ModelManager, "download_ollama_model", return_value=(True, None))
    mocker.patch("ollama.Client", return_value=mock_ollama_client)

    service = LLMAnalyzerService()
    service.max_retries = 2
    service.enable_fallback = True
    service._models_loaded = True
    service.ollama_client = mock_ollama_client

    timestamp = datetime(2024, 1, 15, 22, 30, 0)
    result, error = service.analyze_situation(sample_ai_outputs, timestamp, "Location")

    assert error is None
    assert result["confidence"] == 0.6  # Fallback confidence
    assert "rule-based" in result["reasoning"].lower() or "fallback" in result["reasoning"].lower()


def test_analyze_situation_timeout(mocker, sample_ai_outputs, mock_ollama_client):
    """Test fallback when LLM times out."""
    import time

    def timeout_generate(*args, **kwargs):
        time.sleep(0.1)  # Simulate delay
        raise TimeoutError("LLM timeout")

    mock_ollama_client.generate.side_effect = timeout_generate

    mocker.patch.object(ModelManager, "download_ollama_model", return_value=(True, None))
    mocker.patch("ollama.Client", return_value=mock_ollama_client)

    service = LLMAnalyzerService()
    service.enable_fallback = True
    service._models_loaded = True
    service.ollama_client = mock_ollama_client

    timestamp = datetime(2024, 1, 15, 22, 30, 0)
    result, error = service.analyze_situation(sample_ai_outputs, timestamp, "Location")

    assert error is None
    assert result["confidence"] == 0.6  # Fallback


def test_build_prompt_with_few_shot(mocker, sample_ai_outputs):
    """Test prompt building with few-shot examples."""
    mocker.patch.object(ModelManager, "download_ollama_model", return_value=(True, None))

    service = LLMAnalyzerService()
    service.use_few_shot = True
    service.use_chain_of_thought = False

    timestamp = datetime(2024, 1, 15, 22, 30, 0)
    prompt = service._build_prompt(sample_ai_outputs, timestamp, "Location")

    assert "Examples" in prompt
    assert "Example 1" in prompt or "Example" in prompt


def test_build_prompt_without_few_shot(mocker, sample_ai_outputs):
    """Test prompt building without few-shot examples."""
    mocker.patch.object(ModelManager, "download_ollama_model", return_value=(True, None))

    service = LLMAnalyzerService()
    service.use_few_shot = False
    service.use_chain_of_thought = False

    timestamp = datetime(2024, 1, 15, 22, 30, 0)
    prompt = service._build_prompt(sample_ai_outputs, timestamp, "Location")

    assert "Examples" not in prompt or "## Examples" not in prompt
    assert "TIME:" in prompt
    assert "LOCATION:" in prompt


def test_build_prompt_with_chain_of_thought(mocker, sample_ai_outputs):
    """Test prompt building with chain-of-thought instruction."""
    mocker.patch.object(ModelManager, "download_ollama_model", return_value=(True, None))

    service = LLMAnalyzerService()
    service.use_chain_of_thought = True

    timestamp = datetime(2024, 1, 15, 22, 30, 0)
    prompt = service._build_prompt(sample_ai_outputs, timestamp, "Location")

    assert "step by step" in prompt.lower() or "analyze" in prompt.lower()


def test_parse_and_validate_response_valid():
    """Test parsing valid JSON response."""
    service = LLMAnalyzerService()
    response_text = '{"is_suspicious": true, "confidence": 0.9, "threat_level": "high", "reasoning": "Test reasoning", "recommended_action": "alert", "key_factors": ["factor1", "factor2"]}'

    result = service._parse_and_validate_response(response_text)

    assert result is not None
    assert result["is_suspicious"] is True
    assert result["confidence"] == 0.9
    assert result["threat_level"] == "high"
    assert len(result["key_factors"]) == 2


def test_parse_and_validate_response_invalid_json():
    """Test parsing invalid JSON."""
    service = LLMAnalyzerService()
    response_text = "This is not JSON"

    result = service._parse_and_validate_response(response_text)

    assert result is None


def test_parse_and_validate_response_missing_fields():
    """Test validation fails when required fields missing."""
    service = LLMAnalyzerService()
    response_text = '{"is_suspicious": true, "confidence": 0.9}'  # Missing required fields

    result = service._parse_and_validate_response(response_text)

    assert result is None


def test_parse_and_validate_response_invalid_threat_level():
    """Test validation fails with invalid threat_level."""
    service = LLMAnalyzerService()
    response_text = '{"is_suspicious": true, "confidence": 0.9, "threat_level": "extreme", "reasoning": "Test", "recommended_action": "alert", "key_factors": ["test"]}'

    result = service._parse_and_validate_response(response_text)

    assert result is None


def test_fallback_analysis_high_threat_object(sample_ai_outputs):
    """Test fallback analysis with high-threat object."""
    service = LLMAnalyzerService()

    result = service._fallback_analysis(sample_ai_outputs)

    assert result["is_suspicious"] is True
    assert result["threat_level"] in ["high", "critical"]
    assert "weapon" in result["reasoning"].lower() or "knife" in result["reasoning"].lower()
    assert result["confidence"] == 0.6


def test_fallback_analysis_critical_audio(sample_ai_outputs):
    """Test fallback analysis with critical audio event."""
    sample_ai_outputs["audio_events"]["detected_sounds"] = [
        {"class_name": "Gunshot", "urgency_level": "critical", "timestamp": 42.5, "confidence": 0.95}
    ]
    sample_ai_outputs["objects"]["objects"] = []

    service = LLMAnalyzerService()

    result = service._fallback_analysis(sample_ai_outputs)

    assert result["is_suspicious"] is True
    assert result["threat_level"] == "critical"
    assert "gunshot" in result["reasoning"].lower() or "critical" in result["reasoning"].lower()


def test_fallback_analysis_threat_keywords(sample_ai_outputs):
    """Test fallback analysis with threat keywords."""
    sample_ai_outputs["transcription"]["threat_keywords"] = ["gun", "help"]
    sample_ai_outputs["objects"]["objects"] = []
    sample_ai_outputs["audio_events"]["detected_sounds"] = []

    service = LLMAnalyzerService()

    result = service._fallback_analysis(sample_ai_outputs)

    assert result["is_suspicious"] is True
    assert result["threat_level"] in ["medium", "high"]
    assert "threat keyword" in result["reasoning"].lower() or "gun" in result["reasoning"].lower()


def test_fallback_analysis_normal_situation(sample_ai_outputs):
    """Test fallback analysis with no suspicious indicators."""
    sample_ai_outputs["objects"]["objects"] = []
    sample_ai_outputs["audio_events"]["detected_sounds"] = []
    sample_ai_outputs["transcription"]["threat_keywords"] = []

    service = LLMAnalyzerService()

    result = service._fallback_analysis(sample_ai_outputs)

    assert result["is_suspicious"] is False
    assert result["threat_level"] == "low"
    assert "normal" in result["reasoning"].lower() or "no significant" in result["reasoning"].lower()


def test_get_few_shot_examples():
    """Test few-shot examples retrieval."""
    service = LLMAnalyzerService()

    examples = service._get_few_shot_examples()

    assert len(examples) >= 3
    assert len(examples) <= 5
    for example in examples:
        assert "input" in example
        assert "output" in example
        assert "is_suspicious" in example["output"]
        assert "confidence" in example["output"]
        assert "threat_level" in example["output"]


def test_format_ai_outputs_for_prompt(sample_ai_outputs):
    """Test formatting AI outputs for prompt."""
    service = LLMAnalyzerService()

    formatted = service._format_ai_outputs_for_prompt(sample_ai_outputs)

    assert "scene" in formatted
    assert "persons" in formatted
    assert "objects" in formatted
    assert "transcription" in formatted
    assert "audio_events" in formatted
    assert "outdoor" in formatted["scene"].lower() or "parking" in formatted["scene"].lower()
    assert "person" in formatted["persons"].lower()


def test_format_ai_outputs_missing_data():
    """Test formatting handles missing data gracefully."""
    service = LLMAnalyzerService()
    empty_outputs = {"scene": {}, "persons": [], "objects": {}, "transcription": {}, "audio_events": {}}

    formatted = service._format_ai_outputs_for_prompt(empty_outputs)

    assert "scene" in formatted
    assert "persons" in formatted
    assert "no" in formatted["persons"].lower() or "detected" in formatted["persons"].lower()


def test_analyze_situation_ollama_unavailable_fallback(mocker, sample_ai_outputs):
    """Test fallback when Ollama unavailable."""
    mocker.patch.object(ModelManager, "download_ollama_model", return_value=(False, ConnectionError("Unavailable")))

    service = LLMAnalyzerService()
    service.enable_fallback = True
    service._models_loaded = True

    timestamp = datetime(2024, 1, 15, 22, 30, 0)
    result, error = service.analyze_situation(sample_ai_outputs, timestamp, "Location")

    assert error is None
    assert result["confidence"] == 0.6  # Fallback confidence


def test_analyze_situation_fallback_disabled(mocker, sample_ai_outputs):
    """Test error when fallback disabled and Ollama unavailable."""
    mocker.patch.object(ModelManager, "download_ollama_model", return_value=(False, ConnectionError("Unavailable")))

    service = LLMAnalyzerService()
    service.enable_fallback = False
    service._models_loaded = True

    timestamp = datetime(2024, 1, 15, 22, 30, 0)
    result, error = service.analyze_situation(sample_ai_outputs, timestamp, "Location")

    assert error is not None
    assert isinstance(error, LLMAnalysisError)

