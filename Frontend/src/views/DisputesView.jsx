import { useState } from 'react';
import { useAppContext } from '../context/AppContext';
import { Plus, AlertTriangle, MessageSquare } from 'lucide-react';

export default function DisputesView() {
  const { disputes, claims, fileDispute, loading } = useAppContext();
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [newDispute, setNewDispute] = useState({ claim_id: '', reason: '' });

  // Disputable claims are those that have some denied amount or status denied/partially_approved
  const disputableClaims = claims.filter(c => c.status === 'denied' || c.status === 'partially_approved' || c.total_denied > 0);

  const handleFileDispute = async (e) => {
    e.preventDefault();
    if (!newDispute.claim_id || !newDispute.reason) return;

    setIsSubmitting(true);
    try {
      const claim = claims.find(c => c.claim_id === newDispute.claim_id);
      const lineItemIds = claim?.line_items?.map(l => l.line_item_id) || [];

      await fileDispute(newDispute.claim_id, {
        reason: newDispute.reason,
        line_item_ids: lineItemIds, // typically you dispute specific line items
        supporting_documents: []
      });

      setNewDispute({ claim_id: '', reason: '' });
      setIsModalOpen(false);
    } catch (error) {
      alert("Failed to create dispute.");
    } finally {
      setIsSubmitting(false);
    }
  };

  if (loading) return <div className="view-container"><div style={{ padding: '2rem', textAlign: 'center' }}>Loading disputes...</div></div>;

  return (
    <div className="view-container">
      <div className="view-header">
        <div>
          <h2>Claims Disputes</h2>
          <p className="text-muted">Track and manage appeals for denied claims.</p>
        </div>
        <button className="btn btn-primary" onClick={() => setIsModalOpen(true)}>
          <Plus size={16} /> File Dispute
        </button>
      </div>

      <div style={{ display: 'grid', gap: '1rem' }}>
        {disputes.map(dispute => {
          const relatedClaim = claims.find(c => c.claim_id === dispute.claim_id);
          return (
            <div key={dispute.dispute_id} className="glass-card" style={{ padding: '1.5rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div style={{ display: 'flex', gap: '1.5rem', alignItems: 'center' }}>
                <div style={{ background: 'var(--warning-bg)', color: 'var(--warning)', padding: '1rem', borderRadius: 'var(--radius-lg)' }}>
                  <AlertTriangle size={24} />
                </div>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '0.25rem' }}>
                    <h3 style={{ margin: 0 }}>Dispute #{dispute.dispute_id.substring(0, 8)}</h3>
                    <span className="badge badge-warning" style={{ textTransform: 'capitalize' }}>{dispute.status.replace('_', ' ')}</span>
                  </div>
                  <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem', marginBottom: '0.5rem' }}>
                    Filed on {new Date(dispute.created_at).toLocaleDateString()} • Claim: <strong style={{ color: 'var(--text-main)' }}>{relatedClaim?.claim_number || dispute.claim_id.substring(0, 8)}</strong>
                  </p>
                  <div style={{ display: 'flex', alignItems: 'flex-start', gap: '0.5rem', background: 'rgba(255,255,255,0.02)', padding: '0.75rem', borderRadius: 'var(--radius-md)', border: '1px solid var(--border)' }}>
                    <MessageSquare size={16} style={{ color: 'var(--text-muted)', marginTop: '0.125rem' }} />
                    <p style={{ fontSize: '0.875rem', margin: 0 }}>{dispute.reason}</p>
                  </div>
                </div>
              </div>
              <div style={{ textAlign: 'right' }}>
                {relatedClaim && (
                  <div style={{ marginBottom: '1rem' }}>
                    <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', margin: 0 }}>Denied Amount</p>
                    <p style={{ fontSize: '1.25rem', fontWeight: 600, color: 'var(--danger)', margin: 0 }}>
                      ${relatedClaim.total_denied?.amount?.toLocaleString() || 0}
                    </p>
                  </div>
                )}
                <button className="btn btn-secondary" style={{ fontSize: '0.75rem' }}>Review Case</button>
              </div>
            </div>
          );
        })}
        {disputes.length === 0 && (
          <div className="glass-card" style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-muted)' }}>
            No disputes filed yet.
          </div>
        )}
      </div>

      {isModalOpen && (
        <div className="modal-overlay">
          <div className="modal-content">
            <div className="modal-header">
              <h3 className="modal-title">File a Dispute</h3>
              <button className="modal-close" onClick={() => setIsModalOpen(false)}>×</button>
            </div>
            <form onSubmit={handleFileDispute}>
              <div className="form-group">
                <label className="form-label">Select Denied Claim</label>
                <select
                  className="form-select"
                  value={newDispute.claim_id}
                  onChange={e => setNewDispute({ ...newDispute, claim_id: e.target.value })}
                  required
                >
                  <option value="">Select a Claim</option>
                  {disputableClaims.map(c => (
                    <option key={c.claim_id} value={c.claim_id}>
                      {c.claim_number || c.claim_id.substring(0, 8)} - Denied: ${c.total_denied?.toLocaleString()} ({new Date(c.created_at).toLocaleDateString()})
                    </option>
                  ))}
                </select>
                {disputableClaims.length === 0 && (
                  <p style={{ fontSize: '0.75rem', color: 'var(--warning)', marginTop: '0.5rem' }}>
                    No denied claims available to dispute.
                  </p>
                )}
              </div>
              <div className="form-group">
                <label className="form-label">Appeal Notes / Justification</label>
                <textarea
                  className="form-input"
                  rows="4"
                  placeholder="Explain why this claim should be reconsidered (min 10 chars)..."
                  value={newDispute.reason}
                  onChange={e => setNewDispute({ ...newDispute, reason: e.target.value })}
                  required
                  minLength={10}
                  style={{ resize: 'vertical' }}
                ></textarea>
              </div>
              <div className="modal-footer">
                <button type="button" className="btn btn-secondary" onClick={() => setIsModalOpen(false)} disabled={isSubmitting}>Cancel</button>
                <button type="submit" className="btn btn-primary" disabled={disputableClaims.length === 0 || isSubmitting}>
                  {isSubmitting ? 'Submitting...' : 'Submit Dispute'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
