import React, { useState } from 'react';
import { Briefcase, ArrowLeft } from 'lucide-react';
import {
  Button,
  Card,
  Input,
  Textarea,
  FileUpload,
  Alert,
  PageHeader,
  Toast
} from '../components/ui';

export const ApplyOdPage: React.FC<{
  onBack?: () => void;
  onSuccess?: () => void;
}> = ({ onBack, onSuccess }) => {
  const [eventTitle, setEventTitle] = useState('');
  const [eventDate, setEventDate] = useState('');
  const [purpose, setPurpose] = useState('');
  const [proofFile, setProofFile] = useState<File | null>(null);

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [toastMsg, setToastMsg] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);

    if (!eventTitle.trim()) {
      setErrorMsg('Please enter the event name/title.');
      return;
    }

    if (!eventDate) {
      setErrorMsg('Please select the event date.');
      return;
    }

    if (!purpose.trim()) {
      setErrorMsg('Please detail your participation purpose and role.');
      return;
    }

    setIsSubmitting(true);

    try {
      const { odApi } = await import('../api/od');
      await odApi.createOd({
        event_date: eventDate,
        reason: `${eventTitle.trim()}: ${purpose.trim()}`,
        proof: proofFile,
      });
      setIsSubmitting(false);
      setToastMsg('OD request submitted successfully for review!');
      if (onSuccess) setTimeout(onSuccess, 1500);
    } catch (err: any) {
      setIsSubmitting(false);
      setErrorMsg(err.message || 'Failed to submit OD request.');
    }
  };

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      {/* Page Header */}
      <PageHeader
        title="Apply for On Duty (OD)"
        subtitle="Submit official On Duty application for college event participation."
        actions={
          <Button
            variant="ghost"
            icon={<ArrowLeft className="w-4 h-4" />}
            onClick={onBack || (() => window.location.href = '/my-ods')}
          >
            Back to My ODs
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
          <Input
            label="Event Name / Title"
            placeholder="e.g. Inter-College Hackathon 2026 / IEEE Symposium"
            value={eventTitle}
            onChange={(e) => setEventTitle(e.target.value)}
            required
          />

          <Input
            label="Event Date"
            type="date"
            value={eventDate}
            onChange={(e) => setEventDate(e.target.value)}
            required
          />

          <Textarea
            label="Participation Purpose & Role"
            placeholder="Detail your role, paper title, or competition team..."
            rows={4}
            value={purpose}
            onChange={(e) => setPurpose(e.target.value)}
            required
          />

          <FileUpload
            label="Upload Event Pass / Invitation Brochure (Proof)"
            helperText="Accepted formats: PNG, JPG, PDF up to 10MB"
            onFileSelect={(file) => setProofFile(file)}
          />

          <div className="flex items-center justify-end gap-3 pt-4 border-t border-border">
            <Button
              type="button"
              variant="ghost"
              onClick={onBack || (() => window.location.href = '/my-ods')}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              variant="primary"
              isLoading={isSubmitting}
            >
              Submit OD Application
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
