from pathlib import Path
from urllib.request import urlopen, Request

BASE = Path(__file__).resolve().parent
MODEL_DIR = BASE / "tracker" / "face_models"
MODEL_DIR.mkdir(parents=True, exist_ok=True)

MODELS = {
    "face_detection_yunet_2026may.onnx":
        "https://github.com/opencv/opencv_zoo/raw/refs/heads/main/models/face_detection_yunet/face_detection_yunet_2026may.onnx",
    "face_recognition_sface_2021dec.onnx":
        "https://huggingface.co/opencv/opencv_zoo/resolve/main/models/face_recognition_sface/face_recognition_sface_2021dec.onnx?download=true",
}

def download(name, url):
    target = MODEL_DIR / name
    if target.exists() and target.stat().st_size > 100_000:
        print(f"[OK] {name} already exists")
        return
    print(f"[DOWNLOAD] {name}")
    req = Request(url, headers={"User-Agent": "SmartPresence/1.0"})
    with urlopen(req, timeout=120) as response, open(target, "wb") as out:
        total = 0
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            out.write(chunk)
            total += len(chunk)
            print(f"\r  {total / 1024 / 1024:.1f} MB", end="")
    print("\n[OK] saved", target)

if __name__ == "__main__":
    for name, url in MODELS.items():
        download(name, url)
    print("All face models are ready.")
