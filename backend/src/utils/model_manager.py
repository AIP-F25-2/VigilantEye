import logging
import shutil
from pathlib import Path
from typing import Dict, Optional, Tuple

import requests

from src.config.settings import get_config

logger = logging.getLogger(__name__)


class ModelManager:
    """Utility for managing AI model downloads and cached paths."""

    def __init__(self, config=None) -> None:
        self.config = config or get_config()
        self.models_cache_path = Path(self.config.MODELS_CACHE_PATH)
        self.models_cache_path.mkdir(parents=True, exist_ok=True)

    def get_model_path(self, model_name: str) -> Path:
        model_path = self.models_cache_path / model_name
        model_path.mkdir(parents=True, exist_ok=True)
        return model_path

    def download_yolov8_model(
        self, model_name: str = "yolov8n.pt"
    ) -> Tuple[Optional[str], Optional[Exception]]:
        try:
            target_dir = self.get_model_path("yolov8")
            target_path = target_dir / model_name

            if target_path.exists():
                logger.debug("YOLOv8 model already cached", extra={"context": {"path": str(target_path)}})
                return str(target_path), None

            from ultralytics import YOLO  # type: ignore

            logger.info("Downloading YOLOv8 model", extra={"context": {"model": model_name}})
            model = YOLO(model_name)
            ckpt_path = getattr(model, "ckpt_path", None) or getattr(model, "model", None)

            if ckpt_path is None:
                raise RuntimeError("YOLOv8 checkpoint path could not be determined")

            ckpt_path = Path(ckpt_path)
            target_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ckpt_path, target_path)
            logger.info("YOLOv8 model cached", extra={"context": {"path": str(target_path)}})
            return str(target_path), None
        except Exception as exc:  # pylint: disable=broad-except
            logger.exception("Failed to download YOLOv8 model", extra={"context": {"error": str(exc)}})
            return None, exc

    def download_mtcnn_weights(self) -> Tuple[bool, Optional[Exception]]:
        try:
            logger.info("MTCNN weights handled by library auto-download")
            return True, None
        except Exception as exc:  # pragma: no cover - defensive
            logger.exception("Failed during MTCNN preparation", extra={"context": {"error": str(exc)}})
            return False, exc

    def download_arcface_model(self) -> Tuple[Optional[str], Optional[Exception]]:
        try:
            target_dir = self.get_model_path("arcface")
            target_path = target_dir / "model.pt"

            if target_path.exists():
                logger.debug("ArcFace model already cached", extra={"context": {"path": str(target_path)}})
                return str(target_path), None

            from facenet_pytorch import InceptionResnetV1  # type: ignore

            logger.info("Downloading ArcFace (InceptionResnetV1) weights")
            InceptionResnetV1(pretrained="vggface2")  # auto-downloads to torch cache
            target_dir.mkdir(parents=True, exist_ok=True)
            return str(target_path), None
        except Exception as exc:  # pylint: disable=broad-except
            logger.exception("Failed to download ArcFace model", extra={"context": {"error": str(exc)}})
            return None, exc

    def download_osnet_model(
        self, model_name: str = "osnet_x1_0"
    ) -> Tuple[Optional[str], Optional[Exception]]:
        try:
            target_dir = self.get_model_path("osnet")
            target_path = target_dir / f"{model_name}.pth"

            if target_path.exists():
                logger.debug("OSNet model already cached", extra={"context": {"path": str(target_path)}})
                return str(target_path), None

            from torchreid.utils import FeatureExtractor  # type: ignore

            logger.info("Downloading OSNet model", extra={"context": {"model": model_name}})
            FeatureExtractor(model_name=model_name)  # auto-downloads to torch cache
            target_dir.mkdir(parents=True, exist_ok=True)
            return str(target_path), None
        except Exception as exc:  # pylint: disable=broad-except
            logger.exception("Failed to download OSNet model", extra={"context": {"error": str(exc)}})
            return None, exc

    def download_mivolo_model(self) -> Tuple[Optional[str], Optional[Exception]]:
        try:
            target_dir = self.get_model_path("mivolo")
            target_path = target_dir / "model.pth"

            if target_path.exists():
                logger.debug("MiVOLO model already cached", extra={"context": {"path": str(target_path)}})
                return str(target_path), None

            from transformers import (  # type: ignore
                AutoImageProcessor,
                AutoModelForImageClassification,
            )

            logger.info("Downloading MiVOLO model weights")
            AutoImageProcessor.from_pretrained("iitolstykh/mivolo_v2", cache_dir=str(target_dir))
            AutoModelForImageClassification.from_pretrained(
                "iitolstykh/mivolo_v2",
                cache_dir=str(target_dir),
            )
            target_dir.mkdir(parents=True, exist_ok=True)
            return str(target_path), None
        except Exception as exc:  # pylint: disable=broad-except
            logger.exception("Failed to download MiVOLO model", extra={"context": {"error": str(exc)}})
            return None, exc

    def download_blip2_model(
        self,
        model_name: Optional[str] = None,
    ) -> Tuple[Optional[str], Optional[Exception]]:
        try:
            resolved_model_name = model_name or getattr(self.config, "BLIP2_MODEL_NAME", "Salesforce/blip2-opt-2.7b")
            target_dir = self.get_model_path("blip2")
            sentinel_path = target_dir / "model.pth"

            if self._blip2_cache_complete(target_dir, sentinel_path):
                logger.debug(
                    "BLIP-2 model already cached",
                    extra={"context": {"model": resolved_model_name, "path": str(sentinel_path)}},
                )
                return str(sentinel_path), None

            from transformers import (  # type: ignore
                Blip2ForConditionalGeneration,
                Blip2Processor,
            )

            logger.info(
                "Downloading BLIP-2 model",
                extra={"context": {"model": resolved_model_name}},
            )
            Blip2Processor.from_pretrained(resolved_model_name, cache_dir=str(target_dir))
            Blip2ForConditionalGeneration.from_pretrained(resolved_model_name, cache_dir=str(target_dir))
            target_dir.mkdir(parents=True, exist_ok=True)
            sentinel_path.write_text(
                "BLIP-2 cache ready\n",
                encoding="utf-8",
            )
            logger.info(
                "BLIP-2 model cached",
                extra={"context": {"model": resolved_model_name, "path": str(sentinel_path)}},
            )
            return str(sentinel_path), None
        except Exception as exc:  # pylint: disable=broad-except
            logger.exception(
                "Failed to download BLIP-2 model",
                extra={"context": {"model": model_name or getattr(self.config, 'BLIP2_MODEL_NAME', 'Salesforce/blip2-opt-2.7b'), "error": str(exc)}},
            )
            return None, exc

    def download_whisper_model(
        self, model_size: str = "base"
    ) -> Tuple[Optional[str], Optional[Exception]]:
        try:
            target_dir = self.get_model_path("whisper")
            model_path = target_dir / f"{model_size}.pt"

            if model_path.exists():
                logger.debug(
                    "Whisper model already cached",
                    extra={"context": {"model_size": model_size, "path": str(model_path)}},
                )
                return str(model_path), None

            import whisper  # type: ignore

            logger.info(
                "Downloading Whisper model",
                extra={"context": {"model_size": model_size}},
            )
            model = whisper.load_model(model_size, download_root=str(target_dir))
            logger.info(
                "Whisper model cached",
                extra={"context": {"model_size": model_size, "path": str(model_path)}},
            )
            return str(model_path), None
        except Exception as exc:  # pylint: disable=broad-except
            logger.exception(
                "Failed to download Whisper model",
                extra={"context": {"model_size": model_size, "error": str(exc)}},
            )
            return None, exc

    def download_yamnet_model(self) -> Tuple[Optional[str], Optional[Exception]]:
        try:
            target_dir = self.get_model_path("yamnet")
            model_path = target_dir / "model.h5"

            if model_path.exists():
                logger.debug(
                    "YAMNet model already cached",
                    extra={"context": {"path": str(model_path)}},
                )
                return str(model_path), None

            import tensorflow_hub as hub  # type: ignore

            yamnet_model_url = getattr(self.config, "YAMNET_MODEL_URL", "https://tfhub.dev/google/yamnet/1")
            logger.info("Downloading YAMNet model", extra={"context": {"url": yamnet_model_url}})
            model = hub.load(yamnet_model_url)
            target_dir.mkdir(parents=True, exist_ok=True)
            model_path.write_text("YAMNet cache ready\n", encoding="utf-8")
            logger.info(
                "YAMNet model cached",
                extra={"context": {"path": str(model_path)}},
            )
            return str(model_path), None
        except Exception as exc:  # pylint: disable=broad-except
            logger.exception(
                "Failed to download YAMNet model",
                extra={"context": {"error": str(exc)}},
            )
            return None, exc

    def download_ollama_model(
        self, model_name: str = "llama3.2:1b", ollama_host: str = "http://localhost:11434"
    ) -> Tuple[bool, Optional[Exception]]:
        """Download and cache Ollama model for LLM inference."""
        try:
            import ollama  # type: ignore

            client = ollama.Client(host=ollama_host)

            # Check if model already exists
            try:
                models = client.list()
                model_names = [model.get("name", "") for model in models.get("models", [])]
                if any(model_name in name for name in model_names):
                    logger.debug(
                        "Ollama model already cached",
                        extra={"context": {"model": model_name, "host": ollama_host}},
                    )
                    return True, None
            except Exception as list_exc:  # pylint: disable=broad-except
                logger.warning(
                    "Failed to list Ollama models, attempting pull",
                    extra={"context": {"error": str(list_exc)}},
                )

            # Pull model if not cached
            logger.info(
                "Downloading Ollama model",
                extra={"context": {"model": model_name, "host": ollama_host}},
            )
            client.pull(model_name)
            logger.info(
                "Ollama model cached",
                extra={"context": {"model": model_name, "host": ollama_host}},
            )

            # Verify model loaded
            try:
                models = client.list()
                model_names = [model.get("name", "") for model in models.get("models", [])]
                if any(model_name in name for name in model_names):
                    return True, None
                else:
                    # Propagate error if model not found after pull
                    error_msg = f"Model {model_name} not found after pull"
                    logger.error(
                        "Ollama model not found after pull",
                        extra={"context": {"model": model_name, "available_models": model_names}},
                    )
                    return False, Exception(error_msg)
            except Exception as verify_exc:  # pylint: disable=broad-except
                logger.error(
                    "Could not verify Ollama model after pull",
                    extra={"context": {"error": str(verify_exc)}},
                )
                # Propagate error instead of returning success on uncertain state
                return False, verify_exc

        except ImportError as exc:
            logger.exception(
                "Ollama library not available",
                extra={"context": {"error": str(exc)}},
            )
            return False, exc
        except Exception as exc:  # pylint: disable=broad-except
            logger.exception(
                "Failed to download Ollama model",
                extra={"context": {"model": model_name, "host": ollama_host, "error": str(exc)}},
            )
            return False, exc

    def verify_all_models(self) -> Dict[str, bool]:
        checks = {
            "yolov8": self._verify_yolov8(),
            "mtcnn": self._verify_mtcnn(),
            "arcface": self._verify_arcface(),
            "osnet": self._verify_osnet(),
            "mivolo": self._verify_mivolo(),
            "blip2": self._verify_blip2(),
            "whisper": self._verify_whisper(),
            "yamnet": self._verify_yamnet(),
            "ollama": self._verify_ollama(),
        }

        missing = [name for name, available in checks.items() if not available]
        if missing:
            logger.warning("Missing models detected", extra={"context": {"models": missing}})
        else:
            logger.debug("All models verified")

        return checks

    def _verify_yolov8(self) -> bool:
        path, error = self.download_yolov8_model()
        if error is not None:
            return False
        return path is not None

    def _verify_mtcnn(self) -> bool:
        try:
            from facenet_pytorch import MTCNN  # type: ignore

            MTCNN(keep_all=False)
            return True
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("MTCNN verification failed", extra={"context": {"error": str(exc)}})
            return False

    def _verify_arcface(self) -> bool:
        try:
            from facenet_pytorch import InceptionResnetV1  # type: ignore

            InceptionResnetV1(pretrained="vggface2")
            return True
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("ArcFace verification failed", extra={"context": {"error": str(exc)}})
            return False

    def _verify_osnet(self) -> bool:
        try:
            from torchreid.utils import FeatureExtractor  # type: ignore

            FeatureExtractor(model_name="osnet_x1_0")
            return True
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("OSNet verification failed", extra={"context": {"error": str(exc)}})
            return False

    def _verify_mivolo(self) -> bool:
        cache_dir = self.get_model_path("mivolo")
        try:
            _, error = self.download_mivolo_model()
            if error is None:
                from transformers import (  # type: ignore
                    AutoImageProcessor,
                    AutoModelForImageClassification,
                )

                AutoImageProcessor.from_pretrained("iitolstykh/mivolo_v2", cache_dir=str(cache_dir))
                AutoModelForImageClassification.from_pretrained(
                    "iitolstykh/mivolo_v2",
                    cache_dir=str(cache_dir),
                )
                return True
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("MiVOLO verification via transformers failed", extra={"context": {"error": str(exc)}})

        try:
            from deepface import DeepFace  # type: ignore

            DeepFace.build_model("Age")  # type: ignore[attr-defined]
            DeepFace.build_model("Gender")  # type: ignore[attr-defined]
            DeepFace.build_model("Race")  # type: ignore[attr-defined]
            return True
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("Demographics fallback verification failed", extra={"context": {"error": str(exc)}})
            return False

    def _verify_blip2(self) -> bool:
        cache_dir = self.get_model_path("blip2")
        model_name = getattr(self.config, "BLIP2_MODEL_NAME", "Salesforce/blip2-opt-2.7b")
        sentinel_path = cache_dir / "model.pth"
        if self._blip2_cache_complete(cache_dir, sentinel_path):
            return True
        try:
            _, error = self.download_blip2_model(model_name=model_name)
            if error is None:
                return self._blip2_cache_complete(cache_dir, sentinel_path)
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning(
                "BLIP-2 verification failed",
                extra={"context": {"model": model_name, "error": str(exc)}},
            )
        return False

    def _verify_whisper(self) -> bool:
        try:
            import whisper  # type: ignore

            whisper.load_model("base")
            return True
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("Whisper verification failed", extra={"context": {"error": str(exc)}})
            return False

    def _verify_yamnet(self) -> bool:
        try:
            import tensorflow_hub as hub  # type: ignore

            yamnet_model_url = getattr(self.config, "YAMNET_MODEL_URL", "https://tfhub.dev/google/yamnet/1")
            hub.load(yamnet_model_url)
            return True
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("YAMNet verification failed", extra={"context": {"error": str(exc)}})
            return False

    def _verify_ollama(self, ollama_host: str = "http://localhost:11434") -> bool:
        """Verify Ollama service is running and accessible."""
        try:
            import ollama  # type: ignore

            client = ollama.Client(host=ollama_host)
            client.list()  # Test connection
            return True
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("Ollama verification failed", extra={"context": {"error": str(exc)}})
            return False

    @staticmethod
    def _blip2_cache_complete(cache_dir: Path, sentinel_path: Path) -> bool:
        if not sentinel_path.exists():
            return False

        expected_patterns = (
            "**/*.safetensors",
            "**/*.bin",
            "**/config.json",
        )
        for pattern in expected_patterns:
            if any(cache_dir.glob(pattern)):
                return True
        return False

    def _download_from_url(self, url: str, destination: Path) -> bool:
        try:
            logger.info("Downloading file", extra={"context": {"url": url, "destination": str(destination)}})
            with requests.get(url, stream=True, timeout=30) as response:
                response.raise_for_status()
                destination.parent.mkdir(parents=True, exist_ok=True)
                total = int(response.headers.get("content-length", 0))
                downloaded = 0
                with open(destination, "wb") as output_file:
                    for chunk in response.iter_content(chunk_size=8192):
                        if not chunk:
                            continue
                        output_file.write(chunk)
                        downloaded += len(chunk)
                        if total:
                            progress = round((downloaded / total) * 100, 2)
                            logger.debug(
                                "Download progress",
                                extra={"context": {"url": url, "progress": progress}},
                            )
            logger.info("Download completed", extra={"context": {"destination": str(destination)}})
            return True
        except Exception as exc:  # pylint: disable=broad-except
            logger.exception(
                "Failed to download file",
                extra={"context": {"url": url, "destination": str(destination), "error": str(exc)}},
            )
            return False

