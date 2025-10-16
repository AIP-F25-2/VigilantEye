from typing import Any, Dict

class BaseModel:
    def analyze(self, image_path: str | None = None, audio_path: str | None = None) -> Dict[str, Any]:
        """Analyze artifact(s) and return a serializable dict."""
        raise NotImplementedError
