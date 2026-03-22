import { useRef, useState, useCallback, useEffect } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useAuthContext } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import { attendanceApi, faceApi, subjectsApi, teachersApi } from '../services/api';
import { Camera, CheckCircle, XCircle, UserCheck, ChevronDown } from 'lucide-react';

const CAPTURE_INTERVAL_MS = 500;
const FRAME_BATCH_SIZE = 3; /* 3-frame stability: send every 3 frames */
/* Once marked for a subject, ignore same face for that subject for rest of session */
const FACE_NOT_REGISTERED_DEBOUNCE_MS = 12000; /* Don't spam "not registered" toast */
const PREVIEW_PERSIST_MS = 1500;
const VERIFIED_OVERLAY_MS = 3000; /* Clear "Face verified" overlay after 3 sec */
const MAX_FRAME_SIZE = 640; /* Resize before send for faster inference */

export function FaceCapturePage() {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [stream, setStream] = useState<MediaStream | null>(null);
  const [status, setStatus] = useState<'idle' | 'scanning' | 'recognized' | 'error'>('idle');
  const [message, setMessage] = useState('');
  const [subjectId, setSubjectId] = useState('');
  const [subjectDropdownOpen, setSubjectDropdownOpen] = useState(false);
  const markedThisSessionRef = useRef<Set<string>>(new Set()); /* "student_id:subject_id" */
  const frameBufferRef = useRef<File[]>([]);
  const [lastRecognized, setLastRecognized] = useState<{ names: string[]; time: number; alreadyMarked?: boolean } | null>(null);
  const [livePreview, setLivePreview] = useState<{ names: string[]; confidence: number; ts: number } | null>(null);
  const [attendanceLog, setAttendanceLog] = useState<{ names: string[]; time: string }[]>([]);
  const captureIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const subjectDropdownRef = useRef<HTMLDivElement>(null);
  const inFlightRef = useRef(false);
  const previewPersistRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const verifiedClearRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const lastNotRegisteredToastRef = useRef<number>(0);
  useAuthContext();
  const queryClient = useQueryClient();
  const toast = useToast();

  useEffect(() => {
    teachersApi.ensure().catch(() => {});
  }, []);

  useEffect(() => {
    return () => {
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((t) => t.stop());
        streamRef.current = null;
      }
      if (captureIntervalRef.current) {
        clearInterval(captureIntervalRef.current);
        captureIntervalRef.current = null;
      }
      if (previewPersistRef.current) clearTimeout(previewPersistRef.current);
      if (verifiedClearRef.current) clearTimeout(verifiedClearRef.current);
    };
  }, []);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (subjectDropdownRef.current && !subjectDropdownRef.current.contains(e.target as Node)) {
        setSubjectDropdownOpen(false);
      }
    };
    if (subjectDropdownOpen) document.addEventListener('click', handleClickOutside);
    return () => document.removeEventListener('click', handleClickOutside);
  }, [subjectDropdownOpen]);

  const { data: subjects = [] } = useQuery({
    queryKey: ['subjects'],
    queryFn: () => subjectsApi.list().then((r) => r.data || []),
    staleTime: 60_000,
  });

  const startCamera = useCallback(async () => {
    try {
      const s = await navigator.mediaDevices.getUserMedia({ video: { width: 640, height: 480 } });
      streamRef.current = s;
      setStream(s);
      if (videoRef.current) videoRef.current.srcObject = s;
    } catch {
      setStatus('error');
      setMessage('Camera access denied');
    }
  }, []);

  const stopCamera = useCallback(() => {
    if (captureIntervalRef.current) {
      clearInterval(captureIntervalRef.current);
      captureIntervalRef.current = null;
    }
    if (previewPersistRef.current) {
      clearTimeout(previewPersistRef.current);
      previewPersistRef.current = null;
    }
    if (verifiedClearRef.current) {
      clearTimeout(verifiedClearRef.current);
      verifiedClearRef.current = null;
    }
    const s = streamRef.current;
    if (s) {
      s.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
    setStream(null);
    setStatus('idle');
    setLivePreview(null);
    setLastRecognized(null);
    markedThisSessionRef.current.clear();
    lastNotRegisteredToastRef.current = 0;
  }, []);

  const captureAndVerify = useCallback(async () => {
    if (!videoRef.current || !canvasRef.current || !subjectId || inFlightRef.current) return;
    const vw = videoRef.current.videoWidth;
    const vh = videoRef.current.videoHeight;
    if (!vw || !vh) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    canvas.width = vw;
    canvas.height = vh;
    ctx.drawImage(videoRef.current, 0, 0);

    let outW = vw;
    let outH = vh;
    if (Math.max(vw, vh) > MAX_FRAME_SIZE) {
      const scale = MAX_FRAME_SIZE / Math.max(vw, vh);
      outW = Math.round(vw * scale);
      outH = Math.round(vh * scale);
    }
    const resizeCanvas = document.createElement('canvas');
    resizeCanvas.width = outW;
    resizeCanvas.height = outH;
    const rctx = resizeCanvas.getContext('2d');
    if (!rctx) return;
    rctx.drawImage(canvas, 0, 0, outW, outH);

    const blob = await new Promise<Blob | null>((resolve) => {
      resizeCanvas.toBlob(resolve, 'image/jpeg', 0.82);
    });
    if (!blob) return;

    const file = new File([blob], 'frame.jpg', { type: 'image/jpeg' });
    frameBufferRef.current.push(file);
    if (frameBufferRef.current.length < FRAME_BATCH_SIZE) return;

    const frames = frameBufferRef.current.splice(0, FRAME_BATCH_SIZE);
    inFlightRef.current = true;
    if (previewPersistRef.current) {
      clearTimeout(previewPersistRef.current);
      previewPersistRef.current = null;
    }
    if (verifiedClearRef.current) {
      clearTimeout(verifiedClearRef.current);
      verifiedClearRef.current = null;
    }
    try {
      const res = await faceApi.verifyMultiStable(frames);
      const data = res.data;
      const matches = data?.matches || [];
      if (matches.length > 0) {
        const now = Date.now();
        const markedKey = (sid: string) => `${sid}:${subjectId}`;
        const toProcess = matches.filter((m: { student_id: string }) => !markedThisSessionRef.current.has(markedKey(m.student_id)));
        const allNames: string[] = [];
        let maxConf = 0;
        for (const m of toProcess) {
          const name = m.student?.name || m.student_id;
          allNames.push(name);
          maxConf = Math.max(maxConf, m.confidence || 0);
        }
        if (toProcess.length > 0) {
          setLivePreview({ names: allNames, confidence: maxConf, ts: now });
        } else if (matches.length > 0) {
          setLivePreview(null); /* All detected already marked for this subject - don't show overlay */
        }
        const markedNames: string[] = [];
        const alreadyMarkedNames: string[] = [];
        for (const m of toProcess) {
          const name = m.student?.name || m.student_id;
          const key = markedKey(m.student_id);
          try {
            const checkInRes = await attendanceApi.checkIn(m.student_id, subjectId, m.confidence);
            const checkInData = (checkInRes as { data?: { status?: string; student_name?: string } })?.data;
            markedThisSessionRef.current.add(key);
            if (checkInData?.status === 'already_marked') {
              alreadyMarkedNames.push(name);
              toast.attendanceAlreadyMarked(checkInData.student_name || name);
              continue;
            }
            markedNames.push(name);
            toast.attendanceSuccess(checkInData?.student_name || name);
            // Invalidate dashboard queries to update stats
            queryClient.invalidateQueries({ queryKey: ['dashboard-stats'] });
            queryClient.invalidateQueries({ queryKey: ['attendance-analytics'] });
          } catch (err: unknown) {
            const errRes = (err as { response?: { status?: number; data?: { status?: string; message?: string } } })?.response;
            if (errRes?.status === 409 || errRes?.data?.status === 'already_marked') {
              markedThisSessionRef.current.add(key);
              alreadyMarkedNames.push(name);
              toast.attendanceAlreadyMarked(name);
              continue;
            }
            toast.attendanceError((errRes?.data?.message as string) || 'Failed to mark attendance');
          }
        }
        if (markedNames.length > 0) {
          setLastRecognized({ names: markedNames, time: now, alreadyMarked: false });
          setStatus('recognized');
          setMessage(`Attendance marked: ${markedNames.join(', ')}`);
          setAttendanceLog((prev) => [
            { names: markedNames, time: new Date().toLocaleTimeString() },
            ...prev.slice(0, 9),
          ]);
          queryClient.invalidateQueries({ queryKey: ['attendance'] });
          if (verifiedClearRef.current) clearTimeout(verifiedClearRef.current);
          verifiedClearRef.current = setTimeout(() => {
            verifiedClearRef.current = null;
            setLastRecognized(null);
            setStatus('scanning');
          }, VERIFIED_OVERLAY_MS);
        } else if (alreadyMarkedNames.length > 0) {
          setLastRecognized({ names: alreadyMarkedNames, time: now, alreadyMarked: true });
          setStatus('recognized');
          setMessage(`Attendance already marked: ${alreadyMarkedNames.join(', ')}`);
          if (verifiedClearRef.current) clearTimeout(verifiedClearRef.current);
          verifiedClearRef.current = setTimeout(() => {
            verifiedClearRef.current = null;
            setLastRecognized(null);
            setStatus('scanning');
          }, VERIFIED_OVERLAY_MS);
        }
      } else {
        previewPersistRef.current = setTimeout(() => setLivePreview(null), PREVIEW_PERSIST_MS);
        const facesDetected = (data as { faces_detected?: number })?.faces_detected ?? 0;
        const msg = (data as { message?: string })?.message ?? '';
        const noFaceInFrame = msg.toLowerCase().includes('no faces detected');
        const isFaceNotRegistered =
          !noFaceInFrame && (facesDetected > 0 || msg.includes('No face embeddings'));
        if (isFaceNotRegistered) {
          const now = Date.now();
          if (now - lastNotRegisteredToastRef.current > FACE_NOT_REGISTERED_DEBOUNCE_MS) {
            lastNotRegisteredToastRef.current = now;
            if (msg.includes('No face embeddings')) {
              toast.faceNotRegistered('No students registered yet. Add students with face photos first.');
            } else {
              toast.faceNotRegistered('This face is not registered in our database.');
            }
          }
        }
      }
    } catch {
      previewPersistRef.current = setTimeout(() => setLivePreview(null), PREVIEW_PERSIST_MS);
      toast.attendanceError('Face recognition failed');
    } finally {
      inFlightRef.current = false;
    }
  }, [subjectId, queryClient, toast]);

  useEffect(() => {
    if (stream && subjectId) {
      const t = setTimeout(() => setStatus('scanning'), 0);
      captureIntervalRef.current = setInterval(captureAndVerify, CAPTURE_INTERVAL_MS);
      const id = captureIntervalRef.current;
      return () => {
        clearTimeout(t);
        clearInterval(id);
      };
    }
    return undefined;
  }, [stream, subjectId, captureAndVerify]);

  return (
    <div className="w-full max-w-2xl mx-auto">
      <h1 className="text-2xl font-bold text-slate-800 mb-2">Automatic Face Attendance</h1>
      <p className="text-slate-500 text-sm mb-6">
        Up to 3 faces detected at once. Students stand in front of camera — attendance marked automatically for each recognized face.
      </p>
      <div className="bg-white rounded-xl border border-slate-200">
        <div className="aspect-video bg-slate-900 relative overflow-hidden rounded-t-xl">
          <video ref={videoRef} autoPlay playsInline muted className="w-full h-full object-cover" />
          <canvas ref={canvasRef} className="hidden" />
          {!stream && (
            <div className="absolute inset-0 flex items-center justify-center text-slate-400">
              <Camera className="w-16 h-16" />
            </div>
          )}
          {stream && !subjectId && (
            <div className="absolute top-2 left-2 px-2 py-1 bg-amber-500/90 text-white text-xs rounded">
              Select a subject below to start scanning
            </div>
          )}
          {stream && subjectId && status === 'scanning' && !lastRecognized && (
            <div className="absolute top-2 left-2 px-2 py-1 bg-green-500/80 text-white text-xs rounded flex items-center gap-1">
              <UserCheck className="w-3 h-3" />
              Scanning (up to 3 faces)...
            </div>
          )}
          {stream && (lastRecognized || livePreview) && (
            <div className="absolute top-2 right-2 max-w-[220px] px-3 py-2 bg-green-600/95 text-white rounded-lg shadow-lg border border-green-400/50">
              <div className="flex items-center gap-1.5">
                <CheckCircle className="w-4 h-4 flex-shrink-0 text-green-200" />
                <span className="font-semibold text-sm">Face verified</span>
              </div>
              <p className="text-sm font-bold mt-0.5 truncate">
                {(lastRecognized?.names || livePreview?.names || []).join(', ')}
              </p>
              <p className="text-xs text-green-100 mt-0.5">
                {lastRecognized?.alreadyMarked
                  ? 'Already marked today'
                  : lastRecognized
                    ? 'Marked successfully'
                    : `${Math.round((livePreview?.confidence || 0) * 100)}% confidence`}
              </p>
            </div>
          )}
        </div>
        <div className="p-5 space-y-4 rounded-b-xl">
          <div className="space-y-1 relative z-10" ref={subjectDropdownRef}>
            <label className="block text-sm font-medium text-slate-700">Subject</label>
            <div className="relative">
              <button
                type="button"
                onClick={() => setSubjectDropdownOpen((o) => !o)}
                className="w-full flex items-center justify-between px-4 py-2.5 pr-10 border border-slate-300 rounded-lg text-slate-900 bg-white text-left focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
              >
                <span>{(subjects as { id: string; name: string }[]).find((s) => s.id === subjectId)?.name || 'Select Subject'}</span>
                <ChevronDown className={`absolute right-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-500 pointer-events-none transition-transform ${subjectDropdownOpen ? 'rotate-180' : ''}`} strokeWidth={2} />
              </button>
              {subjectDropdownOpen && (
                <div className="absolute top-full left-0 right-0 mt-1 py-1 bg-white border border-slate-200 rounded-lg shadow-lg z-20 max-h-48 overflow-y-auto">
                  <button
                    type="button"
                    onClick={() => { setSubjectId(''); setSubjectDropdownOpen(false); }}
                    className="w-full px-4 py-2 text-left text-sm hover:bg-slate-50"
                  >
                    Select Subject
                  </button>
                  {(subjects as { id: string; name: string }[]).map((s) => (
                    <button
                      key={s.id}
                      type="button"
                      onClick={() => { setSubjectId(s.id); setSubjectDropdownOpen(false); }}
                      className={`w-full px-4 py-2 text-left text-sm hover:bg-slate-50 ${subjectId === s.id ? 'bg-primary-50 text-primary-700' : ''}`}
                    >
                      {s.name}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>
          <div className="flex items-center gap-3">
            {!stream ? (
              <button
                onClick={startCamera}
                className="flex-1 flex items-center justify-center py-1.5 px-4 text-sm font-medium bg-primary-600 text-white rounded-lg hover:bg-primary-700"
              >
                Start Camera
              </button>
            ) : (
              <button
                onClick={stopCamera}
                className="flex-1 flex items-center justify-center py-1.5 px-4 text-sm font-medium border border-slate-300 rounded-lg hover:bg-slate-50"
              >
                Stop Camera
              </button>
            )}
          </div>
          {lastRecognized && (
            <div className="space-y-2">
              <div className="flex items-center gap-2 text-green-600 bg-green-50 p-3 rounded-lg">
                <CheckCircle className="w-5 h-5 flex-shrink-0" />
                <span>
                  {lastRecognized.alreadyMarked
                    ? 'Attendance already marked for today'
                    : 'Attendance marked'}
                  {' '}({lastRecognized.names.length}): <strong>{lastRecognized.names.join(', ')}</strong>
                </span>
              </div>
              <p className="text-xs text-slate-500">
                {lastRecognized.alreadyMarked
                  ? 'You were already checked in earlier today.'
                  : 'Up to 3 faces detected per frame. All matches logged in attendance.'}
              </p>
            </div>
          )}
          {attendanceLog.length > 0 && (
            <div className="border border-slate-200 rounded-lg p-3">
              <h3 className="text-sm font-medium text-slate-700 mb-2">Session Log</h3>
              <div className="space-y-1 max-h-32 overflow-y-auto">
                {attendanceLog.map((entry, i) => (
                  <div key={i} className="text-sm text-slate-600 flex justify-between">
                    <span>{entry.names.join(', ')}</span>
                    <span className="text-slate-400">{entry.time}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
          {status === 'error' && (
            <div className="flex items-center gap-2 text-destructive-600">
              <XCircle className="w-5 h-5" />
              {message}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

