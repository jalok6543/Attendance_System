import { useState } from 'react';
import { createPortal } from 'react-dom';
import { changeRequestsApi } from '../services/api';
import { getApiErrorMessage } from '../utils/apiError';
import { useToast } from '../context/ToastContext';
import { X } from 'lucide-react';

type Student = {
  id: string;
  name: string;
  email: string;
  roll_number: string;
  parent_phone: string;
  class_name: string;
};

interface RequestChangeModalProps {
  student: Student;
  onSuccess: () => void;
  onCancel: () => void;
}

export function RequestChangeModal({ student, onSuccess, onCancel }: RequestChangeModalProps) {
  const toast = useToast();
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    if (!message.trim()) {
      setError('Message to Admin is required. Please describe the changes you need.');
      return;
    }

    setSubmitting(true);
    try {
      await changeRequestsApi.create({
        student_id: student.id,
        proposed_changes: {},
        message: message.trim(),
      });
      toast.success('Change request submitted. Admin will review shortly.');
      onSuccess();
    } catch (err) {
      const msg = getApiErrorMessage(err, 'Failed to submit change request');
      setError(msg);
      toast.error(msg);
    } finally {
      setSubmitting(false);
    }
  };

  return createPortal(
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm overflow-y-auto">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-lg my-8">
        <div className="px-6 py-5 border-b border-slate-200">
          <div className="flex justify-between items-center">
            <div>
              <h2 className="text-lg font-semibold text-slate-800">Request Update for Admin</h2>
              <p className="text-sm text-slate-500 mt-0.5">Describe the changes needed for <strong>{student.name}</strong>. Admin will review and apply updates.</p>
            </div>
            <button
              type="button"
              onClick={onCancel}
              className="p-1.5 hover:bg-slate-100 rounded-lg"
            >
              <X className="w-5 h-5 text-slate-600" />
            </button>
          </div>
        </div>
        <form onSubmit={handleSubmit}>
          <div className="px-6 py-5 space-y-4">
            <div className="rounded-lg bg-slate-50 border border-slate-200 px-4 py-3 text-sm text-slate-600 space-y-1.5">
              <p><span className="font-medium text-slate-700">Student:</span> {student.name}</p>
              <p><span className="font-medium text-slate-700">Email:</span> {student.email || '—'}</p>
              <p><span className="font-medium text-slate-700">Roll:</span> {student.roll_number || '—'}</p>
              <p><span className="font-medium text-slate-700">Class:</span> {student.class_name || '—'}</p>
              <p><span className="font-medium text-slate-700">Parent phone:</span> {student.parent_phone || '—'}</p>
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1.5">Message to Admin <span className="text-destructive-600">*</span></label>
              <textarea
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                className="w-full px-4 py-2 border border-slate-300 rounded-lg text-slate-900 bg-white resize-none"
                rows={4}
                placeholder="Describe the changes you need (e.g. update parent phone, correct email, change class...)"
                maxLength={500}
                required
              />
            </div>
            {error && <p className="text-destructive-600 text-sm">{error}</p>}
          </div>
          <div className="flex gap-3 px-6 py-5 border-t border-slate-200 bg-slate-50 rounded-b-xl">
            <button
              type="button"
              onClick={onCancel}
              className="flex-1 py-2.5 px-4 text-sm font-medium border border-slate-300 rounded-lg bg-white text-slate-700 hover:bg-slate-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="flex-1 py-2.5 px-4 text-sm font-medium bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50"
            >
              {submitting ? 'Submitting...' : 'Submit to Admin'}
            </button>
          </div>
        </form>
      </div>
    </div>,
    document.body
  );
}
