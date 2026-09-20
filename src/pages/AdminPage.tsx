import React, { useState, useEffect } from 'react';
import {
  Shield,
  Users,
  UserPlus,
  Building,
  GraduationCap,
  FileText,
  Trash2,
  UserCheck,
  CheckCircle2,
  AlertTriangle,
  RefreshCw,
  Search,
  PlusCircle,
  Award
} from 'lucide-react';
import {
  Button,
  Card,
  Input,
  Select,
  Badge,
  PageHeader,
  StatCard,
  Modal,
  Toast,
  Alert
} from '../components/ui';
import {
  adminApi,
  AdminStats,
  AdminUser,
  AdminDepartment,
  AdminClassGroup,
  SystemLeave,
  SystemOD,
  AuditLogItem
} from '../api/admin';

export const AdminPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'users' | 'departments' | 'classes' | 'assignments' | 'leaves' | 'ods' | 'logs'>('users');
  
  // Data states
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [departments, setDepartments] = useState<AdminDepartment[]>([]);
  const [classes, setClasses] = useState<AdminClassGroup[]>([]);
  const [leaves, setLeaves] = useState<SystemLeave[]>([]);
  const [ods, setOds] = useState<SystemOD[]>([]);
  const [auditLogs, setAuditLogs] = useState<AuditLogItem[]>([]);
  
  // Loading & Filter states
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [roleFilter, setRoleFilter] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [toastMsg, setToastMsg] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Modals
  const [createUserModal, setCreateUserModal] = useState(false);
  const [createDeptModal, setCreateDeptModal] = useState(false);
  const [createClassModal, setCreateClassModal] = useState(false);
  const [deleteUserModal, setDeleteUserModal] = useState<AdminUser | null>(null);
  const [clearLeavesModal, setClearLeavesModal] = useState(false);
  const [clearOdsModal, setClearOdsModal] = useState(false);

  // Form states
  const [newUser, setNewUser] = useState({
    full_name: '',
    username: '',
    email: '',
    password: '',
    role: 'student',
    department_id: '',
    class_group_id: '',
    register_number: '',
    date_of_birth: '',
    father_name: ''
  });

  const [newDeptName, setNewDeptName] = useState('');
  const [newClass, setNewClass] = useState({ department_id: '', year: '1', section: 'A' });

  // Assignment states
  const [assignHodForm, setAssignHodForm] = useState({ department_id: '', hod_user_id: '' });
  const [assignFacultyForm, setAssignFacultyForm] = useState({ class_group_id: '', faculty_id: '' });
  const [assignMentorForm, setAssignMentorForm] = useState({ student_ids: [] as number[], mentor_id: '' });

  const loadAdminData = async () => {
    setIsLoading(true);
    setErrorMsg(null);
    try {
      const [sData, uData, dData, cData, lData, oData, logData] = await Promise.all([
        adminApi.getStats().catch(() => null),
        adminApi.getUsers().catch(() => []),
        adminApi.getDepartments().catch(() => []),
        adminApi.getClasses().catch(() => []),
        adminApi.getAllLeaves().catch(() => []),
        adminApi.getAllOds().catch(() => []),
        adminApi.getAuditLogs().catch(() => [])
      ]);

      if (sData) setStats(sData);
      setUsers(uData);
      setDepartments(dData);
      setClasses(cData);
      setLeaves(lData);
      setOds(oData);
      setAuditLogs(logData);
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to load administrative dataset.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadAdminData();
  }, []);

  const handleToggleBlock = async (u: AdminUser) => {
    try {
      const res = await adminApi.toggleBlockUser(u.id);
      setToastMsg(res.message);
      await loadAdminData();
    } catch (err: any) {
      alert(err.message || 'Failed to toggle user block status');
    }
  };

  const handleReviewLeaveOverride = async (leaveId: number, action: 'APPROVE' | 'REJECT') => {
    try {
      const res = await adminApi.reviewLeaveOverride(leaveId, action);
      setToastMsg(res.message);
      await loadAdminData();
    } catch (err: any) {
      alert(err.message || 'Failed to override leave decision');
    }
  };

  const handleReviewOdOverride = async (odId: number, action: 'APPROVE' | 'REJECT') => {
    try {
      const res = await adminApi.reviewOdOverride(odId, action);
      setToastMsg(res.message);
      await loadAdminData();
    } catch (err: any) {
      alert(err.message || 'Failed to override OD decision');
    }
  };

  // Handlers
  const handleCreateUser = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    try {
      const res = await adminApi.createUser({
        full_name: newUser.full_name,
        username: newUser.username,
        email: newUser.email,
        password: newUser.password,
        role: newUser.role,
        department_id: newUser.department_id ? Number(newUser.department_id) : undefined,
        class_group_id: newUser.class_group_id ? Number(newUser.class_group_id) : undefined,
        register_number: newUser.register_number || undefined,
        date_of_birth: newUser.date_of_birth || undefined,
        father_name: newUser.father_name || undefined
      });
      setToastMsg(res.message);
      setCreateUserModal(false);
      setNewUser({
        full_name: '', username: '', email: '', password: '', role: 'student',
        department_id: '', class_group_id: '', register_number: '', date_of_birth: '', father_name: ''
      });
      await loadAdminData();
    } catch (err: any) {
      alert(err.message || 'Failed to create user');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDeleteUser = async () => {
    if (!deleteUserModal) return;
    setIsSubmitting(true);
    try {
      const res = await adminApi.deleteUser(deleteUserModal.id);
      setToastMsg(res.message);
      setDeleteUserModal(null);
      await loadAdminData();
    } catch (err: any) {
      alert(err.message || 'Failed to delete user');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCreateDept = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newDeptName.trim()) return;
    setIsSubmitting(true);
    try {
      const res = await adminApi.createDepartment(newDeptName.trim());
      setToastMsg(res.message);
      setCreateDeptModal(false);
      setNewDeptName('');
      await loadAdminData();
    } catch (err: any) {
      alert(err.message || 'Failed to create department');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCreateClass = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newClass.department_id) return;
    setIsSubmitting(true);
    try {
      const res = await adminApi.createClass({
        department_id: Number(newClass.department_id),
        year: Number(newClass.year),
        section: newClass.section
      });
      setToastMsg(res.message);
      setCreateClassModal(false);
      await loadAdminData();
    } catch (err: any) {
      alert(err.message || 'Failed to create class group');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleAssignHod = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!assignHodForm.department_id || !assignHodForm.hod_user_id) return;
    setIsSubmitting(true);
    try {
      const res = await adminApi.assignHod(Number(assignHodForm.department_id), Number(assignHodForm.hod_user_id));
      setToastMsg(res.message);
      await loadAdminData();
    } catch (err: any) {
      alert(err.message || 'Failed to assign HOD');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleAssignFaculty = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!assignFacultyForm.class_group_id || !assignFacultyForm.faculty_id) return;
    setIsSubmitting(true);
    try {
      const res = await adminApi.assignFaculty(Number(assignFacultyForm.class_group_id), Number(assignFacultyForm.faculty_id));
      setToastMsg(res.message);
      await loadAdminData();
    } catch (err: any) {
      alert(err.message || 'Failed to assign Faculty');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleAssignMentor = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!assignMentorForm.mentor_id || assignMentorForm.student_ids.length === 0) return;
    setIsSubmitting(true);
    try {
      const res = await adminApi.assignMentor(assignMentorForm.student_ids, Number(assignMentorForm.mentor_id));
      setToastMsg(res.message);
      setAssignMentorForm({ student_ids: [], mentor_id: '' });
      await loadAdminData();
    } catch (err: any) {
      alert(err.message || 'Failed to assign Mentor');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleClearLeaves = async () => {
    setIsSubmitting(true);
    try {
      const res = await adminApi.clearAllLeaves();
      setToastMsg(res.message);
      setClearLeavesModal(false);
      await loadAdminData();
    } catch (err: any) {
      alert(err.message || 'Failed to clear leave records');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleClearOds = async () => {
    setIsSubmitting(true);
    try {
      const res = await adminApi.clearAllOds();
      setToastMsg(res.message);
      setClearOdsModal(false);
      await loadAdminData();
    } catch (err: any) {
      alert(err.message || 'Failed to clear OD records');
    } finally {
      setIsSubmitting(false);
    }
  };

  const filteredUsers = users.filter((u) => {
    const matchesRole = !roleFilter || u.role === roleFilter;
    const matchesSearch =
      !searchQuery ||
      u.full_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      u.username.toLowerCase().includes(searchQuery.toLowerCase()) ||
      u.email.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesRole && matchesSearch;
  });

  const studentsList = users.filter((u) => u.role === 'student');
  const facultyList = users.filter((u) => u.role === 'faculty');
  const mentorList = users.filter((u) => u.role === 'mentor' || u.role === 'faculty');
  const hodList = users.filter((u) => u.role === 'hod' || u.role === 'faculty');

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <PageHeader
        title="System Administration & Registry"
        subtitle="Manage users, academic structure, faculty assignments, system records, and organizational controls."
        badge={<Badge variant="warning">ADMINISTRATOR CONTROL</Badge>}
        actions={
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              icon={<RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />}
              onClick={loadAdminData}
            >
              Sync Data
            </Button>
            <Button
              variant="primary"
              icon={<UserPlus className="w-4 h-4" />}
              onClick={() => setCreateUserModal(true)}
            >
              Create New User
            </Button>
          </div>
        }
      />

      {errorMsg && (
        <Alert type="danger" title="Administrative Error">
          {errorMsg}
        </Alert>
      )}

      {/* Metric Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        <StatCard label="Total Users" value={stats?.total_users ?? users.length} icon={<Users className="w-4 h-4" />} variant="primary" />
        <StatCard label="Students" value={stats?.total_students ?? studentsList.length} variant="info" />
        <StatCard label="Faculty" value={stats?.total_faculty ?? facultyList.length} variant="success" />
        <StatCard label="Departments" value={stats?.total_departments ?? departments.length} variant="neutral" />
        <StatCard label="Classes" value={stats?.total_classes ?? classes.length} variant="warning" />
        <StatCard label="Total Leaves" value={stats?.total_leaves ?? leaves.length} variant="danger" />
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-1.5 border-b border-border pb-3 overflow-x-auto">
        {[
          { id: 'users', label: 'User Registry', icon: Users },
          { id: 'departments', label: 'Departments', icon: Building },
          { id: 'classes', label: 'Class Cohorts', icon: GraduationCap },
          { id: 'assignments', label: 'Role Assignments', icon: UserCheck },
          { id: 'leaves', label: 'Leave Oversight', icon: FileText },
          { id: 'ods', label: 'OD Oversight', icon: Award },
          { id: 'logs', label: 'Audit Logs & Reports', icon: Shield },
        ].map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold rounded-lg transition-all whitespace-nowrap ${
                isActive
                  ? 'bg-primary text-[#07151F] shadow-sm'
                  : 'bg-surface-elevated text-text-secondary hover:text-text-primary hover:bg-surface-hover'
              }`}
            >
              <Icon className="w-3.5 h-3.5" />
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* TAB 1: USER REGISTRY */}
      {activeTab === 'users' && (
        <Card className="p-0 overflow-hidden space-y-0">
          <div className="p-4 border-b border-border bg-surface-elevated/20 flex flex-col sm:flex-row items-center justify-between gap-3">
            <div className="relative w-full sm:w-72">
              <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-text-muted" />
              <input
                type="text"
                placeholder="Search user name, username..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-9 pr-3 py-1.5 text-xs bg-bg border border-border rounded-lg text-text-primary placeholder:text-text-muted focus:outline-none focus:border-primary"
              />
            </div>
            <div className="flex items-center gap-2 w-full sm:w-auto">
              <Select
                value={roleFilter}
                onChange={(e) => setRoleFilter(e.target.value)}
                options={[
                  { value: '', label: 'All User Roles' },
                  { value: 'student', label: 'Students' },
                  { value: 'faculty', label: 'Faculty' },
                  { value: 'mentor', label: 'Mentors' },
                  { value: 'hod', label: 'HODs' },
                  { value: 'admin', label: 'Admins' },
                  { value: 'event_coordinator', label: 'Event Coordinators' }
                ]}
              />
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-border bg-surface-elevated/50 text-[11px] font-semibold text-text-muted uppercase tracking-wider">
                  <th className="py-3 px-4">Full Name</th>
                  <th className="py-3 px-4">Username & Email</th>
                  <th className="py-3 px-4">Role</th>
                  <th className="py-3 px-4">Department / Class</th>
                  <th className="py-3 px-4">Mentor</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/40 text-xs">
                {filteredUsers.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="py-8 text-center text-text-muted">
                      No matching user records found.
                    </td>
                  </tr>
                ) : (
                  filteredUsers.map((u) => (
                    <tr key={u.id} className="hover:bg-surface-elevated/30 transition-colors">
                      <td className="py-3 px-4 font-semibold text-text-primary">{u.full_name}</td>
                      <td className="py-3 px-4">
                        <div className="font-mono text-text-primary">@{u.username}</div>
                        <div className="text-[11px] text-text-muted">{u.email}</div>
                      </td>
                      <td className="py-3 px-4">
                        <div className="flex items-center gap-1.5">
                          <Badge
                            variant={
                              u.role === 'admin'
                                ? 'danger'
                                : u.role === 'hod'
                                ? 'warning'
                                : u.role === 'faculty'
                                ? 'success'
                                : u.role === 'mentor'
                                ? 'info'
                                : 'primary'
                            }
                            size="sm"
                          >
                            {u.role.toUpperCase()}
                          </Badge>
                          {u.is_blocked ? (
                            <Badge variant="danger" size="sm">BLOCKED</Badge>
                          ) : (
                            <Badge variant="success" size="sm">ACTIVE</Badge>
                          )}
                        </div>
                      </td>
                      <td className="py-3 px-4 text-text-secondary">
                        <div>{u.department_name}</div>
                        {u.class_name !== 'N/A' && (
                          <div className="text-[10px] text-text-muted">{u.class_name}</div>
                        )}
                      </td>
                      <td className="py-3 px-4 text-text-muted">{u.mentor_name}</td>
                      <td className="py-3 px-4 text-right">
                        <div className="flex items-center justify-end gap-1.5">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleToggleBlock(u)}
                          >
                            {u.is_blocked ? 'Unblock' : 'Block'}
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            icon={<Trash2 className="w-3.5 h-3.5 text-danger" />}
                            onClick={() => setDeleteUserModal(u)}
                          >
                            Delete
                          </Button>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {/* TAB 2: DEPARTMENTS */}
      {activeTab === 'departments' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-text-primary">Academic Departments</h3>
            <Button
              variant="primary"
              size="sm"
              icon={<PlusCircle className="w-4 h-4" />}
              onClick={() => setCreateDeptModal(true)}
            >
              Add Department
            </Button>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {departments.map((d) => (
              <Card key={d.id} className="p-5 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-base text-text-primary">{d.name}</span>
                  <Badge variant="primary">ID: {d.id}</Badge>
                </div>
                <div className="space-y-1 text-xs text-text-muted">
                  <div>Assigned HOD: <span className="font-semibold text-text-primary">{d.hod_name}</span></div>
                  <div>Class Groups: <span className="font-semibold text-text-primary">{d.class_count}</span></div>
                  <div>Students Enrolled: <span className="font-semibold text-text-primary">{d.student_count}</span></div>
                </div>
              </Card>
            ))}
          </div>
        </div>
      )}

      {/* TAB 3: CLASS GROUPS */}
      {activeTab === 'classes' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-text-primary">Class Cohorts & Sections</h3>
            <Button
              variant="primary"
              size="sm"
              icon={<PlusCircle className="w-4 h-4" />}
              onClick={() => setCreateClassModal(true)}
            >
              Add Class Cohort
            </Button>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {classes.map((c) => (
              <Card key={c.id} className="p-5 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-sm text-text-primary">
                    {c.department_name} — Year {c.year} ({c.section})
                  </span>
                  <Badge variant="neutral">Y{c.year}{c.section}</Badge>
                </div>
                <div className="space-y-1 text-xs text-text-muted">
                  <div>Faculty Advisor: <span className="font-semibold text-text-primary">{c.faculty_name}</span></div>
                  <div>Students: <span className="font-semibold text-text-primary">{c.student_count}</span></div>
                </div>
              </Card>
            ))}
          </div>
        </div>
      )}

      {/* TAB 4: ASSIGNMENTS */}
      {activeTab === 'assignments' && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Assign HOD */}
          <Card className="p-5 space-y-4">
            <h4 className="text-sm font-bold text-text-primary border-b border-border pb-2">Assign Department HOD</h4>
            <form onSubmit={handleAssignHod} className="space-y-3">
              <Select
                label="Department"
                value={assignHodForm.department_id}
                onChange={(e) => setAssignHodForm({ ...assignHodForm, department_id: e.target.value })}
                options={[
                  { value: '', label: 'Select Department...' },
                  ...departments.map((d) => ({ value: String(d.id), label: d.name }))
                ]}
              />
              <Select
                label="Select HOD User"
                value={assignHodForm.hod_user_id}
                onChange={(e) => setAssignHodForm({ ...assignHodForm, hod_user_id: e.target.value })}
                options={[
                  { value: '', label: 'Select HOD...' },
                  ...hodList.map((h) => ({ value: String(h.id), label: `${h.full_name} (@${h.username})` }))
                ]}
              />
              <Button type="submit" variant="primary" fullWidth isLoading={isSubmitting}>
                Save HOD Assignment
              </Button>
            </form>
          </Card>

          {/* Assign Faculty */}
          <Card className="p-5 space-y-4">
            <h4 className="text-sm font-bold text-text-primary border-b border-border pb-2">Assign Faculty Advisor</h4>
            <form onSubmit={handleAssignFaculty} className="space-y-3">
              <Select
                label="Class Cohort"
                value={assignFacultyForm.class_group_id}
                onChange={(e) => setAssignFacultyForm({ ...assignFacultyForm, class_group_id: e.target.value })}
                options={[
                  { value: '', label: 'Select Class...' },
                  ...classes.map((c) => ({ value: String(c.id), label: `${c.department_name} Y${c.year}${c.section}` }))
                ]}
              />
              <Select
                label="Select Faculty Member"
                value={assignFacultyForm.faculty_id}
                onChange={(e) => setAssignFacultyForm({ ...assignFacultyForm, faculty_id: e.target.value })}
                options={[
                  { value: '', label: 'Select Faculty...' },
                  ...facultyList.map((f) => ({ value: String(f.id), label: `${f.full_name} (@${f.username})` }))
                ]}
              />
              <Button type="submit" variant="primary" fullWidth isLoading={isSubmitting}>
                Save Faculty Advisor
              </Button>
            </form>
          </Card>

          {/* Assign Mentor */}
          <Card className="p-5 space-y-4">
            <h4 className="text-sm font-bold text-text-primary border-b border-border pb-2">Assign Student Mentor</h4>
            <form onSubmit={handleAssignMentor} className="space-y-3">
              <Select
                label="Select Mentor User"
                value={assignMentorForm.mentor_id}
                onChange={(e) => setAssignMentorForm({ ...assignMentorForm, mentor_id: e.target.value })}
                options={[
                  { value: '', label: 'Select Mentor...' },
                  ...mentorList.map((m) => ({ value: String(m.id), label: `${m.full_name} (@${m.username})` }))
                ]}
              />
              <div className="space-y-1">
                <label className="block text-xs font-semibold text-text-primary">Select Students to Assign</label>
                <div className="max-h-40 overflow-y-auto border border-border rounded-lg p-2 space-y-1 bg-bg text-xs">
                  {studentsList.map((st) => (
                    <label key={st.id} className="flex items-center gap-2 cursor-pointer hover:bg-surface-elevated p-1 rounded">
                      <input
                        type="checkbox"
                        checked={assignMentorForm.student_ids.includes(st.id)}
                        onChange={(e) => {
                          if (e.target.checked) {
                            setAssignMentorForm({ ...assignMentorForm, student_ids: [...assignMentorForm.student_ids, st.id] });
                          } else {
                            setAssignMentorForm({ ...assignMentorForm, student_ids: assignMentorForm.student_ids.filter((id) => id !== st.id) });
                          }
                        }}
                      />
                      <span>{st.full_name} (@{st.username})</span>
                    </label>
                  ))}
                </div>
              </div>
              <Button type="submit" variant="primary" fullWidth isLoading={isSubmitting}>
                Assign Selected Students
              </Button>
            </form>
          </Card>
        </div>
      )}

      {/* TAB 5: SYSTEM LEAVES */}
      {activeTab === 'leaves' && (
        <Card className="p-0 overflow-hidden space-y-0">
          <div className="p-4 border-b border-border flex items-center justify-between">
            <h3 className="text-sm font-bold text-text-primary">System-Wide Leave Registry</h3>
            <Button
              variant="danger"
              size="sm"
              icon={<Trash2 className="w-4 h-4" />}
              onClick={() => setClearLeavesModal(true)}
            >
              Clear All Leave Records
            </Button>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-border bg-surface-elevated/50 text-[11px] font-semibold text-text-muted uppercase">
                  <th className="py-3 px-4">Applicant</th>
                  <th className="py-3 px-4">Duration</th>
                  <th className="py-3 px-4">Reason</th>
                  <th className="py-3 px-4">Emergency</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4">Applied On</th>
                  <th className="py-3 px-4 text-right">Admin Override</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/40 text-xs">
                {leaves.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="py-8 text-center text-text-muted">No leave records in database.</td>
                  </tr>
                ) : (
                  leaves.map((l) => (
                    <tr key={l.id}>
                      <td className="py-3 px-4 font-semibold text-text-primary">{l.applicant}</td>
                      <td className="py-3 px-4 text-text-secondary">{l.start_date} to {l.end_date}</td>
                      <td className="py-3 px-4 text-text-muted">{l.reason}</td>
                      <td className="py-3 px-4">
                        {l.is_emergency ? <Badge variant="danger">YES</Badge> : <Badge variant="neutral">NO</Badge>}
                      </td>
                      <td className="py-3 px-4">
                        <Badge variant={l.status === 'APPROVED' ? 'success' : l.status === 'REJECTED' ? 'danger' : 'warning'}>
                          {l.status}
                        </Badge>
                      </td>
                      <td className="py-3 px-4 text-text-muted">{l.applied_on}</td>
                      <td className="py-3 px-4 text-right">
                        <div className="flex items-center justify-end gap-1.5">
                          <Button
                            variant="primary"
                            size="sm"
                            disabled={l.status === 'APPROVED'}
                            onClick={() => handleReviewLeaveOverride(l.id, 'APPROVE')}
                          >
                            Approve
                          </Button>
                          <Button
                            variant="danger"
                            size="sm"
                            disabled={l.status === 'REJECTED'}
                            onClick={() => handleReviewLeaveOverride(l.id, 'REJECT')}
                          >
                            Reject
                          </Button>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {/* TAB 6: SYSTEM ODS */}
      {activeTab === 'ods' && (
        <Card className="p-0 overflow-hidden space-y-0">
          <div className="p-4 border-b border-border flex items-center justify-between">
            <h3 className="text-sm font-bold text-text-primary">System-Wide OD Registry</h3>
            <Button
              variant="danger"
              size="sm"
              icon={<Trash2 className="w-4 h-4" />}
              onClick={() => setClearOdsModal(true)}
            >
              Clear All OD Records
            </Button>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-border bg-surface-elevated/50 text-[11px] font-semibold text-text-muted uppercase">
                  <th className="py-3 px-4">Applicant</th>
                  <th className="py-3 px-4">Event Date</th>
                  <th className="py-3 px-4">Reason</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4">Applied On</th>
                  <th className="py-3 px-4 text-right">Admin Override</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/40 text-xs">
                {ods.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="py-8 text-center text-text-muted">No OD records in database.</td>
                  </tr>
                ) : (
                  ods.map((o) => (
                    <tr key={o.id}>
                      <td className="py-3 px-4 font-semibold text-text-primary">{o.applicant}</td>
                      <td className="py-3 px-4 text-text-secondary">{o.event_date}</td>
                      <td className="py-3 px-4 text-text-muted">{o.reason}</td>
                      <td className="py-3 px-4">
                        <Badge variant={o.status === 'APPROVED' ? 'success' : o.status === 'REJECTED' ? 'danger' : 'warning'}>
                          {o.status}
                        </Badge>
                      </td>
                      <td className="py-3 px-4 text-text-muted">{o.applied_on}</td>
                      <td className="py-3 px-4 text-right">
                        <div className="flex items-center justify-end gap-1.5">
                          <Button
                            variant="primary"
                            size="sm"
                            disabled={o.status === 'APPROVED'}
                            onClick={() => handleReviewOdOverride(o.id, 'APPROVE')}
                          >
                            Approve
                          </Button>
                          <Button
                            variant="danger"
                            size="sm"
                            disabled={o.status === 'REJECTED'}
                            onClick={() => handleReviewOdOverride(o.id, 'REJECT')}
                          >
                            Reject
                          </Button>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {/* TAB 7: AUDIT LOGS & REPORTS */}
      {activeTab === 'logs' && (
        <Card className="p-0 overflow-hidden space-y-0">
          <div className="p-4 border-b border-border flex items-center justify-between">
            <div>
              <h3 className="text-sm font-bold text-text-primary">System Audit Logs & Report Exports</h3>
              <p className="text-xs text-text-muted">Real-time tracking of security events, administrative changes, and workflow decisions.</p>
            </div>
            <div className="flex items-center gap-2">
              <a
                href="/admin/reports?format=csv"
                target="_blank"
                rel="noreferrer"
                className="px-3 py-1.5 bg-surface-elevated border border-border text-xs font-semibold rounded-lg hover:text-primary transition-colors inline-flex items-center gap-1.5"
              >
                Export CSV Report
              </a>
              <a
                href="/admin/reports?format=pdf"
                target="_blank"
                rel="noreferrer"
                className="px-3 py-1.5 bg-primary text-[#07151F] text-xs font-bold rounded-lg hover:opacity-90 transition-colors inline-flex items-center gap-1.5"
              >
                Export PDF Report
              </a>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-border bg-surface-elevated/50 text-[11px] font-semibold text-text-muted uppercase">
                  <th className="py-3 px-4">Timestamp</th>
                  <th className="py-3 px-4">Actor</th>
                  <th className="py-3 px-4">Action</th>
                  <th className="py-3 px-4">Target Type</th>
                  <th className="py-3 px-4">IP Address</th>
                  <th className="py-3 px-4">Details</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/40 text-xs font-mono">
                {auditLogs.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="py-8 text-center text-text-muted font-sans">No audit log events recorded.</td>
                  </tr>
                ) : (
                  auditLogs.map((log) => (
                    <tr key={log.id} className="hover:bg-surface-elevated/30 transition-colors">
                      <td className="py-3 px-4 text-text-muted whitespace-nowrap">{log.timestamp}</td>
                      <td className="py-3 px-4 font-semibold text-primary font-sans">{log.actor}</td>
                      <td className="py-3 px-4 font-bold text-text-primary">{log.action}</td>
                      <td className="py-3 px-4 text-text-secondary">{log.target_type} {log.target_id ? `#${log.target_id}` : ''}</td>
                      <td className="py-3 px-4 text-text-muted">{log.ip_address}</td>
                      <td className="py-3 px-4 text-text-secondary font-sans max-w-xs truncate">{log.details || '—'}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {/* MODAL: Create User */}
      <Modal
        isOpen={createUserModal}
        onClose={() => setCreateUserModal(false)}
        title="Create New User Account"
        description="Fill in user details and assign role parameters."
      >
        <form onSubmit={handleCreateUser} className="space-y-3">
          <Input label="Full Name" required value={newUser.full_name} onChange={(e) => setNewUser({ ...newUser, full_name: e.target.value })} />
          <Input label="Username" required value={newUser.username} onChange={(e) => setNewUser({ ...newUser, username: e.target.value })} />
          <Input label="Email" type="email" required value={newUser.email} onChange={(e) => setNewUser({ ...newUser, email: e.target.value })} />
          <Input label="Password" type="password" required value={newUser.password} onChange={(e) => setNewUser({ ...newUser, password: e.target.value })} />
          
          <Select
            label="Assign Role"
            value={newUser.role}
            onChange={(e) => setNewUser({ ...newUser, role: e.target.value })}
            options={[
              { value: 'student', label: 'Student' },
              { value: 'faculty', label: 'Faculty' },
              { value: 'mentor', label: 'Mentor' },
              { value: 'hod', label: 'HOD' },
              { value: 'admin', label: 'Admin' },
              { value: 'event_coordinator', label: 'Event Coordinator' }
            ]}
          />

          <Select
            label="Department Assignment"
            value={newUser.department_id}
            onChange={(e) => setNewUser({ ...newUser, department_id: e.target.value })}
            options={[
              { value: '', label: 'None' },
              ...departments.map((d) => ({ value: String(d.id), label: d.name }))
            ]}
          />

          {newUser.role === 'student' && (
            <>
              <Select
                label="Class Group"
                value={newUser.class_group_id}
                onChange={(e) => setNewUser({ ...newUser, class_group_id: e.target.value })}
                options={[
                  { value: '', label: 'Select Class...' },
                  ...classes.map((c) => ({ value: String(c.id), label: `${c.department_name} Y${c.year}${c.section}` }))
                ]}
              />
              <Input label="Register Number" required value={newUser.register_number} onChange={(e) => setNewUser({ ...newUser, register_number: e.target.value })} />
              <Input label="Date of Birth (YYYY-MM-DD)" type="date" required value={newUser.date_of_birth} onChange={(e) => setNewUser({ ...newUser, date_of_birth: e.target.value })} />
              <Input label="Father's Name" required value={newUser.father_name} onChange={(e) => setNewUser({ ...newUser, father_name: e.target.value })} />
            </>
          )}

          <div className="flex justify-end gap-2 pt-3 border-t border-border">
            <Button variant="ghost" type="button" onClick={() => setCreateUserModal(false)}>Cancel</Button>
            <Button variant="primary" type="submit" isLoading={isSubmitting}>Create User Account</Button>
          </div>
        </form>
      </Modal>

      {/* MODAL: Create Department */}
      <Modal
        isOpen={createDeptModal}
        onClose={() => setCreateDeptModal(false)}
        title="Create Academic Department"
        description="Add a new academic department to the system registry."
      >
        <form onSubmit={handleCreateDept} className="space-y-4">
          <Input label="Department Name" required placeholder="e.g. Mechanical Engineering" value={newDeptName} onChange={(e) => setNewDeptName(e.target.value)} />
          <div className="flex justify-end gap-2 pt-3 border-t border-border">
            <Button variant="ghost" type="button" onClick={() => setCreateDeptModal(false)}>Cancel</Button>
            <Button variant="primary" type="submit" isLoading={isSubmitting}>Create Department</Button>
          </div>
        </form>
      </Modal>

      {/* MODAL: Create Class */}
      <Modal
        isOpen={createClassModal}
        onClose={() => setCreateClassModal(false)}
        title="Create Class Cohort"
        description="Define a new student cohort by department, year, and section."
      >
        <form onSubmit={handleCreateClass} className="space-y-3">
          <Select
            label="Department"
            value={newClass.department_id}
            onChange={(e) => setNewClass({ ...newClass, department_id: e.target.value })}
            options={[
              { value: '', label: 'Select Department...' },
              ...departments.map((d) => ({ value: String(d.id), label: d.name }))
            ]}
          />
          <Select
            label="Academic Year"
            value={newClass.year}
            onChange={(e) => setNewClass({ ...newClass, year: e.target.value })}
            options={[
              { value: '1', label: 'Year 1' },
              { value: '2', label: 'Year 2' },
              { value: '3', label: 'Year 3' },
              { value: '4', label: 'Year 4' }
            ]}
          />
          <Input label="Section" required placeholder="e.g. A, B, C" value={newClass.section} onChange={(e) => setNewClass({ ...newClass, section: e.target.value })} />
          <div className="flex justify-end gap-2 pt-3 border-t border-border">
            <Button variant="ghost" type="button" onClick={() => setCreateClassModal(false)}>Cancel</Button>
            <Button variant="primary" type="submit" isLoading={isSubmitting}>Create Class Cohort</Button>
          </div>
        </form>
      </Modal>

      {/* MODAL: Delete User Confirmation */}
      <Modal
        isOpen={!!deleteUserModal}
        onClose={() => setDeleteUserModal(null)}
        title="Confirm User Deletion"
        description="Are you sure you want to delete this user?"
      >
        {deleteUserModal && (
          <div className="space-y-4">
            <Alert type="warning" title="Irreversible Action">
              Deleting user <strong>{deleteUserModal.full_name} (@{deleteUserModal.username})</strong> will remove associated leave and OD records while restoring student leave balances.
            </Alert>
            <div className="flex justify-end gap-2 pt-3 border-t border-border">
              <Button variant="ghost" onClick={() => setDeleteUserModal(null)}>Cancel</Button>
              <Button variant="danger" onClick={handleDeleteUser} isLoading={isSubmitting}>Delete Account</Button>
            </div>
          </div>
        )}
      </Modal>

      {/* MODAL: Clear Leaves Confirmation */}
      <Modal
        isOpen={clearLeavesModal}
        onClose={() => setClearLeavesModal(false)}
        title="Clear All System Leaves"
        description="Wipe all leave records from database."
      >
        <div className="space-y-4">
          <Alert type="danger" title="Warning">
            This action will permanently delete all leave records and restore student leave balances.
          </Alert>
          <div className="flex justify-end gap-2 pt-3 border-t border-border">
            <Button variant="ghost" onClick={() => setClearLeavesModal(false)}>Cancel</Button>
            <Button variant="danger" onClick={handleClearLeaves} isLoading={isSubmitting}>Confirm Clear All</Button>
          </div>
        </div>
      </Modal>

      {/* MODAL: Clear ODs Confirmation */}
      <Modal
        isOpen={clearOdsModal}
        onClose={() => setClearOdsModal(false)}
        title="Clear All System ODs"
        description="Wipe all OD records from database."
      >
        <div className="space-y-4">
          <Alert type="danger" title="Warning">
            This action will permanently delete all OD records across all departments.
          </Alert>
          <div className="flex justify-end gap-2 pt-3 border-t border-border">
            <Button variant="ghost" onClick={() => setClearOdsModal(false)}>Cancel</Button>
            <Button variant="danger" onClick={handleClearOds} isLoading={isSubmitting}>Confirm Clear All</Button>
          </div>
        </div>
      </Modal>

      {toastMsg && (
        <div className="fixed bottom-6 right-6 z-50">
          <Toast type="success" title="Admin Notice" message={toastMsg} onDismiss={() => setToastMsg(null)} />
        </div>
      )}
    </div>
  );
};
