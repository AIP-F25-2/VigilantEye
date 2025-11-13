from __future__ import annotations

import sys
import types
from pathlib import Path
from unittest import mock

import pytest

from src.utils import model_manager as model_manager_module
from src.utils.model_manager import ModelManager


class DummyConfig:
    def __init__(self, cache_path: Path):
        self.MODELS_CACHE_PATH = str(cache_path)
        self.BLIP2_MODEL_NAME = "Salesforce/blip2-opt-2.7b"


@pytest.fixture
def cache_dir(tmp_path: Path) -> Path:
    return tmp_path / "models_cache"


@pytest.fixture
def config(cache_dir: Path) -> DummyConfig:
    return DummyConfig(cache_path=cache_dir)


@pytest.fixture
def manager(config: DummyConfig) -> ModelManager:
    return ModelManager(config=config)


def test_get_model_path(manager: ModelManager, cache_dir: Path) -> None:
    path = manager.get_model_path("yolov8")
    assert path.exists()
    assert path == cache_dir / "yolov8"


def test_download_yolov8_model_success(monkeypatch: pytest.MonkeyPatch, manager: ModelManager, tmp_path: Path) -> None:
    source_ckpt = tmp_path / "yolov8n.pt"
    source_ckpt.write_bytes(b"weights")

    class FakeYOLO:
        def __init__(self, *_args, **_kwargs):
            self.ckpt_path = source_ckpt

    monkeypatch.setitem(
        sys.modules,
        "ultralytics",
        types.SimpleNamespace(YOLO=FakeYOLO),
    )

    path, error = manager.download_yolov8_model("yolov8n.pt")
    assert error is None
    assert Path(path).exists()
    assert Path(path).read_bytes() == b"weights"


def test_download_yolov8_model_already_cached(manager: ModelManager) -> None:
    target = manager.get_model_path("yolov8") / "yolov8n.pt"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(b"cached")

    path, error = manager.download_yolov8_model("yolov8n.pt")
    assert error is None
    assert Path(path) == target


def test_download_mtcnn_weights(manager: ModelManager) -> None:
    success, error = manager.download_mtcnn_weights()
    assert success is True
    assert error is None


def test_download_arcface_model(monkeypatch: pytest.MonkeyPatch, manager: ModelManager) -> None:
    class FakeArcFace:
        def __init__(self, *_args, **_kwargs):
            pass

    monkeypatch.setitem(
        sys.modules,
        "facenet_pytorch",
        types.SimpleNamespace(InceptionResnetV1=FakeArcFace),
    )
    path, error = manager.download_arcface_model()
    assert error is None
    assert isinstance(path, str)


def test_download_osnet_model(monkeypatch: pytest.MonkeyPatch, manager: ModelManager) -> None:
    class FakeExtractor:
        def __init__(self, *_args, **_kwargs):
            pass

        def __call__(self, *_args, **_kwargs):
            return [0]

    monkeypatch.setitem(
        sys.modules,
        "torchreid.utils",
        types.SimpleNamespace(FeatureExtractor=FakeExtractor),
    )
    path, error = manager.download_osnet_model()
    assert error is None
    assert isinstance(path, str)


def test_download_mivolo_model(monkeypatch: pytest.MonkeyPatch, manager: ModelManager) -> None:
    fake_model = object()

    def fake_from_pretrained(*_args, **_kwargs):
        return fake_model

    monkeypatch.setitem(
        sys.modules,
        "transformers",
        types.SimpleNamespace(AutoModel=types.SimpleNamespace(from_pretrained=fake_from_pretrained)),
    )
    path, error = manager.download_mivolo_model()
    assert error is None
    assert isinstance(path, str)


