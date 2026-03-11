"""Face recognition service - orchestrates ML module for face operations."""

import time
from typing import Any

import numpy as np

from app.core.exceptions import DuplicateFaceError, FaceRecognitionError, NotFoundError
from app.repositories.face_embedding_repository import FaceEmbeddingRepository
from app.repositories.student_repository import StudentRepository

# Single shared engine to stay under 512MB (avoid 3x model load)
_face_engine = None

# Embedding cache: [(student_id, embedding), ...] for fast batch matching
_embedding_cache: list[tuple[str, list[float]]] = []
_embedding_cache_ts: float = 0


def _get_face_engine():
    """Single shared engine - keeps memory under 512MB (one model load instead of three)."""
    global _face_engine
    if _face_engine is None:
        from app.core.config import get_settings
        from ml.recognition import FaceRecognitionEngine
        settings = get_settings()
        # 960 det_size for better accuracy; permissive enrollment thresholds for live environment
        det_size_val = getattr(settings, "DET_SIZE", 960)
        det_thresh = getattr(settings, "REALTIME_DET_THRESH", 0.35)
        _face_engine = FaceRecognitionEngine(
            threshold=settings.FACE_RECOGNITION_THRESHOLD,
            max_faces=settings.MAX_FACES_DETECT,
            min_detection_score=getattr(settings, "ENROLLMENT_DETECTION_SCORE_MIN", 0.40),
            min_blur_variance=getattr(settings, "ENROLLMENT_MIN_BLUR_VARIANCE", 50.0),
            min_face_pixels=getattr(settings, "ENROLLMENT_MIN_FACE_PIXELS", 60 * 60),
            realtime=False,
            det_size=(det_size_val, det_size_val),
            det_thresh=det_thresh,
        )
    return _face_engine


async def _ensure_embedding_cache() -> list[tuple[str, list[float]]]:
    """Load or refresh embedding cache. Returns cache for batch matching."""
    global _embedding_cache, _embedding_cache_ts
    from app.core.config import get_settings
    settings = get_settings()
    refresh_sec = getattr(settings, "EMBEDDING_CACHE_REFRESH_SEC", 300)
    now = time.monotonic()
    if not _embedding_cache or (now - _embedding_cache_ts) > refresh_sec:
        data = await FaceEmbeddingRepository.get_all_embeddings()
        _embedding_cache = [(str(r["student_id"]), r["embedding_vector"]) for r in (data or [])]
        _embedding_cache_ts = now
    return _embedding_cache


async def refresh_embedding_cache() -> None:
    """Refresh embedding cache (call at startup or periodically)."""
    global _embedding_cache, _embedding_cache_ts
    data = await FaceEmbeddingRepository.get_all_embeddings()
    _embedding_cache = [(str(r["student_id"]), r["embedding_vector"]) for r in (data or [])]
    _embedding_cache_ts = time.monotonic()


def preload_engines() -> None:
    """Load single shared ML engine (saves ~2/3 memory vs 3 engines)."""
    _get_face_engine()


