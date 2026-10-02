import json
from pathlib import Path
import cv2
import numpy as np

BASE_DIR = Path(__file__).resolve().parent
MODEL_DIR = BASE_DIR / "face_models"
DETECTOR_MODEL = MODEL_DIR / "face_detection_yunet_2026may.onnx"
RECOGNIZER_MODEL = MODEL_DIR / "face_recognition_sface_2021dec.onnx"

_detector = None
_recognizer = None

def models_ready():
    return DETECTOR_MODEL.exists() and RECOGNIZER_MODEL.exists()

def get_models():
    global _detector, _recognizer
    if _detector is None or _recognizer is None:
        if not models_ready():
            raise FileNotFoundError(
                "Face models are missing. Run: python download_models.py"
            )
        _detector = cv2.FaceDetectorYN.create(
            str(DETECTOR_MODEL), "", (320, 320), 0.75, 0.3, 5000
        )
        _recognizer = cv2.FaceRecognizerSF.create(
            str(RECOGNIZER_MODEL), ""
        )
    return _detector, _recognizer

def detect_faces(image):
    detector, _ = get_models()
    h, w = image.shape[:2]
    detector.setInputSize((w, h))
    _, faces = detector.detect(image)
    results = []
    if faces is None:
        return results

    for face in faces:
        x, y, bw, bh = [int(v) for v in face[:4]]
        score = float(face[14])
        landmarks = face[4:14].reshape(5, 2).tolist()
        results.append({
            "bbox": [x, y, bw, bh],
            "score": score,
            "landmarks": landmarks,
        })
    return results

def extract_feature_from_face(image, face):
    _, recognizer = get_models()
    aligned = recognizer.alignCrop(image, np.asarray(face, dtype=np.float32))
    feature = recognizer.feature(aligned)
    return feature.flatten().astype(float).tolist()

def extract_best_feature(image):
    faces = detect_faces(image)
    if not faces:
        return None, None
    face = max(faces, key=lambda f: f["bbox"][2] * f["bbox"][3])
    raw = np.zeros((1, 15), dtype=np.float32)
    raw[0, :4] = face["bbox"]
    raw[0, 4:14] = np.asarray(face["landmarks"]).reshape(-1)
    raw[0, 14] = face["score"]
    return extract_feature_from_face(image, raw[0]), face

def compare_features(a, b):
    _, recognizer = get_models()
    f1 = np.asarray(a, dtype=np.float32).reshape(1, -1)
    f2 = np.asarray(b, dtype=np.float32).reshape(1, -1)
    return float(recognizer.match(f1, f2, cv2.FaceRecognizerSF_FR_COSINE))

def feature_to_json(feature):
    return json.dumps(feature)

def feature_from_json(value):
    return json.loads(value)
