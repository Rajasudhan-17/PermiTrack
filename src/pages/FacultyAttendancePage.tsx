import React, { useState, useEffect } from 'react';
import { Save, RefreshCw, AlertCircle, Calendar } from 'lucide-react';
import {
  Button,
  Card,
  Input,
  Select,
  Badge,
  PageHeader,
  Alert,
  Toast
} from '../components/ui';
import { attendanceApi, ClassGroupOption, AttendanceSheetItem } from '../api/profile';

export const FacultyAttendancePage: React.FC = () => {
  const [classGroups, setClassGroups] = useState<ClassGroupOption[]>([]);
  const [selectedClassId, setSelectedClassId] = useState<string>('');
  const [targetDate, setTargetDate] = useState<string>(new Date().toISOString().split('T')[0]);
  
  const [students, setStudents] = useState<AttendanceSheetItem[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isSaving, setIsSaving] = useState<boolean>(false);
  
  const [toastMsg, setToastMsg] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Load assigned class groups on mount
  useEffect(() => {
    const loadClasses = async () => {
      try {
        const res = await attendanceApi.getClassGroups();
        setClassGroups(res.class_groups);
        if (res.class_groups.length > 0) {
          setSelectedClassId(String(res.class_groups[0].id));
        }
      } catch (err: any) {
        setErrorMsg(err.message || 'Failed to fetch assigned class groups.');
      } finally {
        setIsLoading(false);
      }
    };

    loadClasses();
  }, []);

  // Fetch attendance sheet whenever selected class or date changes
  const loadAttendanceSheet = async () => {
    if (!selectedClassId) return;
    setIsLoading(true);
    setErrorMsg(null);
    try {
      const res = await attendanceApi.getAttendanceSheet(Number(selectedClassId), targetDate);
      setStudents(res.sheet);
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to fetch student roster for selected class.');
      setStudents([]);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (selectedClassId) {
      loadAttendanceSheet();
    }
  }, [selectedClassId, targetDate]);

  const handleStatusChange = (studentId: number, status: 'PRESENT' | 'ABSENT' | 'LEAVE' | 'OD') => {
    setStudents((prev) =>
      prev.map((s) => (s.student_id === studentId ? { ...s, status } : s))
    );
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedClassId || students.length === 0) return;
    setIsSaving(true);
    setErrorMsg(null);
    try {
      const recordsPayload = students.map((s) => ({
        student_id: s.student_id,
        status: s.status,
        reason: s.reason,
        leave_id: s.leave_id,
        od_id: s.od_id
      }));

      const res = await attendanceApi.saveAttendance(Number(selectedClassId), targetDate, recordsPayload);
      setToastMsg(res.message);
      await loadAttendanceSheet();
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to save attendance records.');
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <PageHeader
        title="Attendance Management & Marking"
        subtitle="Select a class group and mark daily working day attendance or record approved attendance updates."
        badge={<Badge variant="primary" className="font-semibold">ATTENDANCE CONTROL</Badge>}
        actions={
          <Button
            variant="outline"
            size="sm"
            icon={<RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />}
            onClick={loadAttendanceSheet}
            disabled={!selectedClassId}
          >
            Refresh Roster
          </Button>
        }
      />

      {errorMsg && (
        <Alert type="danger" title="Attendance Error">
          {errorMsg}
        </Alert>
      )}

      {/* No Class Assigned Warning */}
      {!isLoading && classGroups.length === 0 && (
        <Alert type="warning" title="No Class Groups Available">
          No class groups were found for attendance logging. If you are an Administrator, please ensure class groups are created in Admin Tools.
        </Alert>
      )}

      {/* Class Selection Controls */}
      {classGroups.length > 0 && (
        <Card className="p-4 sm:p-6 space-y-6">
          <form onSubmit={handleSave} className="space-y-6">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <Select
                label="Select Assigned Class Cohort"
                value={selectedClassId}
                onChange={(e) => setSelectedClassId(e.target.value)}
                options={classGroups.map((cg) => ({
                  value: String(cg.id),
                  label: `${cg.department} — Year ${cg.year} (Section ${cg.section})`
                }))}
              />
              <Input
                label="Attendance Date"
                type="date"
                value={targetDate}
                onChange={(e) => setTargetDate(e.target.value)}
                required
              />
            </div>

            {/* Student Roster Table */}
            <div className="overflow-x-auto border border-border rounded-lg">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b border-border bg-surface-elevated/40 text-[11px] font-semibold text-text-muted uppercase tracking-wider">
                    <th className="py-3 px-4">Register / Roll No</th>
                    <th className="py-3 px-4">Student Name</th>
                    <th className="py-3 px-4">Attendance Status</th>
                    <th className="py-3 px-4">Approved Leave / Remarks</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/40 text-xs">
                  {isLoading ? (
                    <tr>
                      <td colSpan={4} className="py-8 text-center text-text-muted">
                        Loading class student roster...
                      </td>
                    </tr>
                  ) : students.length === 0 ? (
                    <tr>
                      <td colSpan={4} className="py-8 text-center text-text-muted">
                        No students enrolled in this class group.
                      </td>
                    </tr>
                  ) : (
                    students.map((student) => (
                      <tr key={student.student_id} className="hover:bg-surface-elevated/30 transition-colors">
                        <td className="py-3 px-4 font-mono font-bold text-primary">{student.roll_number}</td>
                        <td className="py-3 px-4 font-semibold text-text-primary">{student.name}</td>
                        <td className="py-3 px-4">
                          <div className="flex items-center gap-1.5">
                            <button
                              type="button"
                              onClick={() => handleStatusChange(student.student_id, 'PRESENT')}
                              className={`px-2.5 py-1 rounded text-[11px] font-bold transition-colors ${
                                student.status === 'PRESENT'
                                  ? 'bg-success text-[#07151F]'
                                  : 'bg-surface-elevated text-text-muted hover:text-text-primary'
                              }`}
                            >
                              PRESENT
                            </button>
                            <button
                              type="button"
                              onClick={() => handleStatusChange(student.student_id, 'ABSENT')}
                              className={`px-2.5 py-1 rounded text-[11px] font-bold transition-colors ${
                                student.status === 'ABSENT'
                                  ? 'bg-danger text-white'
                                  : 'bg-surface-elevated text-text-muted hover:text-text-primary'
                              }`}
                            >
                              ABSENT
                            </button>
                            <button
                              type="button"
                              onClick={() => handleStatusChange(student.student_id, 'LEAVE')}
                              className={`px-2.5 py-1 rounded text-[11px] font-bold transition-colors ${
                                student.status === 'LEAVE'
                                  ? 'bg-warning text-[#07151F]'
                                  : 'bg-surface-elevated text-text-muted hover:text-text-primary'
                              }`}
                            >
                              LEAVE
                            </button>
                            <button
                              type="button"
                              onClick={() => handleStatusChange(student.student_id, 'OD')}
                              className={`px-2.5 py-1 rounded text-[11px] font-bold transition-colors ${
                                student.status === 'OD'
                                  ? 'bg-info text-[#07151F]'
                                  : 'bg-surface-elevated text-text-muted hover:text-text-primary'
                              }`}
                            >
                              OD
                            </button>
                          </div>
                        </td>
                        <td className="py-3 px-4 text-text-muted">
                          {student.is_auto ? (
                            <div className="flex items-center gap-1.5">
                              <Badge variant={student.status === 'LEAVE' ? 'warning' : 'info'}>
                                {student.status}
                              </Badge>
                              <span className="text-text-primary text-[11px] font-medium">{student.reason}</span>
                            </div>
                          ) : (
                            student.reason || '—'
                          )}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>

            <div className="flex justify-end">
              <Button
                variant="primary"
                type="submit"
                isLoading={isSaving}
                disabled={isLoading || students.length === 0}
                icon={<Save className="w-4 h-4" />}
              >
                Save Class Attendance
              </Button>
            </div>
          </form>
        </Card>
      )}

      {toastMsg && (
        <div className="fixed bottom-6 right-6 z-50">
          <Toast
            type="success"
            title="Attendance Recorded"
            message={toastMsg}
            onDismiss={() => setToastMsg(null)}
          />
        </div>
      )}
    </div>
  );
};