def test_download_blip2_model_creates_sentinel(monkeypatch: pytest.MonkeyPatch, manager: ModelManager) -> None:
    cache_dir = manager.get_model_path("blip2")

    def fake_processor_from_pretrained(*_args, cache_dir: str, **_kwargs):
        processor_config = Path(cache_dir) / "processor" / "config.json"
        processor_config.parent.mkdir(parents=True, exist_ok=True)
        processor_config.write_text("{}", encoding="utf-8")
        return object()

    def fake_model_from_pretrained(*_args, cache_dir: str, **_kwargs):
        model_weights = Path(cache_dir) / "model" / "model.safetensors"
        model_weights.parent.mkdir(parents=True, exist_ok=True)
        model_weights.write_bytes(b"x")
        return object()

    monkeypatch.setitem(
        sys.modules,
        "transformers",
        types.SimpleNamespace(
            Blip2Processor=types.SimpleNamespace(from_pretrained=fake_processor_from_pretrained),
            Blip2ForConditionalGeneration=types.SimpleNamespace(from_pretrained=fake_model_from_pretrained),
        ),
    )

    sentinel_path, error = manager.download_blip2_model()

    assert error is None
    assert sentinel_path is not None
    sentinel = Path(sentinel_path)
    assert sentinel.exists()
    assert sentinel.parent == cache_dir
    assert any(cache_dir.glob("**/config.json"))
    assert any(cache_dir.glob("**/*.safetensors"))


def test_verify_all_models_all_present(monkeypatch: pytest.MonkeyPatch, manager: ModelManager) -> None:
    for name, filename in [
        ("yolov8", "yolov8n.pt"),
        ("arcface", "model.pt"),
        ("osnet", "osnet_x1_0.pth"),
        ("mivolo", "model.pth"),
    ]:
        target = manager.get_model_path(name) / filename
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"x")

    blip_cache = manager.get_model_path("blip2")
    sentinel = blip_cache / "model.pth"
    sentinel.write_text("ready", encoding="utf-8")
    model_weights = blip_cache / "model" / "model.safetensors"
    model_weights.parent.mkdir(parents=True, exist_ok=True)
    model_weights.write_bytes(b"x")
    processor_config = blip_cache / "processor" / "config.json"
    processor_config.parent.mkdir(parents=True, exist_ok=True)
    processor_config.write_text("{}", encoding="utf-8")

    # Mock verification methods for models that require runtime checks
    monkeypatch.setattr(manager, "_verify_whisper", lambda: True)
    monkeypatch.setattr(manager, "_verify_yamnet", lambda: True)
    monkeypatch.setattr(manager, "_verify_ollama", lambda: True)

    status = manager.verify_all_models()
    assert all(status.values())


def test_verify_all_models_some_missing(manager: ModelManager) -> None:
    target = manager.get_model_path("yolov8") / "yolov8n.pt"
    target.write_bytes(b"x")

    status = manager.verify_all_models()
    assert status["yolov8"] is True
    assert status["arcface"] is False
    assert status["osnet"] is False
    assert status["mivolo"] is False
    assert status["blip2"] is False


def test_verify_blip2_success_with_sentinel(manager: ModelManager) -> None:
    cache_dir = manager.get_model_path("blip2")
    sentinel = cache_dir / "model.pth"
    sentinel.write_text("ready", encoding="utf-8")
    model_weights = cache_dir / "model" / "model.safetensors"
    model_weights.parent.mkdir(parents=True, exist_ok=True)
    model_weights.write_bytes(b"x")

    assert manager._verify_blip2() is True


def _mock_response(content: bytes, status: int = 200) -> mock.MagicMock:
    response = mock.MagicMock()
    response.__enter__.return_value = response
    response.__exit__.return_value = False
    response.iter_content.return_value = [content]
    response.headers = {"content-length": str(len(content))}
    response.status_code = status
    response.raise_for_status.return_value = None
    return response


