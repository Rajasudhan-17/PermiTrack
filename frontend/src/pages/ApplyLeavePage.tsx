import React, { useState } from 'react';
import { Calendar, UploadCloud, AlertCircle, ArrowLeft, CheckCircle2 } from 'lucide-react';
import {
  Button,
  Card,
  Input,
  Select,
  Textarea,
  FileUpload,
  Alert,
  PageHeader,
  Toast
} from '../components/ui';

export const ApplyLeavePage: React.FC<{
  onBack?: () => void;
  onSuccess?: () => void;
}> = ({ onBack, onSuccess }) => {
  const [leaveType, setLeaveType] = useState('medical');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [reason, setReason] = useState('');
  const [proofFile, setProofFile] = useState<File | null>(null);
  
  const [isEmergency, setIsEmergency] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [toastMsg, setToastMsg] = useState<string | null>(null);

  const calculateDays = () => {
    if (!startDate || !endDate) return 0;
    const s = new Date(startDate);
    const e = new Date(endDate);
    if (e < s) return -1;
    const diffTime = Math.abs(e.getTime() - s.getTime());
    return Math.ceil(diffTime / (1000 * 60 * 60 * 24)) + 1;
  };

  const durationDays = calculateDays();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);

    if (!startDate || !endDate) {
      setErrorMsg('Please select valid start and end dates.');
      return;
    }

    if (durationDays <= 0) {
      setErrorMsg('End date cannot be prior to start date.');
      return;
    }

    if (!reason.trim()) {
      setErrorMsg('Please enter a detailed reason for leave application.');
      return;
    }

    setIsSubmitting(true);

    try {
      const { leavesApi } = await import('../api/leaves');
      await leavesApi.createLeave({
        start_date: startDate,
        end_date: endDate,
        reason,
        is_emergency: isEmergency,
        proof: proofFile,
      });
      setIsSubmitting(false);
      setToastMsg('Leave application submitted successfully for review!');
      if (onSuccess) setTimeout(onSuccess, 1500);
    } catch (err: any) {
      setIsSubmitting(false);
      setErrorMsg(err.message || 'Failed to submit leave request.');
    }
  };

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      {/* Page Header */}
      <PageHeader
        title="Apply for Academic Leave"
        subtitle="Submit your leave application for mentor, faculty, and HOD approval."
        actions={
          <Button
            variant="ghost"
            icon={<ArrowLeft className="w-4 h-4" />}
            onClick={onBack || (() => window.location.href = '/my-leaves')}
          >
            Back to My Leaves
          </Button>
        }
      />

      {errorMsg && (
        <Alert type="danger" title="Validation Error" onClose={() => setErrorMsg(null)}>
          {errorMsg}
        </Alert>
      )}

      {/* Main Form Card */}
      <Card className="p-6 sm:p-8">
        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
            <Select
              label="Leave Category"
              value={leaveType}
              onChange={(e) => setLeaveType(e.target.value)}
              options={[
                { value: 'medical', label: 'Medical Leave (Requires Proof if 2+ days)' },
                { value: 'casual', label: 'Casual Leave (CL)' },
                { value: 'special', label: 'Special OD / Academic Leave' },
                { value: 'emergency', label: 'Emergency Leave' },
              ]}
            />

            <div className="flex items-center gap-3 pt-6">
              <input
                type="checkbox"
                id="emergency-checkbox"
                checked={isEmergency}
                onChange={(e) => setIsEmergency(e.target.checked)}
                className="w-4 h-4 text-primary bg-bg-secondary border-border rounded focus:ring-primary/40 cursor-pointer"
              />
              <label htmlFor="emergency-checkbox" className="text-xs font-semibold text-text-primary cursor-pointer select-none">
                Mark as Emergency Leave (High Priority Route)
              </label>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
            <Input
              label="Start Date"
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              required
            />
            <Input
              label="End Date"
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              required
            />
          </div>

          {/* Duration Banner */}
          {durationDays > 0 && (
            <div className="p-3 bg-primary-subtle border border-primary/30 rounded-lg flex items-center justify-between text-xs text-primary font-medium">
              <span>Calculated Leave Duration:</span>
              <span className="font-bold text-sm font-display">{durationDays} Working Day{durationDays > 1 ? 's' : ''}</span>
            </div>
          )}

          <Textarea
            label="Detailed Reason for Application"
            placeholder="Explain the reason clearly for mentor verification..."
            rows={4}
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            required
          />

          <FileUpload
            label="Upload Medical Certificate / Supporting Document (Optional)"
            helperText="Accepted formats: PNG, JPG, PDF up to 10MB"
            onFileSelect={(file) => setProofFile(file)}
          />

          <div className="flex items-center justify-end gap-3 pt-4 border-t border-border">
            <Button
              type="button"
              variant="ghost"
              onClick={onBack || (() => window.location.href = '/my-leaves')}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              variant="primary"
              isLoading={isSubmitting}
            >
              Submit Leave Application
            </Button>
          </div>
        </form>
      </Card>

      {toastMsg && (
        <div className="fixed bottom-6 right-6 z-50">
          <Toast
            type="success"
            title="Success"
            message={toastMsg}
            onDismiss={() => setToastMsg(null)}
          />
        </div>
      )}
    </div>
  );
};
