import React, { useState, useEffect } from 'react';
import { Briefcase, PlusCircle, Search, Filter, Eye, FileText } from 'lucide-react';
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
  FileUpload
} from '../components/ui';
import { getAuthenticatedUrl } from '../api/client';
import { odApi, OdApiItem } from '../api/od';

export interface OdRecord {
  id: string;
  numericId: number;
  eventTitle: string;
  eventDate: string;
  purpose: string;
  appliedOn: string;
  status: 'APPROVED' | 'PENDING' | 'REJECTED' | 'UNDER_REVIEW';
  approvalStage: string;
  proofDocument?: string;
  reviewComment?: string;
  hasProof?: boolean;
  proofUrl?: string | null;
}

export const MyOdsPage: React.FC<{
  onApplyOdClick?: () => void;
}> = ({ onApplyOdClick }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [selectedOd, setSelectedOd] = useState<OdRecord | null>(null);
  const [ods, setOds] = useState<OdRecord[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    odApi.getOds()
      .then((data: OdApiItem[]) => {
        const mapped: OdRecord[] = data.map((item) => ({
          id: `OD-${item.id}`,
          numericId: item.id,
          eventTitle: item.reason.includes(':') ? item.reason.split(':')[0] : 'Academic On Duty',
          eventDate: item.event_date,
          purpose: item.reason.includes(':') ? item.reason.split(':').slice(1).join(':').trim() : item.reason,
          appliedOn: item.applied_on || 'N/A',
          status: (item.status as any) || 'PENDING',
          approvalStage: `Stage: ${item.status}`,
          reviewComment: item.review_comment,
          hasProof: item.has_proof,
          proofUrl: item.proof_url,
        }));
        setOds(mapped);
      })
      .catch((err) => console.error('Failed to load ODs:', err))
      .finally(() => setLoading(false));
  }, []);

  const filteredOds = ods.filter((od) => {
    const matchesSearch = od.eventTitle.toLowerCase().includes(searchTerm.toLowerCase()) ||
                          od.purpose.toLowerCase().includes(searchTerm.toLowerCase()) ||
                          od.id.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesStatus = statusFilter === 'ALL' || od.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <PageHeader
        title="My On Duty (OD) Requests"
        subtitle="Manage and track your official academic On Duty attendance requests."
        badge={<Badge variant="info">{ods.length} Total Requests</Badge>}
        actions={
          <Button
            variant="primary"
            icon={<PlusCircle className="w-4 h-4" />}
            onClick={onApplyOdClick || (() => window.location.href = '/apply-od')}
          >
            Apply New OD
          </Button>
        }
      />

      {/* Search & Filter */}
      <Card className="p-4">
        <div className="flex flex-col sm:flex-row items-center gap-4 justify-between">
          <div className="w-full sm:w-72">
            <Input
              placeholder="Search by event title, purpose, ID..."
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

      {/* List / Table */}
      {filteredOds.length === 0 ? (
        <EmptyState
          title="No OD Records Found"
          description="No On Duty requests match your search or filter criteria."
          action={{
            label: "Apply for OD",
            onClick: onApplyOdClick || (() => window.location.href = '/apply-od'),
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
                    <th className="py-3 px-4">OD ID</th>
                    <th className="py-3 px-4">Event Title</th>
                    <th className="py-3 px-4">Event Date</th>
                    <th className="py-3 px-4">Purpose</th>
                    <th className="py-3 px-4">Status</th>
                    <th className="py-3 px-4 text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/40 text-xs">
                  {filteredOds.map((od) => (
                    <tr key={od.id} className="hover:bg-surface-elevated/30 transition-colors">
                      <td className="py-3.5 px-4 font-mono font-bold text-info">{od.id}</td>
                      <td className="py-3.5 px-4 font-semibold text-text-primary">{od.eventTitle}</td>
                      <td className="py-3.5 px-4 text-text-secondary whitespace-nowrap">{od.eventDate}</td>
                      <td className="py-3.5 px-4 text-text-secondary max-w-xs truncate">{od.purpose}</td>
                      <td className="py-3.5 px-4">
                        <StatusBadge status={od.status} size="sm" />
                      </td>
                      <td className="py-3.5 px-4 text-right">
                        <Button
                          variant="ghost"
                          size="sm"
                          icon={<Eye className="w-3.5 h-3.5" />}
                          onClick={() => setSelectedOd(od)}
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

          {/* Mobile Card View */}
          <div className="grid grid-cols-1 gap-4 md:hidden">
            {filteredOds.map((od) => (
              <Card key={od.id} className="p-4 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="font-mono font-bold text-sm text-info">{od.id}</span>
                  <StatusBadge status={od.status} size="sm" />
                </div>
                <div>
                  <h4 className="text-sm font-semibold text-text-primary">{od.eventTitle}</h4>
                  <p className="text-xs text-text-secondary line-clamp-2 mt-0.5">{od.purpose}</p>
                </div>
                <div className="flex items-center justify-between text-xs text-text-muted pt-2 border-t border-border/50">
                  <span>{od.eventDate}</span>
                  <Button
                    variant="ghost"
                    size="sm"
                    icon={<Eye className="w-3.5 h-3.5" />}
                    onClick={() => setSelectedOd(od)}
                  >
                    View Details
                  </Button>
                </div>
              </Card>
            ))}
          </div>
        </>
      )}

      {/* OD Detail Modal */}
      {selectedOd && (
        <Modal
          isOpen={Boolean(selectedOd)}
          onClose={() => setSelectedOd(null)}
          title={`OD Request Details — ${selectedOd.id}`}
          description={`Applied on ${selectedOd.appliedOn}`}
          footer={
            <Button variant="secondary" onClick={() => setSelectedOd(null)}>
              Close
            </Button>
          }
        >
          <div className="space-y-4 text-xs sm:text-sm">
            <div className="grid grid-cols-2 gap-4 p-3 bg-bg-secondary rounded-lg border border-border">
              <div>
                <span className="text-text-muted block text-xs">Status:</span>
                <StatusBadge status={selectedOd.status} size="sm" className="mt-1" />
              </div>
              <div>
                <span className="text-text-muted block text-xs">Event Date:</span>
                <span className="font-semibold text-text-primary">{selectedOd.eventDate}</span>
              </div>
            </div>

            <div>
              <span className="text-text-muted block text-xs font-medium mb-1">Event Title:</span>
              <p className="font-semibold text-text-primary text-sm">{selectedOd.eventTitle}</p>
            </div>

            <div>
              <span className="text-text-muted block text-xs font-medium mb-1">Purpose / Role:</span>
              <p className="p-3 bg-surface-elevated rounded-lg border border-border text-text-primary leading-relaxed">
                {selectedOd.purpose}
              </p>
            </div>

            <div>
              <span className="text-text-muted block text-xs font-medium mb-1">Approval Stage:</span>
              <div className="p-2.5 bg-info-subtle text-info rounded-lg border border-info/20 font-medium">
                {selectedOd.approvalStage}
              </div>
            </div>

            {selectedOd.hasProof ? (
              <div>
                <span className="text-text-muted block text-xs font-medium mb-1">Supporting Proof Document:</span>
                <a
                  href={getAuthenticatedUrl(selectedOd.proofUrl || `/api/v1/ods/${selectedOd.numericId}/proof`)}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-2 px-3 py-2 bg-info/10 text-info border border-info/30 rounded-lg text-xs font-medium hover:bg-info/20 transition-colors"
                >
                  <FileText className="w-4 h-4" />
                  View Attached Event Pass / Proof
                </a>
              </div>
            ) : (
              <div>
                <span className="text-text-muted block text-xs font-medium mb-1">Upload Event Pass / Supporting Proof:</span>
                <FileUpload
                  label="Attach event pass, invitation, or proof brochure"
                  helperText="Accepted formats: PNG, JPG, PDF up to 10MB"
                  onFileSelect={async (file) => {
                    if (!file) return;
                    try {
                      await odApi.uploadProof(selectedOd.numericId, file);
                      const proofUrl = `/api/v1/ods/${selectedOd.numericId}/proof`;
                      setSelectedOd({
                        ...selectedOd,
                        hasProof: true,
                        proofUrl,
                      });
                      setOds((prev) =>
                        prev.map((o) =>
                          o.numericId === selectedOd.numericId ? { ...o, hasProof: true, proofUrl } : o
                        )
                      );
                    } catch (err: any) {
                      alert(err.message || 'Failed to upload proof document');
                    }
                  }}
                />
              </div>
            )}
          </div>
        </Modal>
      )}
    </div>
  );
};