def test_download_from_url_success(monkeypatch: pytest.MonkeyPatch, manager: ModelManager, tmp_path: Path) -> None:
    target = tmp_path / "file.bin"
    response = _mock_response(b"payload")

    monkeypatch.setattr(model_manager_module.requests, "get", mock.MagicMock(return_value=response))

    assert manager._download_from_url("http://example.com/model", target) is True
    assert target.read_bytes() == b"payload"


def test_download_from_url_network_error(monkeypatch: pytest.MonkeyPatch, manager: ModelManager, tmp_path: Path) -> None:
    target = tmp_path / "file.bin"

    def raise_error(*_args, **_kwargs):
        raise ConnectionError("network down")

    monkeypatch.setattr(model_manager_module.requests, "get", raise_error)
    assert manager._download_from_url("http://example.com/model", target) is False


def test_download_whisper_model_success(monkeypatch: pytest.MonkeyPatch, manager: ModelManager) -> None:
    """Test successful Whisper model download."""
    mock_model = object()

    def fake_load_model(model_size: str, download_root: str, device: str = "cpu"):
        target_dir = Path(download_root)
        target_dir.mkdir(parents=True, exist_ok=True)
        model_file = target_dir / f"{model_size}.pt"
        model_file.write_bytes(b"whisper weights")
        return mock_model

    monkeypatch.setitem(
        sys.modules,
        "whisper",
        types.SimpleNamespace(load_model=fake_load_model),
    )

    path, error = manager.download_whisper_model("base")
    assert error is None
    assert path is not None
    assert Path(path).exists()


def test_download_whisper_model_already_cached(manager: ModelManager) -> None:
    """Test Whisper model download when already cached."""
    target = manager.get_model_path("whisper") / "base.pt"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(b"cached whisper")

    path, error = manager.download_whisper_model("base")
    assert error is None
    assert Path(path) == target


def test_download_whisper_model_different_sizes(monkeypatch: pytest.MonkeyPatch, manager: ModelManager) -> None:
    """Test downloading different Whisper model sizes."""
    mock_model = object()

    def fake_load_model(model_size: str, download_root: str, device: str = "cpu"):
        target_dir = Path(download_root)
        target_dir.mkdir(parents=True, exist_ok=True)
        model_file = target_dir / f"{model_size}.pt"
        model_file.write_bytes(b"whisper weights")
        return mock_model

    monkeypatch.setitem(
        sys.modules,
        "whisper",
        types.SimpleNamespace(load_model=fake_load_model),
    )

    for size in ["tiny", "base", "small"]:
        path, error = manager.download_whisper_model(size)
        assert error is None
        assert Path(path).name == f"{size}.pt"


def test_download_yamnet_model_success(monkeypatch: pytest.MonkeyPatch, manager: ModelManager) -> None:
    """Test successful YAMNet model download."""
    mock_model = object()

    def fake_load(url: str):
        return mock_model

    monkeypatch.setitem(
        sys.modules,
        "tensorflow_hub",
        types.SimpleNamespace(load=fake_load),
    )

    path, error = manager.download_yamnet_model()
    assert error is None
    assert path is not None
    assert Path(path).exists()


def test_download_yamnet_model_already_cached(manager: ModelManager) -> None:
    """Test YAMNet model download when already cached."""
    target = manager.get_model_path("yamnet") / "model.h5"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("YAMNet cache ready\n", encoding="utf-8")

    path, error = manager.download_yamnet_model()
    assert error is None
    assert Path(path) == target


