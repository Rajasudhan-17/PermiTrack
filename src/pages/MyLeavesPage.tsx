import React, { useState, useEffect } from 'react';
import { Calendar, PlusCircle, Search, Filter, Eye, Clock, FileText } from 'lucide-react';
import {
  Button,
  Card,
  Input,
  Select,
  StatusBadge,
  Badge,
  PageHeader,
  EmptyState,
  Modal,
  Toast,
  FileUpload
} from '../components/ui';
import { getAuthenticatedUrl } from '../api/client';
import { leavesApi, LeaveApiItem } from '../api/leaves';

export interface LeaveRecord {
  id: string;
  numericId: number;
  startDate: string;
  endDate: string;
  totalDays: number;
  type: string;
  reason: string;
  appliedOn: string;
  status: 'APPROVED' | 'PENDING' | 'REJECTED' | 'UNDER_REVIEW';
  approvalStage: string;
  proofDocument?: string;
  reviewComment?: string;
  hasProof?: boolean;
  proofUrl?: string | null;
}

export const MyLeavesPage: React.FC<{
  onApplyLeaveClick?: () => void;
  onViewDetailsClick?: (leave: LeaveRecord) => void;
}> = ({ onApplyLeaveClick, onViewDetailsClick }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [selectedLeave, setSelectedLeave] = useState<LeaveRecord | null>(null);
  const [leaves, setLeaves] = useState<LeaveRecord[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    leavesApi.getLeaves()
      .then((data: LeaveApiItem[]) => {
        const mapped: LeaveRecord[] = data.map((item) => {
          const s = new Date(item.start_date);
          const e = new Date(item.end_date);
          const diffDays = Math.max(1, Math.ceil(Math.abs(e.getTime() - s.getTime()) / (1000 * 60 * 60 * 24)) + 1);
          return {
            id: `L-${item.id}`,
            numericId: item.id,
            startDate: item.start_date,
            endDate: item.end_date,
            totalDays: diffDays,
            type: item.is_emergency ? 'Emergency Leave' : 'Academic Leave',
            reason: item.reason,
            appliedOn: item.applied_on || 'N/A',
            status: (item.status as any) || 'PENDING',
            approvalStage: `Stage: ${item.status}`,
            reviewComment: item.review_comment,
            hasProof: item.has_proof,
            proofUrl: item.proof_url,
          };
        });
        setLeaves(mapped);
      })
      .catch((err) => console.error('Failed to load leaves:', err))
      .finally(() => setLoading(false));
  }, []);

  const filteredLeaves = leaves.filter((leave) => {
    const matchesSearch = leave.reason.toLowerCase().includes(searchTerm.toLowerCase()) ||
                          leave.id.toLowerCase().includes(searchTerm.toLowerCase()) ||
                          leave.type.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesStatus = statusFilter === 'ALL' || leave.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <PageHeader
        title="My Leave Applications"
        subtitle="Manage and track your submitted academic leave applications."
        badge={<Badge variant="primary">{leaves.length} Total Requests</Badge>}
        actions={
          <Button
            variant="primary"
            icon={<PlusCircle className="w-4 h-4" />}
            onClick={onApplyLeaveClick || (() => window.location.href = '/apply-leave')}
          >
            Apply New Leave
          </Button>
        }
      />

      {/* Search & Filters Controls */}
      <Card className="p-4">
        <div className="flex flex-col sm:flex-row items-center gap-4 justify-between">
          <div className="w-full sm:w-72">
            <Input
              placeholder="Search by reason, ID, or type..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              leftIcon={<Search className="w-4 h-4" />}
            />
          </div>
          <div className="w-full sm:w-48 flex items-center gap-2">
            <Filter className="w-4 h-4 text-text-muted shrink-0" />
            <Select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              options={[
                { value: 'ALL', label: 'All Statuses' },
                { value: 'APPROVED', label: 'Approved' },
                { value: 'PENDING', label: 'Pending' },
                { value: 'REJECTED', label: 'Rejected' },
              ]}
            />
          </div>
        </div>
      </Card>

      {/* Leaves Content */}
      {filteredLeaves.length === 0 ? (
        <EmptyState
          title="No Leave Records Found"
          description="No leave applications match your search or filter criteria."
          action={{
            label: "Apply for Leave",
            onClick: onApplyLeaveClick || (() => window.location.href = '/apply-leave'),
            icon: <PlusCircle className="w-4 h-4" />
          }}
        />
      ) : (
        <>
          {/* Desktop Table */}
          <Card className="hidden md:block overflow-hidden p-0">
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b border-border bg-surface-elevated/40 text-[11px] font-semibold text-text-muted uppercase tracking-wider">
                    <th className="py-3 px-4">Request ID</th>
                    <th className="py-3 px-4">Category</th>
                    <th className="py-3 px-4">Duration</th>
                    <th className="py-3 px-4">Reason / Subject</th>
                    <th className="py-3 px-4">Applied On</th>
                    <th className="py-3 px-4">Status</th>
                    <th className="py-3 px-4 text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/40 text-xs">
                  {filteredLeaves.map((leave) => (
                    <tr key={leave.id} className="hover:bg-surface-elevated/30 transition-colors">
                      <td className="py-3.5 px-4 font-mono font-bold text-primary">{leave.id}</td>
                      <td className="py-3.5 px-4 font-medium text-text-primary">{leave.type}</td>
                      <td className="py-3.5 px-4 text-text-secondary whitespace-nowrap">
                        {leave.startDate} {leave.startDate !== leave.endDate ? `to ${leave.endDate}` : ''} ({leave.totalDays} day{leave.totalDays > 1 ? 's' : ''})
                      </td>
                      <td className="py-3.5 px-4 text-text-secondary max-w-xs truncate">{leave.reason}</td>
                      <td className="py-3.5 px-4 text-text-muted whitespace-nowrap">{leave.appliedOn}</td>
                      <td className="py-3.5 px-4">
                        <StatusBadge status={leave.status} size="sm" />
                      </td>
                      <td className="py-3.5 px-4 text-right">
                        <Button
                          variant="ghost"
                          size="sm"
                          icon={<Eye className="w-3.5 h-3.5" />}
                          onClick={() => setSelectedLeave(leave)}
                        >
                          Details
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>

          {/* Mobile Card List */}
          <div className="grid grid-cols-1 gap-4 md:hidden">
            {filteredLeaves.map((leave) => (
              <Card key={leave.id} className="p-4 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="font-mono font-bold text-sm text-primary">{leave.id}</span>
                  <StatusBadge status={leave.status} size="sm" />
                </div>
                <div>
                  <h4 className="text-sm font-semibold text-text-primary">{leave.type}</h4>
                  <p className="text-xs text-text-secondary line-clamp-2 mt-0.5">{leave.reason}</p>
                </div>
                <div className="flex items-center justify-between text-xs text-text-muted pt-2 border-t border-border/50">
                  <span>{leave.startDate} ({leave.totalDays}d)</span>
                  <Button
                    variant="ghost"
                    size="sm"
                    icon={<Eye className="w-3.5 h-3.5" />}
                    onClick={() => setSelectedLeave(leave)}
                  >
                    View Details
                  </Button>
                </div>
              </Card>
            ))}
          </div>
        </>
      )}

      {/* Leave Detail Modal */}
      {selectedLeave && (
        <Modal
          isOpen={Boolean(selectedLeave)}
          onClose={() => setSelectedLeave(null)}
          title={`Leave Request Details — ${selectedLeave.id}`}
          description={`Applied on ${selectedLeave.appliedOn}`}
          footer={
            <Button variant="secondary" onClick={() => setSelectedLeave(null)}>
              Close
            </Button>
          }
        >
          <div className="space-y-4 text-xs sm:text-sm">
            <div className="grid grid-cols-2 gap-4 p-3 bg-bg-secondary rounded-lg border border-border">
              <div>
                <span className="text-text-muted block text-xs">Status:</span>
                <StatusBadge status={selectedLeave.status} size="sm" className="mt-1" />
              </div>
              <div>
                <span className="text-text-muted block text-xs">Category:</span>
                <span className="font-semibold text-text-primary">{selectedLeave.type}</span>
              </div>
              <div>
                <span className="text-text-muted block text-xs">Start Date:</span>
                <span className="font-medium text-text-primary">{selectedLeave.startDate}</span>
              </div>
              <div>
                <span className="text-text-muted block text-xs">End Date:</span>
                <span className="font-medium text-text-primary">{selectedLeave.endDate}</span>
              </div>
            </div>

            <div>
              <span className="text-text-muted block text-xs font-medium mb-1">Reason Description:</span>
              <p className="p-3 bg-surface-elevated rounded-lg border border-border text-text-primary leading-relaxed">
                {selectedLeave.reason}
              </p>
            </div>

            <div>
              <span className="text-text-muted block text-xs font-medium mb-1">Approval Stage:</span>
              <div className="p-2.5 bg-primary-subtle text-primary rounded-lg border border-primary/20 font-medium">
                {selectedLeave.approvalStage}
              </div>
            </div>

            {selectedLeave.hasProof ? (
              <div>
                <span className="text-text-muted block text-xs font-medium mb-1">Supporting Proof Document:</span>
                <a
                  href={getAuthenticatedUrl(selectedLeave.proofUrl || `/api/v1/leaves/${selectedLeave.numericId}/proof`)}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-2 px-3 py-2 bg-primary/10 text-primary border border-primary/30 rounded-lg text-xs font-medium hover:bg-primary/20 transition-colors"
                >
                  <FileText className="w-4 h-4" />
                  View Attached Proof Document
                </a>
              </div>
            ) : (
              <div>
                <span className="text-text-muted block text-xs font-medium mb-1">Upload Supporting Proof Document:</span>
                <FileUpload
                  label="Attach medical proof or supporting document"
                  helperText="Accepted formats: PNG, JPG, PDF up to 10MB"
                  onFileSelect={async (file) => {
                    if (!file) return;
                    try {
                      await leavesApi.uploadProof(selectedLeave.numericId, file);
                      const proofUrl = `/api/v1/leaves/${selectedLeave.numericId}/proof`;
                      setSelectedLeave({
                        ...selectedLeave,
                        hasProof: true,
                        proofUrl,
                      });
                      setLeaves((prev) =>
                        prev.map((l) =>
                          l.numericId === selectedLeave.numericId ? { ...l, hasProof: true, proofUrl } : l
                        )
                      );
                    } catch (err: any) {
                      alert(err.message || 'Failed to upload proof document');
                    }
                  }}
                />
              </div>
            )}

            {selectedLeave.reviewComment && (
              <div>
                <span className="text-text-muted block text-xs font-medium mb-1">Faculty / Mentor Review Comment:</span>
                <div className="p-3 bg-bg-secondary rounded-lg border border-border text-text-secondary italic">
                  "{selectedLeave.reviewComment}"
                </div>
              </div>
            )}
          </div>
        </Modal>
      )}
    </div>
  );
};
