import { Bell, Search, UserCircle } from 'lucide-react';
import './Header.css';

export const Header = () => {
  return (
    <header className="header glass-card">
      <div className="header-search">
        <Search size={18} className="search-icon" />
        <input type="text" placeholder="Search members, claims, or policies..." className="search-input" />
      </div>
      <div className="header-actions">
        <button className="icon-btn">
          <Bell size={20} />
          <span className="notification-dot"></span>
        </button>
        <div className="user-profile">
          <UserCircle size={32} className="user-avatar" />
          <div className="user-info">
            <span className="user-name">Admin User</span>
            <span className="user-role">Super Admin</span>
          </div>
        </div>
      </div>
    </header>
  );
};
