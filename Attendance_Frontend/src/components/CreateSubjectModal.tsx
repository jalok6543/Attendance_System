import { useState } from 'react';
import { createPortal } from 'react-dom';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { subjectsApi } from '../services/api';
import { useToast } from '../context/ToastContext';
import { getApiErrorMessage } from '../utils/apiError';
import { X } from 'lucide-react';

interface Teacher {
  id: string;
  users?: { name: string };
}

interface CreateSubjectModalProps {
  open: boolean;
  onClose: () => void;
  teachers: Teacher[];
  onSuccess?: (subjectId?: string) => void;
  selectSubjectId?: (id: string) => void;
}

export function CreateSubjectModal({
  open,
  onClose,
  teachers = [],
  onSuccess,
  selectSubjectId,
}: CreateSubjectModalProps) {
  const [newSubject, setNewSubject] = useState({ name: '', teacher_id: '' });
  const [subjectError, setSubjectError] = useState('');
  const queryClient = useQueryClient();
  const toast = useToast();

  const createSubjectMutation = useMutation({
    mutationFn: (data: { name: string; teacher_id: string }) => subjectsApi.create(data),
    onSuccess: (res) => {
      const newId = res?.data?.id;
      if (newId && selectSubjectId) selectSubjectId(newId);
      queryClient.invalidateQueries({ queryKey: ['subjects'] });
      onClose();
      setNewSubject({ name: '', teacher_id: '' });
      setSubjectError('');
      toast.success('Subject created successfully');
      onSuccess?.(newId);
    },
    onError: (err) => {
      const errMsg = getApiErrorMessage(err, 'Failed to create subject');
      setSubjectError(errMsg);
      toast.error(errMsg);
    },
  });

  const handleClose = () => {
    setSubjectError('');
    setNewSubject({ name: '', teacher_id: '' });
    onClose();
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setSubjectError('');
    if (!newSubject.name || !newSubject.teacher_id) {
      setSubjectError('Name and teacher are required');
      return;
    }
    createSubjectMutation.mutate(newSubject);
  };

  if (!open) return null;

  return createPortal(
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm overflow-y-auto">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-lg my-8">
        <div className="px-6 py-5 border-b border-slate-200">
          <div className="flex justify-between items-center">
            <h2 className="text-lg font-semibold text-slate-800">Create Subject</h2>
            <button type="button" onClick={handleClose} className="p-1.5 hover:bg-slate-100 rounded-lg">
              <X className="w-5 h-5 text-slate-600" />
            </button>
          </div>
        </div>
        <form onSubmit={handleSubmit}>
          <div className="px-6 py-5 space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1.5">Subject Name</label>
              <input
                type="text"
                value={newSubject.name}
                onChange={(e) => setNewSubject({ ...newSubject, name: e.target.value })}
                className="w-full px-4 py-2 border border-slate-300 rounded-lg text-slate-900 bg-white"
                placeholder="e.g. Mathematics"
                required
              />
            </div>
            <div className="relative z-10">
              <label className="block text-sm font-medium text-slate-700 mb-1.5">Teacher</label>
              <select
                value={newSubject.teacher_id}
                onChange={(e) => setNewSubject({ ...newSubject, teacher_id: e.target.value })}
                className="w-full px-4 py-2 border border-slate-300 rounded-lg text-slate-900 bg-white"
                required
              >
                <option value="">Select teacher</option>
                {teachers.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.users?.name || t.id}
                  </option>
                ))}
              </select>
            </div>
            {subjectError && <p className="text-destructive-600 text-sm">{subjectError}</p>}
          </div>
          <div className="flex gap-3 px-6 py-5 border-t border-slate-200 bg-slate-50 rounded-b-xl">
            <button
              type="button"
              onClick={handleClose}
              className="flex-1 py-2.5 px-4 text-sm font-medium border border-slate-300 rounded-lg bg-white text-slate-700 hover:bg-slate-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={createSubjectMutation.isPending}
              className="flex-1 py-2.5 px-4 text-sm font-medium bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50"
            >
              {createSubjectMutation.isPending ? 'Creating...' : 'Create Subject'}
            </button>
          </div>
        </form>
      </div>
    </div>,
    document.body
  );
}
