"""Third comparison provider placeholder. Selection is intentionally deferred."""

from .base import ProviderUnavailableError


class Model3Engine:
    name = "model3"
    model = "unselected"

    def transcribe(self, audio_path: str, *, language=None, task="transcribe"):
        raise ProviderUnavailableError(
            "Model 3 has not been selected or configured. Benchmarking will record this provider as unavailable."
        )
