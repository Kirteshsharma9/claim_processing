import { useState } from 'react';
import { useAppContext } from '../context/AppContext';
import { Plus, Search, User } from 'lucide-react';

export default function MembersView() {
  const { members, addMember, policies, loading } = useAppContext();
  const [searchTerm, setSearchTerm] = useState('');
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [newMember, setNewMember] = useState({ first_name: '', last_name: '', date_of_birth: '', email: '', phone: '' });
  const [isSubmitting, setIsSubmitting] = useState(false);

  const filteredMembers = members.filter(m => 
    `${m.first_name} ${m.last_name}`.toLowerCase().includes(searchTerm.toLowerCase()) || 
    m.member_id.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const handleAddMember = async (e) => {
    e.preventDefault();
    if (!newMember.first_name || !newMember.last_name || !newMember.date_of_birth) return;
    
    setIsSubmitting(true);
    try {
      await addMember(newMember);
      setNewMember({ first_name: '', last_name: '', date_of_birth: '', email: '', phone: '' });
      setIsModalOpen(false);
    } catch (error) {
      alert("Failed to add member.");
    } finally {
      setIsSubmitting(false);
    }
  };

  if (loading) return <div className="view-container"><div style={{padding: '2rem', textAlign: 'center'}}>Loading members...</div></div>;

  return (
    <div className="view-container">
      <div className="view-header">
        <div>
          <h2>Members Directory</h2>
          <p className="text-muted">Manage your insurance members and their details.</p>
        </div>
        <button className="btn btn-primary" onClick={() => setIsModalOpen(true)}>
          <Plus size={16} /> Add Member
        </button>
      </div>

      <div className="glass-card table-container">
        <div style={{ padding: '1.5rem', borderBottom: '1px solid var(--border-light)' }}>
          <div className="header-search" style={{ width: '100%', maxWidth: '400px' }}>
            <Search size={18} className="search-icon" />
            <input 
              type="text" 
              placeholder="Search by ID or Name..." 
              className="search-input"
              value={searchTerm}
              onChange={e => setSearchTerm(e.target.value)}
            />
          </div>
        </div>
        <table className="data-table">
          <thead>
            <tr>
              <th>Member ID</th>
              <th>Name</th>
              <th>DOB</th>
              <th>Email</th>
              <th>Phone</th>
              <th>Created At</th>
            </tr>
          </thead>
          <tbody>
            {filteredMembers.map(member => (
              <tr key={member.member_id}>
                <td><strong>{member.member_id}</strong></td>
                <td>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <div style={{ background: 'var(--bg-card-hover)', padding: '0.5rem', borderRadius: '50%' }}>
                      <User size={14} />
                    </div>
                    {member.first_name} {member.last_name}
                  </div>
                </td>
                <td>{member.date_of_birth}</td>
                <td>{member.email || '-'}</td>
                <td>{member.phone || '-'}</td>
                <td>{new Date(member.created_at).toLocaleDateString()}</td>
              </tr>
            ))}
            {filteredMembers.length === 0 && (
              <tr>
                <td colSpan="6" style={{ textAlign: 'center', padding: '2rem' }}>No members found.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {isModalOpen && (
        <div className="modal-overlay">
          <div className="modal-content">
            <div className="modal-header">
              <h3 className="modal-title">Add New Member</h3>
              <button className="modal-close" onClick={() => setIsModalOpen(false)}>×</button>
            </div>
            <form onSubmit={handleAddMember}>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                <div className="form-group">
                  <label className="form-label">First Name</label>
                  <input 
                    type="text" 
                    className="form-input" 
                    value={newMember.first_name}
                    onChange={e => setNewMember({...newMember, first_name: e.target.value})}
                    required
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">Last Name</label>
                  <input 
                    type="text" 
                    className="form-input" 
                    value={newMember.last_name}
                    onChange={e => setNewMember({...newMember, last_name: e.target.value})}
                    required
                  />
                </div>
              </div>
              <div className="form-group">
                <label className="form-label">Date of Birth</label>
                <input 
                  type="date" 
                  className="form-input" 
                  value={newMember.date_of_birth}
                  onChange={e => setNewMember({...newMember, date_of_birth: e.target.value})}
                  required
                />
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                <div className="form-group">
                  <label className="form-label">Email</label>
                  <input 
                    type="email" 
                    className="form-input" 
                    value={newMember.email}
                    onChange={e => setNewMember({...newMember, email: e.target.value})}
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">Phone</label>
                  <input 
                    type="tel" 
                    className="form-input" 
                    value={newMember.phone}
                    onChange={e => setNewMember({...newMember, phone: e.target.value})}
                  />
                </div>
              </div>
              <div className="modal-footer">
                <button type="button" className="btn btn-secondary" onClick={() => setIsModalOpen(false)} disabled={isSubmitting}>Cancel</button>
                <button type="submit" className="btn btn-primary" disabled={isSubmitting}>
                  {isSubmitting ? 'Saving...' : 'Save Member'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
