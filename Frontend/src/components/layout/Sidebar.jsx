import { NavLink } from 'react-router-dom';
import { Users, Shield, FileText, AlertTriangle, Activity } from 'lucide-react';
import './Sidebar.css';

const navItems = [
  { path: '/members', label: 'Members', icon: Users },
  { path: '/policies', label: 'Policies', icon: Shield },
  { path: '/claims', label: 'Claims', icon: FileText },
  { path: '/disputes', label: 'Disputes', icon: AlertTriangle },
];

export const Sidebar = () => {
  return (
    <aside className="sidebar glass-card">
      <div className="sidebar-header">
        <Activity className="sidebar-logo-icon" />
        <h2 className="sidebar-logo">InsureTech</h2>
      </div>
      <nav className="sidebar-nav">
        {navItems.map(({ path, label, icon: Icon }) => (
          <NavLink 
            key={path} 
            to={path} 
            className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
          >
            <Icon size={20} />
            <span>{label}</span>
          </NavLink>
        ))}
      </nav>
    </aside>
  );
};
