import { useState } from 'react';
import { useAppContext } from '../context/AppContext';
import { Plus, ShieldAlert } from 'lucide-react';

export default function PoliciesView() {
  const { policies, addPolicy, members, loading } = useAppContext();
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [newPolicy, setNewPolicy] = useState({
    member_id: '',
    policy_number: '',
    policy_start: '',
    policy_end: '',
    limit_amount: '',
    coverage_percentage: '',
    service_type: 'primary_care',
    limit_type: 'annual_max'
  });

  const handleAddPolicy = async (e) => {
    e.preventDefault();
    if (!newPolicy.member_id || !newPolicy.policy_number) return;

    setIsSubmitting(true);
    try {
      const payload = {
        member_id: newPolicy.member_id,
        policy_number: newPolicy.policy_number,
        policy_start: newPolicy.policy_start,
        policy_end: newPolicy.policy_end,
        coverage_rules: [
          {
            service_type: newPolicy.service_type,
            coverage_percentage: parseFloat(newPolicy.coverage_percentage) / 100,
            limit_type: newPolicy.limit_type,
            limit_amount: parseFloat(newPolicy.limit_amount),
            effective_date: newPolicy.policy_start
          }
        ]
      };

      await addPolicy(payload);
      setNewPolicy({
        member_id: '', policy_number: '', policy_start: '', policy_end: '',
        limit_amount: '', coverage_percentage: '', service_type: 'primary_care', limit_type: 'annual_max'
      });
      setIsModalOpen(false);
    } catch (error) {
      alert("Failed to create policy.");
    } finally {
      setIsSubmitting(false);
    }
  };

  if (loading) return <div className="view-container"><div style={{ padding: '2rem', textAlign: 'center' }}>Loading policies...</div></div>;

  return (
    <div className="view-container">
      <div className="view-header">
        <div>
          <h2>Coverage Policies</h2>
          <p className="text-muted">Define coverage rules, limits, and percentages for members.</p>
        </div>
        <button className="btn btn-primary" onClick={() => setIsModalOpen(true)}>
          <Plus size={16} /> Create Policy
        </button>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '1.5rem' }}>
        {policies.map(policy => {
          const rule = policy.coverage_rules && policy.coverage_rules.length > 0 ? policy.coverage_rules[0] : null;
          return (
            <div key={policy.policy_id} className="glass-card" style={{ padding: '1.5rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                  <div style={{ background: 'var(--primary)', padding: '0.5rem', borderRadius: 'var(--radius-md)', color: 'white' }}>
                    <ShieldAlert size={20} />
                  </div>
                  <div>
                    <h3 style={{ margin: 0 }}>Policy #{policy.policy_number}</h3>
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Member: {policy.member_id}</span>
                  </div>
                </div>
              </div>

              {rule && (
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginTop: '1.5rem' }}>
                  <div>
                    <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '0.25rem' }}>Coverage Limit</p>
                    <p style={{ fontSize: '1.125rem', fontWeight: 600 }}>${rule.limit_amount?.amount?.toLocaleString() || 0}</p>
                  </div>
                  <div>
                    <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '0.25rem' }}>Percentage</p>
                    <p style={{ fontSize: '1.125rem', fontWeight: 600 }}>{(rule.coverage_percentage * 100).toFixed(0)}%</p>
                  </div>
                  <div style={{ gridColumn: 'span 2' }}>
                    <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '0.25rem' }}>Service Type</p>
                    <span className="badge badge-primary">{rule.service_type}</span>
                  </div>
                </div>
              )}
            </div>
          )
        })}
        {policies.length === 0 && (
          <div style={{ gridColumn: '1 / -1', padding: '3rem', textAlign: 'center', color: 'var(--text-muted)' }} className="glass-card">
            No policies found.
          </div>
        )}
      </div>

      {isModalOpen && (
        <div className="modal-overlay">
          <div className="modal-content" style={{ maxWidth: '600px' }}>
            <div className="modal-header">
              <h3 className="modal-title">Create New Policy</h3>
              <button className="modal-close" onClick={() => setIsModalOpen(false)}>×</button>
            </div>
            <form onSubmit={handleAddPolicy}>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                <div className="form-group">
                  <label className="form-label">Member</label>
                  <select
                    className="form-select"
                    value={newPolicy.member_id}
                    onChange={e => setNewPolicy({ ...newPolicy, member_id: e.target.value })}
                    required
                  >
                    <option value="">Select Member</option>
                    {members.map(m => (
                      <option key={m.member_id} value={m.member_id}>{m.first_name} {m.last_name}</option>
                    ))}
                  </select>
                </div>
                <div className="form-group">
                  <label className="form-label">Policy Number</label>
                  <input
                    type="text"
                    className="form-input"
                    value={newPolicy.policy_number}
                    onChange={e => setNewPolicy({ ...newPolicy, policy_number: e.target.value })}
                    required
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">Start Date</label>
                  <input
                    type="date"
                    className="form-input"
                    value={newPolicy.policy_start}
                    onChange={e => setNewPolicy({ ...newPolicy, policy_start: e.target.value })}
                    required
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">End Date</label>
                  <input
                    type="date"
                    className="form-input"
                    value={newPolicy.policy_end}
                    onChange={e => setNewPolicy({ ...newPolicy, policy_end: e.target.value })}
                    required
                  />
                </div>
              </div>

              <hr style={{ borderColor: 'var(--border-light)', margin: '1rem 0' }} />
              <h4 style={{ marginBottom: '1rem' }}>Coverage Rule</h4>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                <div className="form-group">
                  <label className="form-label">Service Type</label>
                  <select
                    className="form-select"
                    value={newPolicy.service_type}
                    onChange={e => setNewPolicy({ ...newPolicy, service_type: e.target.value })}
                  >
                    <option value="primary_care">Primary Care</option>
                    <option value="specialist">Specialist</option>
                    <option value="emergency">Emergency</option>
                    <option value="urgent_care">Urgent Care</option>
                    <option value="inpatient">Inpatient</option>
                    <option value="surgery">Surgery</option>
                    <option value="prescription">Prescription</option>
                    <option value="other">Other</option>
                  </select>
                </div>
                <div className="form-group">
                  <label className="form-label">Limit Type</label>
                  <select
                    className="form-select"
                    value={newPolicy.limit_type}
                    onChange={e => setNewPolicy({ ...newPolicy, limit_type: e.target.value })}
                  >
                    <option value="annual_max">Annual Max</option>
                    <option value="per_occurrence">Per Occurrence</option>
                    <option value="per_visit">Per Visit</option>
                    <option value="lifetime_max">Lifetime Max</option>
                  </select>
                </div>
                <div className="form-group">
                  <label className="form-label">Limit Amount ($)</label>
                  <input
                    type="number"
                    className="form-input"
                    min="0"
                    value={newPolicy.limit_amount}
                    onChange={e => setNewPolicy({ ...newPolicy, limit_amount: e.target.value })}
                    required
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">Coverage % (0-100)</label>
                  <input
                    type="number"
                    className="form-input"
                    min="0" max="100"
                    value={newPolicy.coverage_percentage}
                    onChange={e => setNewPolicy({ ...newPolicy, coverage_percentage: e.target.value })}
                    required
                  />
                </div>
              </div>

              <div className="modal-footer">
                <button type="button" className="btn btn-secondary" onClick={() => setIsModalOpen(false)} disabled={isSubmitting}>Cancel</button>
                <button type="submit" className="btn btn-primary" disabled={isSubmitting}>
                  {isSubmitting ? 'Creating...' : 'Create Policy'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
