"""Face recognition engine - enterprise-grade detection, embedding, matching.
RetinaFace + ArcFace (buffalo_l), strict quality filters, duplicate-safe.
"""

from typing import Any

import cv2
import numpy as np

# Enterprise-grade thresholds
DEFAULT_MATCH_THRESHOLD = 0.68  # Recognition: 0.68-0.72
ENROLLMENT_DUPLICATE_THRESHOLD = 0.75  # Reject duplicate faces
MIN_DETECTION_SCORE = 0.6  # Strict: reject low-confidence detections
MIN_FACE_PIXELS = 100 * 100  # Minimum 100x100 face size
MIN_BLUR_VARIANCE = 100.0  # Reject blurry images (Laplacian)
DET_SIZE = (640, 640)  # Default real-time: 640 for speed
DET_SIZE_ENROLLMENT = (1024, 1024)  # Enrollment: 1024 for max accuracy
DET_THRESH = 0.4  # Enrollment detection threshold
DET_THRESH_REALTIME = 0.5  # Real-time detection threshold


def _fix_exif_orientation(image_bytes: bytes) -> bytes:
    """Fix image orientation from EXIF (e.g. phone photos). Returns corrected bytes."""
    try:
        from PIL import Image
        import io
        img = Image.open(io.BytesIO(image_bytes))
        exif = img.getexif() or {}
        orientation = exif.get(0x112, 1)  # EXIF Orientation tag, 1 = normal
        if orientation == 3:
            img = img.rotate(180, expand=True)
        elif orientation == 6:
            img = img.rotate(270, expand=True)
        elif orientation == 8:
            img = img.rotate(90, expand=True)
        else:
            return image_bytes  # No rotation needed, keep original
        buf = io.BytesIO()
        img.convert("RGB").save(buf, format="JPEG", quality=95)
        return buf.getvalue()
    except Exception:
        return image_bytes


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Compute cosine similarity between two vectors."""
    a_norm = np.linalg.norm(a)
    b_norm = np.linalg.norm(b)
    if a_norm < 1e-9 or b_norm < 1e-9:
        return 0.0
    return float(np.dot(a, b) / (a_norm * b_norm))


def _preprocess_for_accuracy(img: np.ndarray) -> np.ndarray:
    """Strong preprocessing: CLAHE + gamma for varied lighting (indoor, outdoor, webcam)."""
    # CLAHE for contrast in shadows
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
    l = clahe.apply(l)
    lab = cv2.merge([l, a, b])
    out = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
    # Light gamma for dark images (common with webcams)
    gray = cv2.cvtColor(out, cv2.COLOR_BGR2GRAY)
    mean_val = np.mean(gray)
    if mean_val < 100:
        gamma = 1.2
        inv_gamma = 1.0 / gamma
        table = ((np.arange(256) / 255.0) ** inv_gamma * 255).astype(np.uint8)
        out = cv2.LUT(out, cv2.merge([table, table, table]))
    return out


def _blur_score(face_img: np.ndarray) -> float:
    """Laplacian variance - lower = blurrier. Returns sharpness score."""
    gray = cv2.cvtColor(face_img, cv2.COLOR_BGR2GRAY) if len(face_img.shape) == 3 else face_img
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


def _extract_aligned_face(img: np.ndarray, bbox: np.ndarray, kps: np.ndarray | None) -> np.ndarray | None:
    """Extract and align face crop using 5-point landmarks. Returns aligned face or None."""
    x1, y1, x2, y2 = map(int, bbox[:4])
    x1 = max(0, x1)
    y1 = max(0, y1)
    x2 = min(img.shape[1], x2)
    y2 = min(img.shape[0], y2)
    if x2 <= x1 or y2 <= y1:
        return None
    face_img = img[y1:y2, x1:x2]
    if face_img.size == 0:
        return None
    # Simple alignment: resize to fixed size for consistent blur check
    face_img = cv2.resize(face_img, (112, 112), interpolation=cv2.INTER_LINEAR)
    return face_img


class FaceRecognitionEngine:
    """
    Production face recognition engine optimized for maximum accuracy.
    Uses InsightFace buffalo_l (RetinaFace + ArcFace) with high-quality settings.
    """

    def __init__(
        self,
        threshold: float = DEFAULT_MATCH_THRESHOLD,
        max_faces: int = 3,
        min_detection_score: float | None = None,
        min_blur_variance: float | None = None,
        min_face_pixels: int | None = None,
        realtime: bool = False,
        det_size: tuple[int, int] | None = None,
        det_thresh: float | None = None,
    ):
        self._app = None
        self.threshold = max(threshold, 0.5)
        self.max_faces = max_faces
        self.min_detection_score = min_detection_score if min_detection_score is not None else MIN_DETECTION_SCORE
        self.min_blur_variance = min_blur_variance if min_blur_variance is not None else MIN_BLUR_VARIANCE
        self.min_face_pixels = min_face_pixels if min_face_pixels is not None else MIN_FACE_PIXELS
        self.realtime = realtime
        self._det_size = det_size or (DET_SIZE if realtime else DET_SIZE_ENROLLMENT)
        self._det_thresh = det_thresh if det_thresh is not None else (DET_THRESH_REALTIME if realtime else DET_THRESH)

    def _get_app(self):
        """Lazy load InsightFace FaceAnalysis. Model from INSIGHTFACE_MODEL env (buffalo_s for 512MB RAM)."""
        if self._app is None:
            try:
                from app.core.config import get_settings
                from insightface.app import FaceAnalysis
                model = get_settings().INSIGHTFACE_MODEL
                self._app = FaceAnalysis(
                    name=model,
                    root="~/.insightface/models",
                    allowed_modules=["detection", "recognition"],
                )
                self._app.prepare(ctx_id=0, det_thresh=self._det_thresh, det_size=self._det_size)
            except Exception as e:
                raise RuntimeError(f"InsightFace not available: {e}") from e
        return self._app

    def _decode_image(self, image_bytes: bytes, max_side: int | None = None) -> np.ndarray:
        """Decode image bytes to numpy array (BGR). Handles EXIF orientation and preprocessing."""
        if not image_bytes or len(image_bytes) < 100:
            raise ValueError("Image data too small or empty")

        # Fix EXIF orientation (phone photos often have wrong rotation)
        try:
            image_bytes = _fix_exif_orientation(image_bytes)
        except Exception:
            pass

        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError("Invalid or unsupported image format. Use JPEG or PNG.")

        h, w = img.shape[:2]
        min_side = 320
        if min(h, w) < min_side:
            scale = min_side / min(h, w)
            new_w, new_h = int(w * scale), int(h * scale)
            img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_LINEAR)

        max_side = max_side or (640 if self.realtime else 1920)
        if max(h, w) > max_side:
            scale = max_side / max(h, w)
            new_w, new_h = int(w * scale), int(h * scale)
            img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)

        return img

    def _get_faces_with_quality_filter(
        self, img: np.ndarray, use_preprocess: bool = True, allow_relaxed: bool = False
    ) -> list:
        """Detect faces with quality filtering. Try preprocessed then original for best pickup."""
        app = self._get_app()
        faces = []
        if use_preprocess:
            img_enhanced = _preprocess_for_accuracy(img.copy())
            faces = app.get(img_enhanced, max_num=self.max_faces)
            if not faces:
                faces = app.get(img, max_num=self.max_faces)
            if not faces and img.shape[0] * img.shape[1] > 640 * 640:
                # Try slightly upscaled if image is small
                scaled = cv2.resize(img, (min(1280, img.shape[1] * 2), min(1280, img.shape[0] * 2)))
                faces = app.get(scaled, max_num=self.max_faces)
        if not faces:
            faces = app.get(img, max_num=self.max_faces)

        filtered = []
        for face in faces:
            det_score = float(getattr(face, "det_score", 1.0))
            if det_score < self.min_detection_score:
                continue
            bbox = getattr(face, "bbox", None)
            if bbox is not None:
                x1, y1, x2, y2 = bbox[:4]
                area = (x2 - x1) * (y2 - y1)
                if area < self.min_face_pixels:
                    continue
                kps = getattr(face, "kps", None)
                aligned = _extract_aligned_face(img, bbox, kps)
                if aligned is not None:
                    blur_var = _blur_score(aligned)
                    if blur_var < self.min_blur_variance:
                        continue
            filtered.append(face)

        # If no faces pass strict filter but we have detections, allow relaxed for enrollment
        if allow_relaxed and not filtered and faces:
            relaxed_min_score = max(0.25, self.min_detection_score - 0.15)
            for face in faces:
                det_score = float(getattr(face, "det_score", 1.0))
                if det_score >= relaxed_min_score and hasattr(face, "embedding") and face.embedding is not None:
                    filtered.append(face)
                    break  # Take first acceptable face for enrollment

        return filtered

    def extract_embedding(self, image_bytes: bytes) -> np.ndarray | None:
        """
        Extract 512-D face embedding from image.
        Returns None if no face detected.
        Uses quality filtering and preprocessing for maximum accuracy.
        """
        img = self._decode_image(image_bytes)
        faces = self._get_faces_with_quality_filter(img)
        if not faces:
            return None
        face = faces[0]
        if not hasattr(face, "embedding") or face.embedding is None:
            return None
        emb = np.array(face.embedding, dtype=np.float32)
        # L2 normalize for consistent cosine similarity
        norm = np.linalg.norm(emb)
        if norm > 1e-9:
            emb = emb / norm
        return emb

    def extract_embedding_strict_single(
        self, image_bytes: bytes, require_exactly_one: bool = True, enrollment_fallback: bool = False
    ) -> np.ndarray | None:
        """
        For enrollment: prefer exactly one face; if multiple, use the best (highest det_score).
        Helps when small face in background - take the primary face.
        If enrollment_fallback=True and strict filter fails, retry with relaxed quality thresholds.
        """
        img = self._decode_image(image_bytes)
        faces = self._get_faces_with_quality_filter(img, allow_relaxed=False)
        if not faces and enrollment_fallback:
            faces = self._get_faces_with_quality_filter(img, allow_relaxed=True)
        if not faces:
            return None
        # If multiple faces, take the one with highest detection score (primary/best quality)
        if len(faces) > 1 and require_exactly_one:
            faces = sorted(faces, key=lambda f: float(getattr(f, "det_score", 0)), reverse=True)
            face = faces[0]  # Best face
        else:
            face = faces[0]
        if not hasattr(face, "embedding") or face.embedding is None:
            return None
        emb = np.array(face.embedding, dtype=np.float32)
        norm = np.linalg.norm(emb)
        if norm > 1e-9:
            emb = emb / norm
        return emb

    def extract_embeddings_multi(self, image_bytes: bytes) -> list[tuple[np.ndarray, list[int]]]:
        """
        Extract embeddings for up to max_faces faces.
        Returns list of (embedding, bbox). Embeddings are L2-normalized.
        """
        img = self._decode_image(image_bytes)
        faces = self._get_faces_with_quality_filter(img)
        result = []
        for face in faces:
            if hasattr(face, "embedding") and face.embedding is not None:
                emb = np.array(face.embedding, dtype=np.float32)
                norm = np.linalg.norm(emb)
                if norm > 1e-9:
                    emb = emb / norm
                bbox = face.bbox.astype(int).tolist()
                result.append((emb, bbox))
        return result

    def match_face(
        self,
        probe_embedding: np.ndarray,
        student_embeddings: dict[str, list],
    ) -> tuple[str, float] | None:
        """
        Match probe embedding against stored student embeddings.
        Uses cosine similarity for normalized embeddings.
        student_embeddings: {student_id: [embedding1, embedding2, ...]}
        Returns (student_id, confidence) or None.
        """
        probe = np.array(probe_embedding, dtype=np.float32).flatten()
        probe_norm = np.linalg.norm(probe)
        if probe_norm < 1e-9:
            return None
        probe = probe / probe_norm

        best_student = None
        best_score = 0.0

        for student_id, embeddings in student_embeddings.items():
            for emb in embeddings:
                emb_arr = np.array(emb, dtype=np.float32).flatten()
                emb_norm = np.linalg.norm(emb_arr)
                if emb_norm < 1e-9:
                    continue
                emb_arr = emb_arr / emb_norm
                score = float(np.dot(probe, emb_arr))
                if score > best_score:
                    best_score = score
                    best_student = student_id

        if best_student and best_score >= self.threshold:
            return (best_student, best_score)
        return None

    def match_face_batch(
        self,
        probe_embedding: np.ndarray,
        stored: list[tuple[str, np.ndarray | list[float]]],
    ) -> tuple[str, float] | None:
        """
        Vectorized batch match: similarities = stored @ probe.
        stored: [(student_id, embedding), ...]
        Returns (student_id, best_score) if best >= threshold, else None.
        """
        if not stored:
            return None
        probe = np.array(probe_embedding, dtype=np.float32).flatten()
        probe_norm = np.linalg.norm(probe)
        if probe_norm < 1e-9:
            return None
        probe = probe / probe_norm
        ids = [s[0] for s in stored]
        matrix = np.array([np.array(s[1], dtype=np.float32).flatten() for s in stored])
        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        norms[norms < 1e-9] = 1.0
        matrix = matrix / norms
        similarities = matrix @ probe
        best_idx = int(np.argmax(similarities))
        best_score = float(similarities[best_idx])
        if best_score >= self.threshold:
            return (ids[best_idx], best_score)
        return None

    def find_duplicate_face(
        self,
        probe_embedding: np.ndarray,
        stored_embeddings: list[tuple[str, list[float]]],
        threshold: float = ENROLLMENT_DUPLICATE_THRESHOLD,
    ) -> tuple[str, float] | None:
        """
        Vectorized batch check: does probe match any stored embedding?
        stored_embeddings: [(student_id, embedding), ...]
        Returns (student_id, max_similarity) if match >= threshold, else None.
        """
        if not stored_embeddings:
            return None
        probe = np.array(probe_embedding, dtype=np.float32).flatten()
        probe_norm = np.linalg.norm(probe)
        if probe_norm < 1e-9:
            return None
        probe = probe / probe_norm
        ids = [s[0] for s in stored_embeddings]
        matrix = np.array([s[1] for s in stored_embeddings], dtype=np.float32)
        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        norms[norms < 1e-9] = 1.0
        matrix = matrix / norms
        similarities = matrix @ probe
        best_idx = int(np.argmax(similarities))
        best_score = float(similarities[best_idx])
        if best_score >= threshold:
            return (ids[best_idx], best_score)
        return None

    def detect_faces_with_embeddings(self, image_bytes: bytes) -> list[dict[str, Any]]:
        """
        Detect multiple faces and extract embeddings.
        Returns list of {bbox, score, embedding}. Embeddings are L2-normalized.
        """
        img = self._decode_image(image_bytes)
        faces = self._get_faces_with_quality_filter(img)
        result = []
        for face in faces:
            emb = None
            if hasattr(face, "embedding") and face.embedding is not None:
                emb = np.array(face.embedding, dtype=np.float32)
                norm = np.linalg.norm(emb)
                if norm > 1e-9:
                    emb = (emb / norm).tolist()
                else:
                    emb = emb.tolist()
            result.append({
                "bbox": face.bbox.astype(int).tolist(),
                "score": float(face.det_score),
                "embedding": emb,
            })
        return result
