/** User-friendly message for timeout/network errors (no technical details) */
const FACE_ERROR_FRIENDLY = 'Face not detected or unclear. Please try again with a clearer, front-facing photo.';

/** Check if error is timeout, network, or gateway-related */
function isTechnicalError(err: unknown): boolean {
  const e = err as { code?: string; message?: string; response?: { status?: number } };
  const msg = (e?.message || '').toLowerCase();
  return (
    e?.response?.status === 502 ||
    e?.response?.status === 503 ||
    e?.code === 'ECONNABORTED' ||
    e?.code === 'ERR_NETWORK' ||
    msg.includes('timeout') ||
    msg.includes('network') ||
    msg.includes('exceeded')
  );
}

/** Check if error response indicates duplicate face (409) */
export function isDuplicateFaceError(err: unknown): boolean {
  const e = err as { response?: { status?: number; data?: { details?: { status?: string } } } };
  return (
    e?.response?.status === 409 &&
    e?.response?.data?.details?.status === 'duplicate_face'
  );
}

/** Extract a user-friendly error message from API error responses */
export function getApiErrorMessage(
  err: unknown,
  fallback = 'An error occurred',
  options?: { faceContext?: boolean }
): string {
  const e = err as { response?: { data?: { message?: string; detail?: string | { msg?: string }[]; details?: { status?: string } } }; message?: string };
  const d = e?.response?.data;

  if (isDuplicateFaceError(err)) {
    return d?.message || 'This face is already registered in the system.';
  }

  /* For face capture: never show technical timeout/network errors */
  if (options?.faceContext && isTechnicalError(err)) {
    return FACE_ERROR_FRIENDLY;
  }

  let msg = d?.message;
  if (!msg && typeof d?.detail === 'string') msg = d.detail;
  if (!msg && Array.isArray(d?.detail)) {
    msg = d.detail.map((x) => x?.msg).filter(Boolean).join(', ');
  }
  if (msg) return msg;

  /* 502/503: backend down, sleeping, or overloaded */
  if ((err as { response?: { status?: number } })?.response?.status === 502) {
    return 'Backend is starting or overloaded. Wait 30–60 seconds and try again.';
  }
  if ((err as { response?: { status?: number } })?.response?.status === 503) {
    return 'Service temporarily unavailable. Please try again in a moment.';
  }
  /* Network error: backend unreachable */
  if (isTechnicalError(err)) {
    return options?.faceContext ? FACE_ERROR_FRIENDLY : 'Unable to connect to server. Please check your connection.';
  }

  return e?.message || fallback;
}