class FaceRecognitionService:
    """Service for face recognition operations."""

    @staticmethod
    def get_engine():
        """Return the shared face recognition engine."""
        return _get_face_engine()

    @staticmethod
    def extract_embedding_from_image(image_bytes: bytes):
        """Extract face embedding from image. Returns None if no face detected."""
        engine = _get_face_engine()
        return engine.extract_embedding(image_bytes)

    @staticmethod
    def extract_embedding_for_enrollment(image_bytes: bytes):
        """
        Strict extraction for new student registration.
        Returns None if: no face, multiple faces, invalid image, or face fails quality checks.
        Student must NOT be added to DB unless this returns a valid embedding.
        """
        if not image_bytes or len(image_bytes) < 500:
            return None
        try:
            engine = _get_face_engine()
            return engine.extract_embedding_strict_single(
                image_bytes, require_exactly_one=True, enrollment_fallback=True
            )
        except ValueError:
            return None

    @staticmethod
    async def register_face(student_id: str, image_bytes: bytes) -> dict[str, Any]:
        """Extract embedding from image and store for student. Block if face matches another student."""
        student = await StudentRepository.get_by_id(student_id)
        if not student:
            raise NotFoundError("Student not found")

        engine = _get_face_engine()
        embedding = engine.extract_embedding(image_bytes)
        if embedding is None:
            raise FaceRecognitionError("No face detected in image")

        # Duplicate check: reject if this face matches a different student
        from app.core.config import get_settings
        stored = await FaceEmbeddingRepository.get_all_embeddings()
        if stored:
            stored_list = [(str(r["student_id"]), r["embedding_vector"]) for r in stored]
            duplicate = engine.find_duplicate_face(
                embedding,
                stored_list,
                threshold=get_settings().ENROLLMENT_DUPLICATE_THRESHOLD,
            )
            if duplicate:
                matched_student_id, similarity = duplicate
                if str(matched_student_id) != str(student_id):
                    raise DuplicateFaceError(
                        "This face is already registered under another student.",
                        similarity=similarity,
                    )

        await FaceEmbeddingRepository.create(student_id, embedding.tolist())
        await refresh_embedding_cache()  # Keep real-time cache fresh
        return {"success": True, "message": "Face registered successfully"}

    @staticmethod
    async def verify_face(
        image_bytes: bytes,
        subject_id: str | None = None,
    ) -> dict[str, Any]:
        """Verify face against stored embeddings and return match."""
        engine = _get_face_engine()
        embeddings_data = await FaceEmbeddingRepository.get_all_embeddings()
        if not embeddings_data:
            raise FaceRecognitionError("No face embeddings in database")

        # Build embedding map: student_id -> list of embeddings
        student_embeddings: dict[str, list] = {}
        for row in embeddings_data:
            sid = row["student_id"]
            if sid not in student_embeddings:
                student_embeddings[sid] = []
            student_embeddings[sid].append(row["embedding_vector"])

        probe_embedding = engine.extract_embedding(image_bytes)
        if probe_embedding is None:
            raise FaceRecognitionError("No face detected in image")

        best_match = engine.match_face(probe_embedding, student_embeddings)
        if not best_match:
            return {"matched": False, "message": "No matching face found"}

        student_id, confidence = best_match
        student = await StudentRepository.get_by_id(student_id)
        return {
            "matched": True,
            "student_id": student_id,
            "confidence": float(confidence),
            "student": student,
        }

    @staticmethod
    async def verify_faces_multi(
        image_bytes: bytes,
        subject_id: str | None = None,
    ) -> dict[str, Any]:
        """Detect up to 3 faces, match each using cached embeddings and batch comparison."""
        engine = _get_face_engine()
        cache = await _ensure_embedding_cache()
        if not cache:
            return {"matches": [], "message": "No face embeddings in database"}

        face_embeddings = engine.extract_embeddings_multi(image_bytes)
        if not face_embeddings:
            return {"matches": [], "message": "No faces detected"}

        matches = []
        seen_students: set[str] = set()
        for embedding, _bbox in face_embeddings:
            best_match = engine.match_face_batch(embedding, cache)
            if best_match:
                student_id, confidence = best_match
                if student_id not in seen_students:
                    seen_students.add(student_id)
                    student = await StudentRepository.get_by_id(student_id)
                    if student:
                        matches.append({
                            "student_id": student_id,
                            "confidence": float(confidence),
                            "student": student,
                        })

        return {"matches": matches, "faces_detected": len(face_embeddings)}

    @staticmethod
    async def verify_faces_multi_stable(
        image_bytes_list: list[bytes],
        subject_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Verify using 3 frames: extract embeddings from each, average, then match.
        Reduces false positives via 3-frame stability.
        """
        engine = _get_face_engine()
        cache = await _ensure_embedding_cache()
        if not cache:
            return {"matches": [], "faces_detected": 0, "message": "No face embeddings in database"}

        embeddings_per_frame: list[list[tuple[np.ndarray, list[int]]]] = []
        for img_bytes in image_bytes_list[:3]:  # max 3 frames
            if not img_bytes or len(img_bytes) < 100:
                continue
            embs = engine.extract_embeddings_multi(img_bytes)
            if embs:
                embeddings_per_frame.append(embs)

        if not embeddings_per_frame:
            return {"matches": [], "faces_detected": 0, "message": "No faces detected in frames"}

        # Use first frame's face count; average embeddings for corresponding faces
        first_embs = embeddings_per_frame[0]
        matches = []
        seen_students: set[str] = set()

        for idx, (emb0, bbox0) in enumerate(first_embs):
            emb_list = [emb0]
            for frame_embs in embeddings_per_frame[1:]:
                if idx < len(frame_embs):
                    emb_list.append(frame_embs[idx][0])
            avg_emb = np.mean(emb_list, axis=0).astype(np.float32)
            norm = np.linalg.norm(avg_emb)
            if norm > 1e-9:
                avg_emb = avg_emb / norm
            best_match = engine.match_face_batch(avg_emb, cache)
            if best_match:
                student_id, confidence = best_match
                if student_id not in seen_students:
                    seen_students.add(student_id)
                    student = await StudentRepository.get_by_id(student_id)
                    if student:
                        matches.append({
                            "student_id": student_id,
                            "confidence": float(confidence),
                            "student": student,
                        })

        msg = None
        if not matches and len(first_embs) > 0:
            msg = "Face detected but not registered in our database"
        return {"matches": matches, "faces_detected": len(first_embs), "message": msg}

    @staticmethod
    async def verify_face_with_liveness(
        image_bytes: bytes,
        subject_id: str | None = None,
    ) -> dict[str, Any]:
        """Verify face with liveness check (requires multiple frames - simplified)."""
        engine = _get_face_engine()
        # For single image, we do basic verification
        # Full liveness requires video stream - API accepts single frame for now
        return await FaceRecognitionService.verify_face(image_bytes, subject_id)
