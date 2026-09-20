import { client } from './client';

export interface AdminStats {
  total_users: number;
  total_students: number;
  total_faculty: number;
  total_departments: number;
  total_classes: number;
  total_leaves: number;
  total_ods: number;
}

export interface AdminUser {
  id: number;
  full_name: string;
  username: string;
  email: string;
  role: string;
  department_id?: number;
  department_name: string;
  class_group_id?: number;
  class_name: string;
  mentor_id?: number;
  mentor_name: string;
  register_number?: string;
  is_blocked: boolean;
}

export interface AdminDepartment {
  id: number;
  name: string;
  hod_id?: number;
  hod_name: string;
  class_count: number;
  student_count: number;
}

export interface AdminClassGroup {
  id: number;
  department_id: number;
  department_name: string;
  year: number;
  section: string;
  faculty_id?: number;
  faculty_name: string;
  student_count: number;
}

export interface SystemLeave {
  id: number;
  applicant: string;
  start_date: string;
  end_date: string;
  reason: string;
  is_emergency: boolean;
  status: string;
  applied_on: string;
}

export interface SystemOD {
  id: number;
  applicant: string;
  event_date: string;
  reason: string;
  status: string;
  applied_on: string;
}

export interface AuditLogItem {
  id: number;
  timestamp: string;
  actor: string;
  action: string;
  target_type: string;
  target_id: number | null;
  ip_address: string;
  details: string;
}

export const adminApi = {
  getStats: () => client.get<AdminStats>('/admin/stats'),

  getUsers: (role?: string, departmentId?: number) => {
    const params = new URLSearchParams();
    if (role) params.append('role', role);
    if (departmentId) params.append('department_id', String(departmentId));
    const query = params.toString() ? `?${params.toString()}` : '';
    return client.get<AdminUser[]>(`/admin/users${query}`);
  },

  createUser: (payload: {
    full_name: string;
    username: string;
    email: string;
    password?: string;
    role: string;
    department_id?: number;
    class_group_id?: number;
    register_number?: string;
    date_of_birth?: string;
    father_name?: string;
  }) => client.post<{ message: string; user_id: number }>('/admin/users', payload),

  deleteUser: (userId: number) => client.delete<{ message: string }>(`/admin/users/${userId}`),

  toggleBlockUser: (userId: number) => client.post<{ message: string }>(`/admin/users/${userId}/toggle-block`),

  getDepartments: () => client.get<AdminDepartment[]>('/admin/departments'),

  createDepartment: (name: string) =>
    client.post<{ message: string; department_id: number }>('/admin/departments', { name }),

  getClasses: () => client.get<AdminClassGroup[]>('/admin/classes'),

  createClass: (payload: { department_id: number; year: number; section: string }) =>
    client.post<{ message: string; class_id: number }>('/admin/classes', payload),

  assignHod: (departmentId: number, hodUserId: number) =>
    client.post<{ message: string }>('/admin/assign-hod', { department_id: departmentId, hod_user_id: hodUserId }),

  assignFaculty: (classGroupId: number, facultyId: number) =>
    client.post<{ message: string }>('/admin/assign-faculty', { class_group_id: classGroupId, faculty_id: facultyId }),

  assignMentor: (studentIds: number[], mentorId: number) =>
    client.post<{ message: string }>('/admin/assign-mentor', { student_ids: studentIds, mentor_id: mentorId }),

  getAllLeaves: () => client.get<SystemLeave[]>('/admin/all-leaves'),

  clearAllLeaves: () => client.post<{ message: string }>('/admin/clear-all-leaves'),

  reviewLeaveOverride: (leaveId: number, action: 'APPROVE' | 'REJECT', comment?: string) =>
    client.post<{ message: string }>(`/admin/leaves/${leaveId}/review`, { action, comment }),

  getAllOds: () => client.get<SystemOD[]>('/admin/all-ods'),

  clearAllOds: () => client.post<{ message: string }>('/admin/clear-all-ods'),

  reviewOdOverride: (odId: number, action: 'APPROVE' | 'REJECT', comment?: string) =>
    client.post<{ message: string }>(`/admin/ods/${odId}/review`, { action, comment }),

  getAuditLogs: () => client.get<AuditLogItem[]>('/admin/audit-logs'),
};

