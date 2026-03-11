import { useState, useCallback, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { studentsApi, teachersApi } from '../services/api';
import { FaceCaptureModal } from '../components/FaceCaptureModal';
import { CreateSubjectModal } from '../components/CreateSubjectModal';
import { useAuthContext } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import { getApiErrorMessage } from '../utils/apiError';
import * as XLSX from 'xlsx';
import { Plus, User, X, Pencil, Trash2, BookOpen, Download, Send } from 'lucide-react';
import { RequestChangeModal } from '../components/RequestChangeModal';

type Student = {
  id: string;
  name: string;
  email: string;
  roll_number: string;
  parent_phone: string;
  class_name: string;
};

export function StudentsPage() {
  const { user } = useAuthContext();
  const isAdmin = user?.role === 'admin';

  const [showModal, setShowModal] = useState(false);
  const [form, setForm] = useState({
    name: '',
    email: '',
    roll_number: '',
    parent_phone: '',
    class: 'A' as 'A' | 'B',
  });
  const [error, setError] = useState('');
  const [pendingFaceCapture, setPendingFaceCapture] = useState<{
    formData: { name: string; email: string; roll_number: string; parent_phone: string; class: 'A' | 'B' };
    studentName: string;
  } | null>(null);
  const [editingStudent, setEditingStudent] = useState<Student | null>(null);
  const [requestChangeStudent, setRequestChangeStudent] = useState<Student | null>(null);
  const [deleteConfirm, setDeleteConfirm] = useState<Student | null>(null);
  const [showSubjectModal, setShowSubjectModal] = useState(false);

  const queryClient = useQueryClient();
  const toast = useToast();

  const { data: teachers = [] } = useQuery({
    queryKey: ['teachers'],
    queryFn: () => teachersApi.list().then((r) => r.data || []),
    staleTime: 60_000,
  });

  const { data, isLoading, isError, error: queryError, refetch } = useQuery({
    queryKey: ['students'],
    queryFn: async () => {
      const res = await studentsApi.list();
      return Array.isArray(res.data) ? res.data : [];
    },
    retry: 1,
    staleTime: 20_000,
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Record<string, string> }) =>
      studentsApi.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['students'] });
      setEditingStudent(null);
      setError('');
      toast.success('Student updated successfully');
    },
    onError: (err) => {
      const msg = getApiErrorMessage(err, 'Failed to update student');
      setError(msg);
      toast.error(msg);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => studentsApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['students'] });
      setDeleteConfirm(null);
      toast.success('Student deleted successfully');
    },
    onError: (err) => {
      const msg = getApiErrorMessage(err, 'Failed to delete student');
      setError(msg);
      toast.error(msg);
    },
  });

  const handleRegisterWithFaceSuccess = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ['students'] });
    setPendingFaceCapture(null);
    setForm({ name: '', email: '', roll_number: '', parent_phone: '', class: 'A' });
  }, [queryClient]);

  const handleRegisterWithFaceCancel = useCallback(() => {
    setPendingFaceCapture(null);
    setShowModal(true);
  }, []);

  const anyModalOpen = showModal || !!editingStudent || !!requestChangeStudent || !!deleteConfirm || showSubjectModal || !!pendingFaceCapture;
  useEffect(() => {
    if (anyModalOpen) document.body.style.overflow = 'hidden';
    return () => { document.body.style.overflow = ''; };
  }, [anyModalOpen]);

  const handleExportExcel = useCallback(() => {
    const list = Array.isArray(data) ? data : [];
    const rows = list.map((s: Student) => ({
      Name: s.name || '',
      'Roll No': s.roll_number || '',
      Class: s.class_name || '',
      'Parent Phone (SMS)': s.parent_phone || '',
    }));
    if (rows.length === 0) return;
    const ws = XLSX.utils.json_to_sheet(rows);
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, 'Students');
    XLSX.writeFile(wb, 'students.xlsx');
  }, [data]);

  const handleEditSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingStudent) return;
    setError('');
    const data: Record<string, string> = {};
    if (form.name?.trim()) data.name = form.name.trim();
    if (form.email?.trim()) data.email = form.email.trim();
    if (form.roll_number?.trim()) data.roll_number = form.roll_number.trim();
    if (form.parent_phone?.trim()) data.parent_phone = form.parent_phone.trim();
    if (form.class) data.class = form.class;
    if (Object.keys(data).length === 0) return;
    updateMutation.mutate({ id: editingStudent.id, data });
  };

  const openEditModal = (s: Student) => {
    setEditingStudent(s);
    setForm({
      name: s.name || '',
      email: s.email || '',
      roll_number: s.roll_number,
      parent_phone: s.parent_phone,
      class: (s.class_name || 'A') as 'A' | 'B',
    });
    setError('');
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    if (!form.name || !form.email || !form.roll_number || !form.parent_phone) {
      setError('All fields are required');
      return;
    }
    /* Student is created ONLY when face is registered via register-with-face. No DB entry until then. */
    setPendingFaceCapture({ formData: form, studentName: form.name });
    setShowModal(false);
  };

  if (isLoading) return <div className="text-slate-500">Loading...</div>;

  if (isError) {
    const errMsg = (queryError as { response?: { data?: { message?: string }; status?: number } })?.response?.data?.message
      || (queryError as Error)?.message
      || 'Failed to load students';
    return (
      <div className="space-y-4">
        <h1 className="text-2xl font-bold text-slate-800">Students</h1>
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">
          <p className="font-medium">Could not load students</p>
          <p className="text-sm mt-1">{errMsg}</p>
          <p className="text-xs mt-2 text-slate-600">Ensure the backend is running and the database schema is up to date (run supabase/migrations/001_initial_schema.sql).</p>
          <button
            onClick={() => refetch()}
            className="mt-3 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 text-sm"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  const students: Student[] = Array.isArray(data) ? data : [];

  return (
    <div className="w-full min-w-0">
      {!isAdmin && (
        <div className="mb-6 p-4 rounded-xl bg-primary-50 border border-primary-200">
          <p className="text-sm text-primary-800">
            <strong>Need to update a student?</strong> Click &quot;Request update&quot; on any row to submit changes. Admin will review and approve your request.
          </p>
        </div>
      )}
      <div className="flex flex-col sm:flex-row sm:flex-wrap sm:justify-between sm:items-center gap-4 mb-8">
        <h1 className="text-2xl font-bold text-slate-800 shrink-0">Students</h1>
        <div className="flex flex-wrap items-center gap-3 shrink-0">
          <button
            onClick={handleExportExcel}
            disabled={students.length === 0}
            className="inline-flex items-center justify-center gap-2 px-3 py-1.5 text-sm font-medium border border-slate-300 rounded-lg hover:bg-slate-50 text-slate-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Download className="w-4 h-4 shrink-0" />
            Export to Excel
          </button>
          <button
            onClick={() => setShowSubjectModal(true)}
            className="inline-flex items-center justify-center gap-2 px-3 py-1.5 text-sm font-medium border border-slate-300 rounded-lg hover:bg-slate-50 text-slate-700"
          >
            <BookOpen className="w-4 h-4 shrink-0" />
            Create Subject
          </button>
          <button
            onClick={() => setShowModal(true)}
            className="inline-flex items-center justify-center gap-2 px-3 py-1.5 text-sm font-medium bg-primary-600 text-white rounded-lg hover:bg-primary-700"
          >
            <Plus className="w-4 h-4 shrink-0" />
            Add Student
          </button>
        </div>
      </div>

      <CreateSubjectModal
        open={showSubjectModal}
        onClose={() => setShowSubjectModal(false)}
        teachers={(teachers as { id: string; users?: { name: string } }[]) || []}
      />

      {showModal && createPortal(
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm overflow-y-auto">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-lg my-8">
            <div className="px-6 py-5 border-b border-slate-200">
              <div className="flex justify-between items-start gap-4">
                <div>
                  <h2 className="text-lg font-semibold text-slate-800">Add Student</h2>
                  <p className="text-xs text-slate-500 mt-1">Face registration required — student will be added only after face is captured</p>
                </div>
                <button
                  type="button"
                  onClick={() => {
                    setShowModal(false);
                    setError('');
                    setForm({ name: '', email: '', roll_number: '', parent_phone: '', class: 'A' });
                  }}
                  className="p-1.5 hover:bg-slate-100 rounded-lg"
                >
                  <X className="w-5 h-5 text-slate-600" />
                </button>
              </div>
            </div>
            <form onSubmit={handleSubmit}>
              <div className="px-6 py-5 space-y-4">
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1.5">Full Name</label>
                  <input
                    type="text"
                    value={form.name}
                    onChange={(e) => setForm({ ...form, name: e.target.value })}
                    className="w-full px-4 py-2 border border-slate-300 rounded-lg text-slate-900 bg-white"
                    placeholder="Student full name"
                    required
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1.5">Email</label>
                  <input
                    type="email"
                    value={form.email}
                    onChange={(e) => setForm({ ...form, email: e.target.value })}
                    className="w-full px-4 py-2 border border-slate-300 rounded-lg text-slate-900 bg-white"
                    required
                  />
                </div>
                <div className="relative z-10">
                  <label className="block text-sm font-medium text-slate-700 mb-1.5">Class</label>
                  <select
                    value={form.class}
                    onChange={(e) => setForm({ ...form, class: e.target.value as 'A' | 'B' })}
                    className="w-full px-4 py-2 border border-slate-300 rounded-lg text-slate-900 bg-white"
                  >
                    <option value="A">Class A</option>
                    <option value="B">Class B</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1.5">Roll Number</label>
                  <input
                    type="text"
                    value={form.roll_number}
                    onChange={(e) => setForm({ ...form, roll_number: e.target.value })}
                    className="w-full px-4 py-2 border border-slate-300 rounded-lg text-slate-900 bg-white"
                    placeholder="Student roll number"
                    required
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1.5">Parent&apos;s Phone (SMS alerts)</label>
                  <input
                    type="tel"
                    value={form.parent_phone}
                    onChange={(e) => setForm({ ...form, parent_phone: e.target.value })}
                    className="w-full px-4 py-2 border border-slate-300 rounded-lg text-slate-900 bg-white"
                    placeholder="10-15 digits — receives SMS when attendance &lt; 60%"
                    required
                  />
                </div>
                {error && <p className="text-red-600 text-sm">{error}</p>}
              </div>
              <div className="flex gap-3 px-6 py-5 border-t border-slate-200 bg-slate-50 rounded-b-xl">
                <button
                  type="button"
                  onClick={() => {
                    setShowModal(false);
                    setForm({ name: '', email: '', roll_number: '', parent_phone: '', class: 'A' });
                    setError('');
                  }}
                  className="flex-1 py-2.5 px-4 text-sm font-medium border border-slate-300 rounded-lg bg-white text-slate-700 hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="flex-1 py-2.5 px-4 text-sm font-medium bg-primary-600 text-white rounded-lg hover:bg-primary-700 whitespace-nowrap"
                >
                  Next: Register Face
                </button>
              </div>
            </form>
          </div>
        </div>,
        document.body
      )}

      {editingStudent && createPortal(
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm overflow-y-auto">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-lg my-8">
            <div className="px-6 py-5 border-b border-slate-200">
              <div className="flex justify-between items-center">
                <h2 className="text-lg font-semibold text-slate-800">Edit Student</h2>
                <button
                  type="button"
                  onClick={() => { setEditingStudent(null); setError(''); }}
                  className="p-1.5 hover:bg-slate-100 rounded-lg"
                >
                  <X className="w-5 h-5 text-slate-600" />
                </button>
              </div>
            </div>
            <form onSubmit={handleEditSubmit}>
              <div className="px-6 py-5 space-y-4">
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1.5">Full Name</label>
                  <input
                    type="text"
                    value={form.name}
                    onChange={(e) => setForm({ ...form, name: e.target.value })}
                    className="w-full px-4 py-2 border border-slate-300 rounded-lg text-slate-900 bg-white"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1.5">Email</label>
                  <input
                    type="email"
                    value={form.email}
                    onChange={(e) => setForm({ ...form, email: e.target.value })}
                    className="w-full px-4 py-2 border border-slate-300 rounded-lg text-slate-900 bg-white"
                  />
                </div>
                <div className="relative z-10">
                  <label className="block text-sm font-medium text-slate-700 mb-1.5">Class</label>
                  <select
                    value={form.class}
                    onChange={(e) => setForm({ ...form, class: e.target.value as 'A' | 'B' })}
                    className="w-full px-4 py-2 border border-slate-300 rounded-lg text-slate-900 bg-white"
                  >
                    <option value="A">Class A</option>
                    <option value="B">Class B</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1.5">Roll Number</label>
                  <input
                    type="text"
                    value={form.roll_number}
                    onChange={(e) => setForm({ ...form, roll_number: e.target.value })}
                    className="w-full px-4 py-2 border border-slate-300 rounded-lg text-slate-900 bg-white"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1.5">Parent&apos;s Phone (SMS alerts)</label>
                  <input
                    type="tel"
                    value={form.parent_phone}
                    onChange={(e) => setForm({ ...form, parent_phone: e.target.value })}
                    className="w-full px-4 py-2 border border-slate-300 rounded-lg text-slate-900 bg-white"
                    placeholder="Receives SMS when attendance &lt; 60%"
                  />
                </div>
                {error && <p className="text-red-600 text-sm">{error}</p>}
              </div>
              <div className="flex gap-3 px-6 py-5 border-t border-slate-200 bg-slate-50 rounded-b-xl">
                <button
                  type="button"
                  onClick={() => setEditingStudent(null)}
                  className="flex-1 py-2.5 px-4 text-sm font-medium border border-slate-300 rounded-lg bg-white text-slate-700 hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={updateMutation.isPending}
                  className="flex-1 py-2.5 px-4 text-sm font-medium bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50"
                >
                  {updateMutation.isPending ? 'Saving...' : 'Save'}
                </button>
              </div>
            </form>
          </div>
        </div>,
        document.body
      )}

      {deleteConfirm && createPortal(
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm overflow-y-auto">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-lg">
            <div className="px-6 py-5 border-b border-slate-200">
              <h2 className="text-lg font-semibold text-slate-800">Delete Student</h2>
            </div>
            <div className="px-6 py-5">
              <p className="text-slate-600 mb-4">
                Are you sure you want to delete <strong>{deleteConfirm.name || deleteConfirm.id}</strong>? This will remove the student and all related data.
              </p>
              {error && <p className="text-red-600 text-sm mb-4">{error}</p>}
            </div>
            <div className="flex gap-3 px-6 py-5 border-t border-slate-200 bg-slate-50 rounded-b-xl">
              <button
                onClick={() => { setDeleteConfirm(null); setError(''); }}
                className="flex-1 flex items-center justify-center py-2.5 px-4 text-sm font-medium border border-slate-300 rounded-lg bg-white text-slate-700 hover:bg-slate-50"
              >
                Cancel
              </button>
              <button
                onClick={() => deleteMutation.mutate(deleteConfirm.id)}
                disabled={deleteMutation.isPending}
                className="flex-1 flex items-center justify-center py-2.5 px-4 text-sm font-medium bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50"
              >
                {deleteMutation.isPending ? 'Deleting...' : 'Delete'}
              </button>
            </div>
          </div>
        </div>,
        document.body
      )}

      {requestChangeStudent && (
        <RequestChangeModal
          student={requestChangeStudent}
          onSuccess={() => {
            setRequestChangeStudent(null);
            queryClient.invalidateQueries({ queryKey: ['change-requests-pending'] });
          }}
          onCancel={() => setRequestChangeStudent(null)}
        />
      )}

      {pendingFaceCapture && (
        <FaceCaptureModal
          studentName={pendingFaceCapture.studentName}
          formData={pendingFaceCapture.formData}
          onSuccess={handleRegisterWithFaceSuccess}
          onCancel={handleRegisterWithFaceCancel}
        />
      )}

      <div className="bg-white rounded-xl border border-slate-200 overflow-x-auto mt-2">
        <table className="w-full min-w-[600px]">
          <thead className="bg-slate-50 border-b border-slate-200">
            <tr>
              <th className="text-left px-6 py-3 text-sm font-medium text-slate-700 align-middle">Name</th>
              <th className="text-left px-6 py-3 text-sm font-medium text-slate-700 align-middle">Roll No</th>
              <th className="text-left px-6 py-3 text-sm font-medium text-slate-700 align-middle">Class</th>
              <th className="text-left px-6 py-3 text-sm font-medium text-slate-700 align-middle">Parent Phone (SMS)</th>
              <th className="text-right px-6 py-3 text-sm font-medium text-slate-700 align-middle">Actions</th>
            </tr>
          </thead>
          <tbody>
            {students.map((s) => (
              <tr key={s.id} className="border-b border-slate-100 hover:bg-slate-50">
                <td className="px-6 py-4 align-middle">
                  <span className="inline-flex items-center gap-2">
                    <User className="w-4 h-4 text-slate-400 shrink-0" />
                    <span className="truncate">{s.name || s.id}</span>
                  </span>
                </td>
                <td className="px-6 py-4 text-slate-600 align-middle">{s.roll_number}</td>
                <td className="px-6 py-4 text-slate-600 align-middle">{s.class_name || '-'}</td>
                <td className="px-6 py-4 text-slate-600 align-middle">{s.parent_phone}</td>
                <td className="px-6 py-4 text-right align-middle">
                  {isAdmin ? (
                    <>
                      <button
                        onClick={() => openEditModal(s)}
                        className="p-2 text-slate-600 hover:bg-slate-100 rounded-lg mr-1"
                        title="Edit"
                      >
                        <Pencil className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => setDeleteConfirm(s)}
                        className="p-2 text-red-600 hover:bg-red-50 rounded-lg"
                        title="Delete"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </>
                  ) : (
                    <button
                      onClick={() => setRequestChangeStudent(s)}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-primary-700 bg-primary-50 hover:bg-primary-100 rounded-lg border border-primary-200"
                      title="Request update for admin to review"
                    >
                      <Send className="w-4 h-4" />
                      Request update
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {students.length === 0 && (
          <div className="py-12 text-center text-slate-500">No students yet. Click &quot;Add Student&quot; to add one.</div>
        )}
      </div>
    </div>
  );
}