def test_verify_all_models_includes_audio(monkeypatch: pytest.MonkeyPatch, manager: ModelManager) -> None:
    """Test that verify_all_models includes Whisper and YAMNet."""
    # Mock all models as available
    for name, filename in [
        ("yolov8", "yolov8n.pt"),
        ("arcface", "model.pt"),
        ("osnet", "osnet_x1_0.pth"),
        ("mivolo", "model.pth"),
        ("whisper", "base.pt"),
        ("yamnet", "model.h5"),
    ]:
        target = manager.get_model_path(name) / filename
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"x")

    blip_cache = manager.get_model_path("blip2")
    sentinel = blip_cache / "model.pth"
    sentinel.write_text("ready", encoding="utf-8")
    model_weights = blip_cache / "model" / "model.safetensors"
    model_weights.parent.mkdir(parents=True, exist_ok=True)
    model_weights.write_bytes(b"x")

    # Mock Whisper and YAMNet verification
    def fake_whisper_load(*_args, **_kwargs):
        return object()

    def fake_yamnet_load(*_args, **_kwargs):
        return object()

    monkeypatch.setitem(
        sys.modules,
        "whisper",
        types.SimpleNamespace(load_model=fake_whisper_load),
    )
    monkeypatch.setitem(
        sys.modules,
        "tensorflow_hub",
        types.SimpleNamespace(load=fake_yamnet_load),
    )

    status = manager.verify_all_models()
    assert "whisper" in status
    assert "yamnet" in status
    assert len(status) == 8  # All 8 models


def test_verify_whisper(monkeypatch: pytest.MonkeyPatch, manager: ModelManager) -> None:
    """Test Whisper verification."""
    mock_model = object()

    def fake_load_model(*_args, **_kwargs):
        return mock_model

    monkeypatch.setitem(
        sys.modules,
        "whisper",
        types.SimpleNamespace(load_model=fake_load_model),
    )

    assert manager._verify_whisper() is True


def test_verify_whisper_unavailable(monkeypatch: pytest.MonkeyPatch, manager: ModelManager) -> None:
    """Test Whisper verification when unavailable."""
    monkeypatch.setitem(
        sys.modules,
        "whisper",
        None,
    )
    monkeypatch.setattr("builtins.__import__", lambda name, **kwargs: (_ for _ in ()).throw(ImportError("No module named 'whisper'")))

    # Mock import to raise ImportError
    def raise_import_error(*_args, **_kwargs):
        raise ImportError("No module named 'whisper'")

    monkeypatch.setattr("builtins.__import__", raise_import_error)

    # Since we can't easily mock the import in _verify_whisper, we'll test the error path differently
    # by making load_model raise an exception
    def fake_load_model(*_args, **_kwargs):
        raise RuntimeError("Whisper unavailable")

    monkeypatch.setitem(
        sys.modules,
        "whisper",
        types.SimpleNamespace(load_model=fake_load_model),
    )

    assert manager._verify_whisper() is False


def test_verify_yamnet(monkeypatch: pytest.MonkeyPatch, manager: ModelManager) -> None:
    """Test YAMNet verification."""
    mock_model = object()

    def fake_load(*_args, **_kwargs):
        return mock_model

    monkeypatch.setitem(
        sys.modules,
        "tensorflow_hub",
        types.SimpleNamespace(load=fake_load),
    )

    assert manager._verify_yamnet() is True


def test_verify_yamnet_unavailable(monkeypatch: pytest.MonkeyPatch, manager: ModelManager) -> None:
    """Test YAMNet verification when unavailable."""
    def fake_load(*_args, **_kwargs):
        raise RuntimeError("YAMNet unavailable")

    monkeypatch.setitem(
        sys.modules,
        "tensorflow_hub",
        types.SimpleNamespace(load=fake_load),
    )

    assert manager._verify_yamnet() is False


def test_download_ollama_model_success(monkeypatch: pytest.MonkeyPatch, manager: ModelManager) -> None:
    """Test successful Ollama model download."""
    mock_client = mock.Mock()
    mock_client.list.return_value = {"models": []}  # Model not cached
    mock_client.pull.return_value = None  # Pull succeeds

    class FakeOllama:
        def Client(self, host=None):
            return mock_client

    monkeypatch.setitem(sys.modules, "ollama", FakeOllama())

    success, error = manager.download_ollama_model("llama3.2:1b", "http://localhost:11434")
    assert success is True
    assert error is None
    assert mock_client.pull.called
    assert mock_client.pull.call_args[0][0] == "llama3.2:1b"


