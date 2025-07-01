"""Download ONNX model for embeddings."""

import requests
from pathlib import Path


def download_model():
    """Download the all-MiniLM-L6-v2 ONNX model."""
    model_dir = Path("models/onnx")
    model_path = model_dir / "all-MiniLM-L6-v2.onnx"

    if model_path.exists():
        print(f"✓ Model already exists at {model_path}")
        return

    # Create directory if it doesn't exist
    model_dir.mkdir(parents=True, exist_ok=True)

    # Model URL (from Hugging Face)
    url = "https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2/resolve/main/onnx/model.onnx"

    print(f"Downloading model from {url}...")
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()

        total_size = int(response.headers.get("content-length", 0))
        downloaded = 0

        with open(model_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
                downloaded += len(chunk)
                if total_size > 0:
                    progress = (downloaded / total_size) * 100
                    print(f"\rProgress: {progress:.1f}%", end="", flush=True)

        print(f"\n✓ Model downloaded successfully to {model_path}")

    except Exception as e:
        print(f"\n✗ Error downloading model: {e}")
        print("\nAlternative: Download manually from:")
        print(
            "https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2/tree/main/onnx"
        )
        print(f"And save as: {model_path}")


if __name__ == "__main__":
    download_model()
