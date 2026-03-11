-- Attendance Tracking System - Database Schema v1
-- Mirrors supabase/migrations/001_initial_schema.sql
-- Teacher or Admin can add students. Only Admin can delete.
-- Tables: users, teachers, students, subjects, attendance, face_embeddings, logs, student_change_requests

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =============================================================================
-- Users (admin and teacher only - no student login)
-- =============================================================================
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL CHECK (role IN ('admin', 'teacher')),
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(email)
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_role ON users(role);

-- =============================================================================
-- Teachers (1:1 with users)
-- =============================================================================
CREATE TABLE teachers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id)
);

CREATE INDEX idx_teachers_user_id ON teachers(user_id);

-- =============================================================================
-- Students (class A/B, roll_number, parent_phone for SMS)
-- =============================================================================
CREATE TABLE students (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL,
    roll_number VARCHAR(50) NOT NULL,
    parent_phone VARCHAR(15) NOT NULL,
    class VARCHAR(10) NOT NULL CHECK (class IN ('A', 'B')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(email),
    UNIQUE(roll_number)
);

CREATE INDEX idx_students_email ON students(email);
CREATE INDEX idx_students_roll_number ON students(roll_number);
CREATE INDEX idx_students_class ON students(class);
CREATE INDEX idx_students_class_name ON students(class, name);

-- =============================================================================
-- Subjects (taught by teachers)
-- =============================================================================
CREATE TABLE subjects (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    teacher_id UUID NOT NULL REFERENCES teachers(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_subjects_teacher_id ON subjects(teacher_id);
CREATE INDEX idx_subjects_name ON subjects(name);

-- =============================================================================
-- Attendance (one record per student, subject, date)
-- =============================================================================
CREATE TABLE attendance (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    student_id UUID NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    subject_id UUID NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    check_in TIME,
    check_out TIME,
    status VARCHAR(50) NOT NULL DEFAULT 'present' CHECK (status IN ('present', 'absent', 'late', 'excused')),
    confidence_score FLOAT CHECK (confidence_score >= 0 AND confidence_score <= 1),
    ip_address VARCHAR(45),
    device_info TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(student_id, subject_id, date)
);

CREATE INDEX idx_attendance_student_date ON attendance(student_id, date);
CREATE INDEX idx_attendance_subject_date ON attendance(subject_id, date);
CREATE INDEX idx_attendance_student_subject_date ON attendance(student_id, subject_id, date);
CREATE INDEX idx_attendance_date ON attendance(date);
CREATE INDEX idx_attendance_status ON attendance(status) WHERE status = 'present';

-- =============================================================================
-- Face embeddings (512-D vectors for recognition)
-- =============================================================================
CREATE TABLE face_embeddings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    student_id UUID NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    embedding_vector FLOAT[] NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_face_embeddings_student ON face_embeddings(student_id);

-- =============================================================================
-- Logs (audit trail)
-- =============================================================================
CREATE TABLE logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    action VARCHAR(255) NOT NULL,
    ip_address VARCHAR(45),
    device_info TEXT,
    details JSONB DEFAULT '{}',
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_logs_user_id ON logs(user_id);
CREATE INDEX idx_logs_timestamp ON logs(timestamp DESC);
CREATE INDEX idx_logs_action ON logs(action);
CREATE INDEX idx_logs_action_timestamp ON logs(action, timestamp DESC);

-- =============================================================================
-- Student change requests (teachers request edits, admins approve/reject)
-- =============================================================================
CREATE TABLE student_change_requests (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    student_id UUID NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    requested_by UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    proposed_changes JSONB NOT NULL DEFAULT '{}',
    message TEXT,
    status VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected')),
    reviewed_by UUID REFERENCES users(id) ON DELETE SET NULL,
    reviewed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_student_change_requests_student ON student_change_requests(student_id);
CREATE INDEX idx_student_change_requests_requested_by ON student_change_requests(requested_by);
CREATE INDEX idx_student_change_requests_status ON student_change_requests(status);
CREATE INDEX idx_student_change_requests_created ON student_change_requests(created_at DESC);

-- =============================================================================
-- Realtime (Supabase live updates)
-- =============================================================================
DO $$
DECLARE
  tbl text;
  tables text[] := ARRAY['students', 'attendance', 'teachers', 'subjects', 'face_embeddings', 'logs', 'student_change_requests'];
BEGIN
  FOREACH tbl IN ARRAY tables
  LOOP
    IF NOT EXISTS (
      SELECT 1 FROM pg_publication_tables
      WHERE pubname = 'supabase_realtime' AND tablename = tbl
    ) THEN
      EXECUTE format('ALTER PUBLICATION supabase_realtime ADD TABLE %I', tbl);
    END IF;
  END LOOP;
END $$;

-- =============================================================================
-- Seed data
-- =============================================================================
INSERT INTO users (name, email, role, password_hash) VALUES
    ('Admin User', 'admin@school.com', 'admin', '$2b$12$G2RLGbtPqF9Wy3X1065g4OVG5mzg0xlx8wFywtUnvs2b14wGyny6S'),
    ('Teacher One', 'teacher@school.com', 'teacher', '$2b$12$G2RLGbtPqF9Wy3X1065g4OVG5mzg0xlx8wFywtUnvs2b14wGyny6S');

INSERT INTO teachers (user_id)
SELECT id FROM users WHERE email = 'teacher@school.com' AND role = 'teacher' LIMIT 1;
