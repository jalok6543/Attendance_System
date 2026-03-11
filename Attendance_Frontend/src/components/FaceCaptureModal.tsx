import { useRef, useState, useCallback, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { faceApi, studentsApi } from '../services/api';
import { getApiErrorMessage, isDuplicateFaceError } from '../utils/apiError';
import { useToast } from '../context/ToastContext';
import { Camera, CheckCircle, XCircle, Upload } from 'lucide-react';

export type StudentFormData = {
  name: string;
  email: string;
  roll_number: string;
  parent_phone: string;
  class: 'A' | 'B';
};

interface FaceCaptureModalProps {
  studentId?: string;
  studentName: string;
  formData?: StudentFormData;  /* Required for new student: creates student + face in one step. Omit for existing student. */
  onSuccess: () => void;
  onCancel: () => void;
}

export function FaceCaptureModal({ studentId, studentName, formData, onSuccess, onCancel }: FaceCaptureModalProps) {
  const toast = useToast();
  const isRegistrationMode = !!formData && !studentId;
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [stream, setStream] = useState<MediaStream | null>(null);
  const [videoReady, setVideoReady] = useState(false);
  const [status, setStatus] = useState<'idle' | 'capturing' | 'success' | 'error'>('idle');
  const [message, setMessage] = useState('');
  const [cameraError, setCameraError] = useState(false);

  const streamRef = useRef<MediaStream | null>(null);

  const registerFace = useCallback(async (file: File) => {
    setStatus('capturing');
    setMessage('');
    try {
      if (isRegistrationMode && formData) {
        const fd = new FormData();
        fd.append('name', formData.name);
        fd.append('email', formData.email);
        fd.append('roll_number', formData.roll_number);
        fd.append('parent_phone', formData.parent_phone);
        fd.append('class', formData.class);
        fd.append('image', file);
        await studentsApi.registerWithFace(fd);
      } else if (studentId) {
        await faceApi.register(studentId, file);
      }
      setStatus('success');
      setMessage('Face registered successfully!');
      toast.success('Face registered successfully');
    } catch (e) {
      setStatus('error');
      const msg = getApiErrorMessage(e, 'Face not detected or unclear. Please try again.', { faceContext: true });
      setMessage(msg);
      if (isDuplicateFaceError(e)) {
        toast.duplicateFace('This face is already registered in the system.');
      } else {
        toast.error(msg);
      }
    }
  }, [studentId, isRegistrationMode, formData, toast]);

  useEffect(() => {
    let cancelled = false;
    let stream: MediaStream | null = null;

    const stopCamera = (s: MediaStream | null) => {
      if (s) {
        s.getTracks().forEach((t) => t.stop());
      }
      streamRef.current = null;
      if (videoRef.current) {
        videoRef.current.srcObject = null;
      }
    };

    if (!navigator.mediaDevices?.getUserMedia) {
      setCameraError(true);
      const msg = 'Camera not supported. Use Upload Photo instead.';
      setMessage(msg);
      toast.error(msg);
      return;
    }
    navigator.mediaDevices.getUserMedia({ video: { width: { ideal: 1280 }, height: { ideal: 720 } }, audio: false })
      .then((s) => {
        stream = s;
        if (cancelled) {
          stopCamera(s);
          return;
        }
        streamRef.current = s;
        setStream(s);
        setVideoReady(false);
        if (videoRef.current) {
          videoRef.current.srcObject = s;
        }
      })
      .catch((err) => {
        if (cancelled) return;
        setCameraError(true);
        const msg = err?.name === 'NotAllowedError'
          ? 'Camera permission denied. Allow camera access or use Upload Photo.'
          : err?.name === 'NotFoundError'
            ? 'No camera found. Use Upload Photo instead.'
            : 'Camera unavailable. Use Upload Photo instead.';
        setMessage(msg);
        toast.error(msg);
      });

    return () => {
      cancelled = true;
      stopCamera(streamRef.current ?? stream);
    };
  }, [toast]);

  const captureAndRegister = useCallback(async () => {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas) return;
    if (video.videoWidth === 0 || video.readyState < 2) {
      const msg = 'Camera not ready. Wait for the video to load, then try again.';
      setStatus('error');
      setMessage(msg);
      toast.error(msg);
      return;
    }
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    // Capture at full resolution for better face detection
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    ctx.drawImage(video, 0, 0);
    canvas.toBlob(async (blob) => {
      if (!blob) {
        setStatus('error');
        setMessage('Capture failed');
        toast.error('Capture failed');
        return;
      }
      const file = new File([blob], 'face.jpg', { type: 'image/jpeg' });
      await registerFace(file);
    }, 'image/jpeg', 0.92);
  }, [registerFace, toast]);

  const handleFileUpload = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file && /^image\/(jpeg|jpg|png|webp)$/i.test(file.type)) {
      registerFace(file);
    } else if (file) {
      setStatus('error');
      const msg = 'Please upload a valid image (JPEG, PNG, or WebP)';
      setMessage(msg);
      toast.error(msg);
    }
    e.target.value = '';
  }, [registerFace]);

  return createPortal(
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm overflow-y-auto">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-lg my-8">
        <div className="px-6 py-5 border-b border-slate-200">
          <h2 className="text-lg font-semibold text-slate-800">
            {isRegistrationMode ? `Register Face - ${studentName}` : `Register Face - ${studentName}`}
          </h2>
          <p className="text-sm text-slate-500 mt-1">
            {isRegistrationMode
              ? 'Face is required. Student will not be added until a valid face is detected.'
              : 'Upload a photo or capture from camera. Face is required for automatic attendance recognition.'}
          </p>
          <p className="text-xs text-slate-400 mt-2">
            <strong>Recommended:</strong> 640×480 to 1024×1024 px • Face should be at least 100×100 px • Clear, front-facing, good lighting
          </p>
        </div>
        <div className="px-6 py-5 space-y-4">
          <div className="aspect-video bg-slate-900 rounded-lg overflow-hidden relative">
            <video
              ref={videoRef}
              autoPlay
              playsInline
              muted
              className="w-full h-full object-cover"
              onLoadedData={() => {
                const v = videoRef.current;
                if (v && v.videoWidth > 0 && v.videoHeight > 0) setVideoReady(true);
              }}
              onCanPlay={() => {
                const v = videoRef.current;
                if (v && v.videoWidth > 0 && v.videoHeight > 0) setVideoReady(true);
              }}
            />
            <canvas ref={canvasRef} className="hidden" />
            {!stream && !cameraError && (
              <div className="absolute inset-0 flex flex-col items-center justify-center gap-2 text-slate-400">
                <Camera className="w-16 h-16" />
                <span className="text-sm">Starting camera…</span>
              </div>
            )}
            {stream && !videoReady && !cameraError && (
              <div className="absolute inset-0 flex flex-col items-center justify-center gap-2 text-slate-400">
                <Camera className="w-12 h-12 animate-pulse" />
                <span className="text-sm">Loading video…</span>
              </div>
            )}
            {cameraError && !stream && (
              <div className="absolute inset-0 flex flex-col items-center justify-center text-slate-600 text-center p-4 gap-2">
                <XCircle className="w-12 h-12 text-amber-500" />
                <span className="font-medium">Camera unavailable</span>
                <span className="text-sm">{message || 'Use Upload Photo instead.'}</span>
              </div>
            )}
          </div>
          <div className="flex gap-3">
            <input
              ref={fileInputRef}
              type="file"
              accept="image/jpeg,image/jpg,image/png,image/webp"
              onChange={handleFileUpload}
              className="hidden"
            />
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              disabled={status === 'capturing'}
              className="flex-1 flex items-center justify-center gap-2 py-1.5 px-3 text-sm font-medium border border-slate-300 rounded-lg hover:bg-slate-50 disabled:opacity-50"
            >
              <Upload className="w-4 h-4" />
              Upload Photo
            </button>
            <button
              type="button"
              onClick={captureAndRegister}
              disabled={status === 'capturing' || !stream || !videoReady}
              title={
                !stream
                  ? 'Waiting for camera...'
                  : !videoReady
                    ? 'Waiting for video to load...'
                    : 'Take a photo from your camera'
              }
              className="flex-1 flex items-center justify-center gap-2 py-1.5 px-3 text-sm font-medium border border-slate-300 rounded-lg hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Camera className="w-4 h-4" />
              Capture from Camera
            </button>
          </div>
          {status === 'success' ? (
            <div className="flex items-center gap-2 text-green-600">
              <CheckCircle className="w-5 h-5" />
              {message}
            </div>
          ) : status === 'capturing' ? (
            <div className="flex items-center gap-2 text-primary-600 bg-primary-50 px-3 py-2 rounded-lg text-sm">
              <span className="animate-pulse">Processing…</span>
              <span className="text-slate-500">Face recognition may take 30–60 seconds on first load.</span>
            </div>
          ) : status === 'error' ? (
            <div className="space-y-2">
              <div className="flex items-center gap-2 text-amber-700 bg-amber-50 px-3 py-2 rounded-lg text-sm">
                <XCircle className="w-4 h-4 shrink-0" />
                <span>{message}</span>
              </div>
              <button
                type="button"
                onClick={() => { setStatus('idle'); setMessage(''); }}
                className="w-full flex items-center justify-center gap-2 py-2 px-4 text-sm font-medium bg-amber-100 text-amber-800 border border-amber-200 rounded-lg hover:bg-amber-200"
              >
                Try again
              </button>
            </div>
          ) : null}
          <div className="flex gap-3 pt-4 mt-4 border-t border-slate-200">
            <button
              type="button"
              onClick={onCancel}
              className="flex-1 flex items-center justify-center py-2.5 px-4 text-sm font-medium border border-slate-300 rounded-lg bg-white text-slate-700 hover:bg-slate-50"
            >
              {isRegistrationMode ? 'Go back' : 'Skip (register later)'}
            </button>
            {status === 'success' && (
              <button
                type="button"
                onClick={onSuccess}
                className="flex-1 flex items-center justify-center py-2.5 px-4 text-sm font-medium bg-primary-600 text-white rounded-lg hover:bg-primary-700"
              >
                Done
              </button>
            )}
          </div>
        </div>
      </div>
    </div>,
    document.body
  );
}
