import { client } from './client';

export interface OdApiItem {
  id: number;
  event_date: string;
  status: string;
  reason: string;
  applied_on: string;
  review_comment?: string;
  has_proof?: boolean;
  proof_url?: string | null;
}

export const odApi = {
  getOds: () => client.get<OdApiItem[]>('/ods'),

  createOd: (payload: { event_date: string; reason: string; proof?: File | null }) => {
    if (payload.proof) {
      const formData = new FormData();
      formData.append('event_date', payload.event_date);
      formData.append('reason', payload.reason);
      formData.append('proof', payload.proof);
      return client.post<{ message: string; od_id: number }>('/ods', formData);
    }
    return client.post<{ message: string; od_id: number }>('/ods', payload);
  },

  uploadProof: (odId: number, proofFile: File) => {
    const formData = new FormData();
    formData.append('proof', proofFile);
    return client.post<{ message: string; proof_url: string }>(`/ods/${odId}/proof`, formData);
  },

  reviewOd: (odId: number, action: 'APPROVE' | 'REJECT', comment?: string) =>
    client.post<{ message: string }>(`/ods/${odId}/review`, { action, comment }),
};
