import numpy as np
import pytest

from src.ai_modules.scene_analyzer import SceneAnalysisError, SceneAnalyzerService
from src.config.constants import (
    CrowdDensity,
    LightingCondition,
    SceneType,
    WeatherCondition,
)
from src.utils.model_manager import ModelManager


class _DummyTensor:
    def to(self, _device):
        return self


class _DummyProcessor:
    def __init__(self, caption: str):
        self.caption = caption

    def __call__(self, *args, **kwargs):
        return {"pixel_values": _DummyTensor()}

    def batch_decode(self, generated_ids, skip_special_tokens: bool = True):
        return [self.caption]


class _DummyModel:
    def generate(self, *args, **kwargs):
        return ["dummy"]


@pytest.fixture(autouse=True)
def reset_scene_analyzer_singleton():
    SceneAnalyzerService._instance = None
    yield
    SceneAnalyzerService._instance = None


@pytest.fixture
def dark_frame() -> np.ndarray:
    return np.full((480, 640, 3), 20, dtype=np.uint8)


@pytest.fixture
def bright_frame() -> np.ndarray:
    return np.full((480, 640, 3), 230, dtype=np.uint8)


@pytest.fixture
def medium_frame() -> np.ndarray:
    return np.full((480, 640, 3), 120, dtype=np.uint8)


def test_load_models_success(mocker):
    mocker.patch.object(
        ModelManager,
        "download_blip2_model",
        return_value=("models_cache/blip2/model.pth", None),
    )
    processor_mock = mocker.Mock()
    model_mock = mocker.Mock()
    model_mock.to.return_value = model_mock
    model_mock.eval.return_value = model_mock
    model_mock.parameters.return_value = [mocker.Mock()]

    mocker.patch("transformers.Blip2Processor.from_pretrained", return_value=processor_mock)
    mocker.patch("transformers.Blip2ForConditionalGeneration.from_pretrained", return_value=model_mock)

    analyzer = SceneAnalyzerService()
    analyzer._load_models()

    assert analyzer.blip2_processor is processor_mock
    assert analyzer.blip2_model is model_mock
    assert analyzer._models_loaded is True
    model_mock.eval.assert_called_once()


def test_load_models_blip2_unavailable(mocker):
    mocker.patch.object(
        ModelManager,
        "download_blip2_model",
        return_value=(None, RuntimeError("network error")),
    )

    analyzer = SceneAnalyzerService()
    analyzer._load_models()

    assert analyzer.blip2_model is None
    assert analyzer.blip2_processor is None
    assert analyzer._models_loaded is True


def test_analyze_scene_with_blip2(dark_frame):
    analyzer = SceneAnalyzerService()
    analyzer.blip2_processor = _DummyProcessor("An outdoor parking lot at night with dim lighting")
    analyzer.blip2_model = _DummyModel()
    analyzer._models_loaded = True

    result, error = analyzer.analyze_scene(dark_frame)

    assert error is None
    assert result["scene_type"] == SceneType.OUTDOOR
    assert result["lighting"] in {LightingCondition.NIGHT, LightingCondition.DIM}
    assert result["description"] == "An outdoor parking lot at night with dim lighting"
    assert result["confidence"] >= analyzer.scene_confidence_threshold


def test_analyze_scene_indoor(bright_frame):
    analyzer = SceneAnalyzerService()
    analyzer.blip2_processor = _DummyProcessor("An indoor office room with bright fluorescent lighting")
    analyzer.blip2_model = _DummyModel()
    analyzer._models_loaded = True

    result, error = analyzer.analyze_scene(bright_frame)

    assert error is None
    assert result["scene_type"] == SceneType.INDOOR
    assert result["lighting"] == LightingCondition.BRIGHT
    assert result["environment_details"]["location_type"] == "building"


def test_analyze_scene_crowded(medium_frame):
    analyzer = SceneAnalyzerService()
    analyzer.blip2_processor = _DummyProcessor("A crowded street with many people walking")
    analyzer.blip2_model = _DummyModel()
    analyzer._models_loaded = True

    result, error = analyzer.analyze_scene(medium_frame)

    assert error is None
    assert result["scene_type"] == SceneType.OUTDOOR
    assert result["crowd_density"] == CrowdDensity.CROWDED


def test_analyze_scene_fallback(dark_frame):
    analyzer = SceneAnalyzerService()
    analyzer._models_loaded = True
    analyzer.blip2_model = None
    analyzer.blip2_processor = None

    result, error = analyzer.analyze_scene(dark_frame)

    assert error is None
    assert result["confidence"] == 0.5
    assert result["description"].startswith("Fallback scene analysis")


def test_parse_scene_description_outdoor_night(dark_frame):
    analyzer = SceneAnalyzerService()
    analyzer.blip2_model = object()
    parsed = analyzer._parse_scene_description(
        "Outdoor parking lot at night with poor lighting",
        dark_frame,
    )

    assert parsed["scene_type"] == SceneType.OUTDOOR
    assert parsed["lighting"] in {LightingCondition.NIGHT, LightingCondition.DARK}
    assert parsed["time_of_day"] == "night"
    assert parsed["location_type"] == "parking_lot"


def test_parse_scene_description_indoor_day(bright_frame):
    analyzer = SceneAnalyzerService()
    analyzer.blip2_model = object()
    parsed = analyzer._parse_scene_description(
        "Indoor office with bright natural lighting",
        bright_frame,
    )

    assert parsed["scene_type"] == SceneType.INDOOR
    assert parsed["lighting"] == LightingCondition.BRIGHT
    assert parsed["time_of_day"] == "day"


def test_classify_location_type():
    analyzer = SceneAnalyzerService()
    assert analyzer._classify_location_type("parking lot near a mall") == "parking_lot"
    assert analyzer._classify_location_type("busy street corner downtown") == "street"
    assert analyzer._classify_location_type("corporate office building lobby") == "building"
    assert analyzer._classify_location_type("city park with trees") == "park"
    assert analyzer._classify_location_type("unknown location") == "unknown"


def test_estimate_time_of_day_night(dark_frame):
    analyzer = SceneAnalyzerService()
    assert analyzer._estimate_time_of_day(dark_frame, "night scene in city") == "night"


def test_estimate_time_of_day_day(bright_frame):
    analyzer = SceneAnalyzerService()
    assert analyzer._estimate_time_of_day(bright_frame, "sunny day downtown") == "day"


def test_fallback_scene_analysis(dark_frame):
    analyzer = SceneAnalyzerService()
    result = analyzer._fallback_scene_analysis(dark_frame)

    assert result["confidence"] == 0.5
    assert result["environment_details"]["visibility"] in {"good", "poor"}


def test_analyze_scene_empty_frame():
    analyzer = SceneAnalyzerService()
    result, error = analyzer.analyze_scene(np.array([]))

    assert result == {}
    assert isinstance(error, SceneAnalysisError)