def test_download_ollama_model_already_cached(monkeypatch: pytest.MonkeyPatch, manager: ModelManager) -> None:
    """Test Ollama model download when already cached."""
    mock_client = mock.Mock()
    mock_client.list.return_value = {"models": [{"name": "llama3.2:1b"}]}  # Model already cached

    class FakeOllama:
        def Client(self, host=None):
            return mock_client

    monkeypatch.setitem(sys.modules, "ollama", FakeOllama())

    success, error = manager.download_ollama_model("llama3.2:1b", "http://localhost:11434")
    assert success is True
    assert error is None
    assert not mock_client.pull.called  # Should not call pull if already cached


def test_download_ollama_model_connection_error(monkeypatch: pytest.MonkeyPatch, manager: ModelManager) -> None:
    """Test Ollama model download when service unavailable."""
    import requests

    class FakeOllama:
        def Client(self, host=None):
            raise requests.exceptions.ConnectionError("Ollama service unavailable")

    monkeypatch.setitem(sys.modules, "ollama", FakeOllama())

    success, error = manager.download_ollama_model("llama3.2:1b", "http://localhost:11434")
    assert success is False
    assert error is not None
    assert "ConnectionError" in str(type(error)) or "unavailable" in str(error).lower()


def test_download_ollama_model_pull_fails(monkeypatch: pytest.MonkeyPatch, manager: ModelManager) -> None:
    """Test Ollama model download when pull fails."""
    mock_client = mock.Mock()
    mock_client.list.return_value = {"models": []}  # Model not cached
    mock_client.pull.side_effect = Exception("Model not found")

    class FakeOllama:
        def Client(self, host=None):
            return mock_client

    monkeypatch.setitem(sys.modules, "ollama", FakeOllama())

    success, error = manager.download_ollama_model("invalid-model", "http://localhost:11434")
    assert success is False
    assert error is not None


def test_verify_ollama_success(monkeypatch: pytest.MonkeyPatch, manager: ModelManager) -> None:
    """Test Ollama verification when service available."""
    mock_client = mock.Mock()
    mock_client.list.return_value = {"models": []}

    class FakeOllama:
        def Client(self, host=None):
            return mock_client

    monkeypatch.setitem(sys.modules, "ollama", FakeOllama())

    assert manager._verify_ollama("http://localhost:11434") is True


def test_verify_ollama_unavailable(monkeypatch: pytest.MonkeyPatch, manager: ModelManager) -> None:
    """Test Ollama verification when service unavailable."""
    import requests

    class FakeOllama:
        def Client(self, host=None):
            raise requests.exceptions.ConnectionError("Service unavailable")

    monkeypatch.setitem(sys.modules, "ollama", FakeOllama())

    assert manager._verify_ollama("http://localhost:11434") is False


def test_verify_all_models_includes_ollama(monkeypatch: pytest.MonkeyPatch, manager: ModelManager) -> None:
    """Test that verify_all_models includes Ollama check."""
    # Mock all models as available
    monkeypatch.setattr(manager, "_verify_yolov8", lambda: True)
    monkeypatch.setattr(manager, "_verify_mtcnn", lambda: True)
    monkeypatch.setattr(manager, "_verify_arcface", lambda: True)
    monkeypatch.setattr(manager, "_verify_osnet", lambda: True)
    monkeypatch.setattr(manager, "_verify_mivolo", lambda: True)
    monkeypatch.setattr(manager, "_verify_blip2", lambda: True)
    monkeypatch.setattr(manager, "_verify_whisper", lambda: True)
    monkeypatch.setattr(manager, "_verify_yamnet", lambda: True)
    monkeypatch.setattr(manager, "_verify_ollama", lambda: True)

    checks = manager.verify_all_models()

    assert "ollama" in checks
    assert checks["ollama"] is True
    assert len(checks) == 9  # All 9 models including Ollama

