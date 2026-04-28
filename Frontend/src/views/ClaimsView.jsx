import { useState } from 'react';
import { useAppContext } from '../context/AppContext';
import { Plus, CheckCircle, XCircle, Clock } from 'lucide-react';

export default function ClaimsView() {
  const { claims, submitClaim, members, getAdjudication, loading } = useAppContext();
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [newClaim, setNewClaim] = useState({ 
    member_id: '', 
    amount: '', 
    service_type: 'primary_care',
    description: '',
    service_date: new Date().toISOString().split('T')[0]
  });
  const [adjudicationResult, setAdjudicationResult] = useState(null);

  const handleSubmitClaim = async (e) => {
    e.preventDefault();
    if (!newClaim.member_id || !newClaim.amount) return;
    
    setIsSubmitting(true);
    try {
      const payload = {
        member_id: newClaim.member_id,
        diagnosis_codes: ["Z00.00"],
        line_items: [
          {
            service_type: newClaim.service_type,
            service_date: newClaim.service_date,
            description: newClaim.description || 'General visit',
            amount: parseFloat(newClaim.amount)
          }
        ]
      };

      const result = await submitClaim(payload);
      
      try {
        // Fetch detailed adjudication if it is automatically adjudicated
        const adjDetails = await getAdjudication(result.claim_id);
        setAdjudicationResult(adjDetails);
      } catch (err) {
        // Fallback to claim response
        setAdjudicationResult(result);
      }
    } catch (error) {
      alert("Failed to submit claim.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const resetForm = () => {
    setNewClaim({ 
      member_id: '', 
      amount: '', 
      service_type: 'primary_care',
      description: '',
      service_date: new Date().toISOString().split('T')[0]
    });
    setAdjudicationResult(null);
    setIsModalOpen(false);
  };

  const getStatusIcon = (status) => {
    switch(status) {
      case 'approved': return <CheckCircle size={16} />;
      case 'denied': return <XCircle size={16} />;
      case 'partially_approved': return <CheckCircle size={16} color="var(--warning)" />;
      default: return <Clock size={16} />;
    }
  };

  if (loading) return <div className="view-container"><div style={{padding: '2rem', textAlign: 'center'}}>Loading claims...</div></div>;

  return (
    <div className="view-container">
      <div className="view-header">
        <div>
          <h2>Claims Adjudication</h2>
          <p className="text-muted">Submit claims and view automatic adjudication results.</p>
        </div>
        <button className="btn btn-primary" onClick={() => setIsModalOpen(true)}>
          <Plus size={16} /> Submit Claim
        </button>
      </div>

      <div className="glass-card table-container">
        <table className="data-table">
          <thead>
            <tr>
              <th>Claim Number</th>
              <th>Member ID</th>
              <th>Date</th>
              <th>Amount Billed</th>
              <th>Amount Approved</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {claims.map(claim => (
              <tr key={claim.claim_id}>
                <td><strong>{claim.claim_number || claim.claim_id.substring(0, 8)}</strong></td>
                <td>{claim.member_id}</td>
                <td>{new Date(claim.created_at).toLocaleDateString()}</td>
                <td>${claim.total_requested?.toLocaleString()}</td>
                <td>${claim.total_approved?.toLocaleString()}</td>
                <td>
                  <span className={`badge ${
                    claim.status === 'approved' ? 'badge-success' : 
                    claim.status === 'denied' ? 'badge-danger' : 
                    claim.status === 'partially_approved' ? 'badge-warning' : 'badge-primary'
                  }`} style={{ display: 'flex', gap: '0.25rem', width: 'fit-content', textTransform: 'capitalize' }}>
                    {getStatusIcon(claim.status)} {claim.status.replace('_', ' ')}
                  </span>
                </td>
              </tr>
            ))}
            {claims.length === 0 && (
              <tr>
                <td colSpan="6" style={{ textAlign: 'center', padding: '2rem' }}>No claims found.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {isModalOpen && (
        <div className="modal-overlay">
          <div className="modal-content">
            <div className="modal-header">
              <h3 className="modal-title">Submit New Claim</h3>
              <button className="modal-close" onClick={resetForm}>×</button>
            </div>
            
            {!adjudicationResult ? (
              <form onSubmit={handleSubmitClaim}>
                <div className="form-group">
                  <label className="form-label">Member</label>
                  <select 
                    className="form-select"
                    value={newClaim.member_id}
                    onChange={e => setNewClaim({...newClaim, member_id: e.target.value})}
                    required
                  >
                    <option value="">Select Member</option>
                    {members.map(m => (
                      <option key={m.member_id} value={m.member_id}>{m.first_name} {m.last_name}</option>
                    ))}
                  </select>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                  <div className="form-group">
                    <label className="form-label">Amount Billed ($)</label>
                    <input 
                      type="number" 
                      className="form-input" 
                      min="0" step="0.01"
                      value={newClaim.amount}
                      onChange={e => setNewClaim({...newClaim, amount: e.target.value})}
                      required
                    />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Service Date</label>
                    <input 
                      type="date" 
                      className="form-input"
                      value={newClaim.service_date}
                      onChange={e => setNewClaim({...newClaim, service_date: e.target.value})}
                      required
                    />
                  </div>
                </div>
                <div className="form-group">
                  <label className="form-label">Service Type</label>
                  <select 
                    className="form-select"
                    value={newClaim.service_type}
                    onChange={e => setNewClaim({...newClaim, service_type: e.target.value})}
                  >
                    <option value="primary_care">Primary Care</option>
                    <option value="emergency">Emergency</option>
                    <option value="surgery">Surgery</option>
                    <option value="prescription">Prescription</option>
                  </select>
                </div>
                <div className="form-group">
                  <label className="form-label">Description</label>
                  <input 
                    type="text" 
                    className="form-input"
                    value={newClaim.description}
                    onChange={e => setNewClaim({...newClaim, description: e.target.value})}
                  />
                </div>
                <div className="modal-footer">
                  <button type="button" className="btn btn-secondary" onClick={resetForm} disabled={isSubmitting}>Cancel</button>
                  <button type="submit" className="btn btn-primary" disabled={isSubmitting}>
                    {isSubmitting ? 'Processing...' : 'Process Adjudication'}
                  </button>
                </div>
              </form>
            ) : (
              <div className="animate-fade-in" style={{ textAlign: 'center', padding: '1rem 0' }}>
                <div style={{ 
                  display: 'inline-flex', 
                  padding: '1rem', 
                  borderRadius: '50%', 
                  backgroundColor: ['approved', 'partially_approved'].includes(adjudicationResult.status) ? 'var(--success-bg)' : 'var(--danger-bg)',
                  color: ['approved', 'partially_approved'].includes(adjudicationResult.status) ? 'var(--success)' : 'var(--danger)',
                  marginBottom: '1rem'
                }}>
                  {['approved', 'partially_approved'].includes(adjudicationResult.status) ? <CheckCircle size={48} /> : <XCircle size={48} />}
                </div>
                <h3 style={{ marginBottom: '0.5rem', textTransform: 'capitalize' }}>Claim {adjudicationResult.status.replace('_', ' ')}</h3>
                
                <div style={{ background: 'var(--bg-card-hover)', padding: '1rem', borderRadius: 'var(--radius-md)', marginBottom: '1.5rem', textAlign: 'left' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                    <span style={{ color: 'var(--text-muted)' }}>Billed Amount:</span>
                    <span>${adjudicationResult.total_requested?.toLocaleString() || newClaim.amount}</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontWeight: 600, color: 'var(--success)' }}>
                    <span>Approved Amount:</span>
                    <span>${adjudicationResult.total_approved?.toLocaleString() || 0}</span>
                  </div>
                  {adjudicationResult.total_denied > 0 && (
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontWeight: 600, color: 'var(--danger)', marginTop: '0.5rem' }}>
                      <span>Denied Amount:</span>
                      <span>${adjudicationResult.total_denied?.toLocaleString() || 0}</span>
                    </div>
                  )}
                  {adjudicationResult.results && adjudicationResult.results[0]?.reason && (
                    <div style={{ marginTop: '1rem', paddingTop: '1rem', borderTop: '1px solid var(--border)', fontSize: '0.875rem' }}>
                      <span style={{ color: 'var(--text-muted)' }}>Explanation:</span><br/>
                      {adjudicationResult.results[0].reason}
                    </div>
                  )}
                </div>
                
                <button className="btn btn-primary" style={{ width: '100%' }} onClick={resetForm}>
                  Done
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
