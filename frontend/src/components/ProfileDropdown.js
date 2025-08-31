import React, { useState, useRef, useEffect } from "react";
import api from "../services/api";

function ProfileDropdown({ user, onLogout, onNavigate }) {
  const [isOpen, setIsOpen] = useState(false);
  const [profileData, setProfileData] = useState(null);
  const dropdownRef = useRef(null);

  useEffect(() => {
    // Load user profile data
    loadProfileData();
  }, []);

  useEffect(() => {
    // Close dropdown when clicking outside
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const loadProfileData = async () => {
    try {
      const response = await api.get('/auth/me');
      setProfileData(response.data);
    } catch (error) {
      console.error('Error loading profile:', error);
    }
  };

  const getUserInitials = (name) => {
    return name
      .split(' ')
      .map(word => word.charAt(0))
      .join('')
      .toUpperCase()
      .slice(0, 2);
  };

  const getRoleColor = (role) => {
    const colors = {
      super_admin: '#dc3545',
      org_admin: '#dc3545',
      dept_admin: '#dc3545',
      instructor: '#28a745',
      teaching_assistant: '#28a745',
      content_author: '#28a745',
      student: '#007bff',
      auditor: '#6f42c1',
      parent_guardian: '#fd7e14',
      proctor: '#17a2b8',
      support_moderator: '#ffc107',
      career_coach: '#20c997',
      marketplace_manager: '#e83e8c',
      industry_reviewer: '#6f42c1',
      alumni: '#6c757d'
    };
    return colors[role] || '#6c757d';
  };

  const getRoleIcon = (role) => {
    const icons = {
      super_admin: '👑',
      org_admin: '🏢',
      dept_admin: '📋',
      instructor: '🎓',
      teaching_assistant: '👨‍🏫',
      content_author: '✍️',
      student: '📚',
      auditor: '🔍',
      parent_guardian: '👨‍👩‍👧‍👦',
      proctor: '👁️',
      support_moderator: '🆘',
      career_coach: '🎯',
      marketplace_manager: '🛒',
      industry_reviewer: '⭐',
      alumni: '🎓'
    };
    return icons[role] || '👤';
  };

  const handleProfileClick = () => {
    setIsOpen(!isOpen);
  };

  const handleMenuItemClick = (action) => {
    setIsOpen(false);
    // Handle different menu actions
    switch (action) {
      case 'notifications':
        if (onNavigate) onNavigate('notifications');
        break;
      case 'profile':
        if (onNavigate) onNavigate('settings'); // Profile settings are in settings page
        break;
      case 'settings':
        if (onNavigate) onNavigate('settings');
        break;
      case 'help':
        // Show help - could open a modal or navigate to help page
        alert('Help & Support coming soon!');
        break;
      case 'logout':
        onLogout();
        break;
      default:
        break;
    }
  };

  return (
    <div className="profile-dropdown" ref={dropdownRef}>
      <button
        className="profile-trigger"
        onClick={handleProfileClick}
        aria-haspopup="true"
        aria-expanded={isOpen}
      >
        <div className="profile-avatar">
          <span className="avatar-text">
            {getUserInitials(user?.name || 'User')}
          </span>
        </div>
        <div className="profile-info">
          <span className="profile-name">{user?.name}</span>
          <span className="profile-role" style={{ color: getRoleColor(user?.role) }}>
            {getRoleIcon(user?.role)} {user?.role}
          </span>
        </div>
        <svg
          className={`dropdown-arrow ${isOpen ? 'open' : ''}`}
          width="12"
          height="12"
          viewBox="0 0 12 12"
          fill="none"
        >
          <path
            d="M3 4.5L6 7.5L9 4.5"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      </button>

      {isOpen && (
        <div className="profile-menu">
          <div className="menu-header">
            <div className="menu-avatar">
              <span className="avatar-text-large">
                {getUserInitials(user?.name || 'User')}
              </span>
            </div>
            <div className="menu-user-info">
              <h4>{user?.name}</h4>
              <p>{user?.email}</p>
              <span className="menu-role-badge" style={{ backgroundColor: getRoleColor(user?.role) }}>
                {getRoleIcon(user?.role)} {user?.role}
              </span>
            </div>
          </div>

          <div className="menu-divider"></div>

          <div className="menu-items">
            <button
              className="menu-item"
              onClick={() => handleMenuItemClick('notifications')}
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                <path d="M13.73 21a2 2 0 0 1-3.46 0" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
              <span>Notifications</span>
            </button>

            <button
              className="menu-item"
              onClick={() => handleMenuItemClick('profile')}
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                <path d="M20 21V19C20 17.9391 19.5786 16.9217 18.8284 16.1716C18.0783 15.4214 17.0609 15 16 15H8C6.93913 15 5.92172 15.4214 5.17157 16.1716C4.42143 16.9217 4 17.9391 4 19V21M16 7C16 9.20914 14.2091 11 12 11C9.79086 11 8 9.20914 8 7C8 4.79086 9.79086 3 12 3C14.2091 3 16 4.79086 16 7Z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
              <span>Profile Settings</span>
            </button>

            <button
              className="menu-item"
              onClick={() => handleMenuItemClick('settings')}
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                <path d="M12 2L13.09 8.26L20 9L13.09 9.74L12 16L10.91 9.74L4 9L10.91 8.26L12 2Z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                <circle cx="12" cy="12" r="3" stroke="currentColor" strokeWidth="2"/>
              </svg>
              <span>Settings</span>
            </button>

            <button
              className="menu-item"
              onClick={() => handleMenuItemClick('help')}
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                <path d="M9.09 9C9.3251 9.14052 9.56351 9.24839 9.81637 9.32175C10.0692 9.39511 10.3326 9.43262 10.5977 9.43262C10.8628 9.43262 11.1262 9.39511 11.3791 9.32175C11.6319 9.24839 11.8703 9.14052 12.1054 9C12.3405 8.85948 12.579 8.75161 12.8318 8.67825C13.0847 8.60489 13.3481 8.56738 13.6132 8.56738C13.8783 8.56738 14.1417 8.60489 14.3946 8.67825C14.6474 8.75161 14.8858 8.85948 15.1209 9C15.356 9.14052 15.5944 9.24839 15.8473 9.32175C16.1001 9.39511 16.3635 9.43262 16.6286 9.43262C16.8937 9.43262 17.1571 9.39511 17.41 9.32175C17.6628 9.24839 17.9012 9.14052 18.1363 9L18.5 7.5C17.9375 7.1875 17.3306 7.01758 16.7123 6.99865C16.094 6.97972 15.4778 7.01224 14.8828 7.09438C14.2878 7.17652 13.7261 7.30658 13.2164 7.47746C12.7067 7.64834 12.2587 7.85672 11.89 8.09C11.5213 8.32328 11.2387 8.57746 10.9554 8.85246C10.6721 9.12746 10.3914 9.42188 10.1172 9.73C9.84301 10.0381 9.57715 10.3574 9.32422 10.68C9.07129 11.0026 8.83203 11.3262 8.60938 11.64L7.5 10.5C8.0625 10.1875 8.66937 10.0176 9.28765 9.99865C9.90593 9.97972 10.5222 10.0122 11.1172 10.0944C11.7122 10.1765 12.2739 10.3066 12.7836 10.4775C13.2933 10.6483 13.7413 10.8567 14.11 11.09C14.4787 11.3233 14.7613 11.5775 15.0446 11.8525C15.3279 12.1275 15.6086 12.4219 15.8828 12.73C16.157 13.0381 16.4229 13.3574 16.6758 13.68C16.9287 14.0026 17.168 14.3262 17.3906 14.64L18.5 13.5C17.9375 13.1875 17.3306 13.0176 16.7123 12.9987C16.094 12.9797 15.4778 13.0122 14.8828 13.0944C14.2878 13.1765 13.7261 13.3066 13.2164 13.4775C12.7067 13.6483 12.2587 13.8567 11.89 14.09C11.5213 14.3233 11.2387 14.5775 10.9554 14.8525C10.6721 15.1275 10.3914 15.4219 10.1172 15.73C9.84301 16.0381 9.57715 16.3574 9.32422 16.68C9.07129 17.0026 8.83203 17.3262 8.60938 17.64L7.5 16.5C8.0625 16.1875 8.66937 16.0176 9.28765 15.9987C9.90593 15.9797 10.5222 16.0122 11.1172 16.0944C11.7122 16.1765 12.2739 16.3066 12.7836 16.4775C13.2933 16.6483 13.7413 16.8567 14.11 17.09C14.4787 17.3233 14.7613 17.5775 15.0446 17.8525C15.3279 18.1275 15.6086 18.4219 15.8828 18.73C16.157 19.0381 16.4229 19.3574 16.6758 19.68C16.9287 20.0026 17.168 20.3262 17.3906 20.64L18.5 19.5C17.9375 19.1875 17.3306 19.0176 16.7123 18.9987C16.094 18.9797 15.4778 19.0122 14.8828 19.0944C14.2878 19.1765 13.7261 19.3066 13.2164 19.4775C12.7067 19.6483 12.2587 19.8567 11.89 20.09C11.5213 20.3233 11.2387 20.5775 10.9554 20.8525C10.6721 21.1275 10.3914 21.4219 10.1172 21.73C9.84301 22.0381 9.57715 22.3574 9.32422 22.68C9.07129 23.0026 8.83203 23.3262 8.60938 23.64L7.5 22.5C8.0625 22.1875 8.66937 22.0176 9.28765 21.9987C9.90593 21.9797 10.5222 22.0122 11.1172 22.0944C11.7122 22.1765 12.2739 22.3066 12.7836 22.4775C13.2933 22.6483 13.7413 22.8567 14.11 23.09C14.4787 23.3233 14.7613 23.5775 15.0446 23.8525C15.3279 24.1275 15.6086 24.4219 15.8828 24.73C16.157 25.0381 16.4229 25.3574 16.6758 25.68C16.9287 26.0026 17.168 26.3262 17.3906 26.64L18.5 25.5C17.9375 25.1875 17.3306 25.0176 16.7123 24.9987C16.094 24.9797 15.4778 25.0122 14.8828 25.0944C14.2878 25.1765 13.7261 25.3066 13.2164 25.4775C12.7067 25.6483 12.2587 25.8567 11.89 26.09C11.5213 26.3233 11.2387 26.5775 10.9554 26.8525C10.6721 27.1275 10.3914 27.4219 10.1172 27.73C9.84301 28.0381 9.57715 28.3574 9.32422 28.68C9.07129 29.0026 8.83203 29.3262 8.60938 29.64L7.5 28.5C8.0625 28.1875 8.66937 28.0176 9.28765 27.9987C9.90593 27.9797 10.5222 28.0122 11.1172 28.0944C11.7122 28.1765 12.2739 28.3066 12.7836 28.4775C13.2933 28.6483 13.7413 28.8567 14.11 29.09C14.4787 29.3233 14.7613 29.5775 15.0446 29.8525C15.3279 30.1275 15.6086 30.4219 15.8828 30.73C16.157 31.0381 16.4229 31.3574 16.6758 31.68C16.9287 32.0026 17.168 32.3262 17.3906 32.64L18.5 31.5C17.9375 31.1875 17.3306 31.0176 16.7123 30.9987C16.094 30.9797 15.4778 31.0122 14.8828 31.0944C14.2878 31.1765 13.7261 31.3066 13.2164 31.4775C12.7067 31.6483 12.2587 31.8567 11.89 32.09C11.5213 32.3233 11.2387 32.5775 10.9554 32.8525C10.6721 33.1275 10.3914 33.4219 10.1172 33.73C9.84301 34.0381 9.57715 34.3574 9.32422 34.68C9.07129 35.0026 8.83203 35.3262 8.60938 35.64L7.5 34.5C8.0625 34.1875 8.66937 34.0176 9.28765 33.9987C9.90593 33.9797 10.5222 34.0122 11.1172 34.0944C11.7122 34.1765 12.2739 34.3066 12.7836 34.4775C13.2933 34.6483 13.7413 34.8567 14.11 35.09C14.4787 35.3233 14.7613 35.5775 15.0446 35.8525C15.3279 36.1275 15.6086 36.4219 15.8828 36.73C16.157 37.0381 16.4229 37.3574 16.6758 37.68C16.9287 38.0026 17.168 38.3262 17.3906 38.64L18.5 37.5C17.9375 37.1875 17.3306 37.0176 16.7123 36.9987C16.094 36.9797 15.4778 37.0122 14.8828 37.0944C14.2878 37.1765 13.7261 37.3066 13.2164 37.4775C12.7067 37.6483 12.2587 37.8567 11.89 38.09C11.5213 38.3233 11.2387 38.5775 10.9554 38.8525C10.6721 39.1275 10.3914 39.4219 10.1172 39.73C9.84301 40.0381 9.57715 40.3574 9.32422 40.68C9.07129 41.0026 8.83203 41.3262 8.60938 41.64L7.5 40.5C8.0625 40.1875 8.66937 40.0176 9.28765 39.9987C9.90593 39.9797 10.5222 40.0122 11.1172 40.0944C11.7122 40.1765 12.2739 40.3066 12.7836 40.4775C13.2933 40.6483 13.7413 40.8567 14.11 41.09C14.4787 41.3233 14.7613 41.5775 15.0446 41.8525C15.3279 42.1275 15.6086 42.4219 15.8828 42.73C16.157 43.0381 16.4229 43.3574 16.6758 43.68C16.9287 44.0026 17.168 44.3262 17.3906 44.64L18.5 43.5C17.9375 43.1875 17.3306 43.0176 16.7123 42.9987C16.094 42.9797 15.4778 43.0122 14.8828 43.0944C14.2878 43.1765 13.7261 43.3066 13.2164 43.4775C12.7067 43.6483 12.2587 43.8567 11.89 44.09C11.5213 44.3233 11.2387 44.5775 10.9554 44.8525C10.6721 45.1275 10.3914 45.4219 10.1172 45.73C9.84301 46.0381 9.57715 46.3574 9.32422 46.68C9.07129 47.0026 8.83203 47.3262 8.60938 47.64L7.5 46.5C8.0625 46.1875 8.66937 45.9987 9.28765 45.9797C9.90593 45.9608 10.5222 45.9933 11.1172 46.0754C11.7122 46.1576 12.2739 46.2876 12.7836 46.4585C13.2933 46.6294 13.7413 46.8377 14.11 47.071C14.4787 47.3043 14.7613 47.5585 15.0446 47.8335C15.3279 48.1085 15.6086 48.4029 15.8828 48.711C16.157 49.0191 16.4229 49.3384 16.6758 49.661C16.9287 49.9836 17.168 50.3072 17.3906 50.621L18.5 49.5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
              <span>Help & Support</span>
            </button>

            <div className="menu-divider"></div>

            <button
              className="menu-item logout"
              onClick={() => handleMenuItemClick('logout')}
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                <path d="M9 21H5C4.46957 21 3.96086 20.7893 3.58579 20.4142C3.21071 20.0391 3 19.5304 3 19V5C3 4.46957 3.21071 3.96086 3.58579 3.58579C3.96086 3.21071 4.46957 3 5 3H9M16 17L21 12M21 12L16 7M21 12H9" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
              <span>Sign Out</span>
            </button>
          </div>
        </div>
      )}

      <style jsx>{`
        .profile-dropdown {
          position: relative;
          display: flex;
          align-items: center;
        }

        .profile-trigger {
          display: flex;
          align-items: center;
          gap: 0.75rem;
          padding: 0.5rem 0.75rem;
          background: rgba(255, 255, 255, 0.1);
          border: 1px solid rgba(255, 255, 255, 0.2);
          border-radius: 50px;
          color: white;
          cursor: pointer;
          transition: all 0.3s ease;
          backdrop-filter: blur(10px);
        }

        .profile-trigger:hover {
          background: rgba(255, 255, 255, 0.2);
          transform: translateY(-1px);
        }

        .profile-avatar {
          width: 32px;
          height: 32px;
          border-radius: 50%;
          background: linear-gradient(135deg, #667eea, #764ba2);
          display: flex;
          align-items: center;
          justify-content: center;
          font-weight: 600;
          font-size: 0.9rem;
          color: white;
          border: 2px solid rgba(255, 255, 255, 0.3);
        }

        .profile-info {
          display: flex;
          flex-direction: column;
          align-items: flex-start;
          min-width: 0;
        }

        .profile-name {
          font-weight: 600;
          font-size: 0.9rem;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
          max-width: 120px;
        }

        .profile-role {
          font-size: 0.75rem;
          opacity: 0.9;
          display: flex;
          align-items: center;
          gap: 0.25rem;
        }

        .dropdown-arrow {
          transition: transform 0.3s ease;
          opacity: 0.8;
        }

        .dropdown-arrow.open {
          transform: rotate(180deg);
        }

        .profile-menu {
          position: absolute;
          top: calc(100% + 0.5rem);
          right: 0;
          width: 280px;
          background: white;
          border-radius: 16px;
          box-shadow: 0 20px 40px rgba(0, 0, 0, 0.15);
          border: 1px solid rgba(0, 0, 0, 0.05);
          overflow: hidden;
          z-index: 1000;
          animation: slideDown 0.3s ease-out;
        }

        @keyframes slideDown {
          from {
            opacity: 0;
            transform: translateY(-10px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }

        .menu-header {
          padding: 1.5rem;
          background: linear-gradient(135deg, #f8f9fa, #e9ecef);
          display: flex;
          align-items: center;
          gap: 1rem;
        }

        .menu-avatar {
          width: 50px;
          height: 50px;
          border-radius: 50%;
          background: linear-gradient(135deg, #667eea, #764ba2);
          display: flex;
          align-items: center;
          justify-content: center;
          font-weight: 700;
          font-size: 1.2rem;
          color: white;
          border: 3px solid white;
          box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
        }

        .menu-user-info h4 {
          margin: 0 0 0.25rem 0;
          color: #2c3e50;
          font-size: 1.1rem;
        }

        .menu-user-info p {
          margin: 0 0 0.5rem 0;
          color: #6c757d;
          font-size: 0.9rem;
        }

        .menu-role-badge {
          display: inline-flex;
          align-items: center;
          gap: 0.25rem;
          padding: 0.25rem 0.75rem;
          border-radius: 20px;
          color: white;
          font-size: 0.75rem;
          font-weight: 600;
          text-transform: uppercase;
          letter-spacing: 0.5px;
        }

        .menu-divider {
          height: 1px;
          background: #e9ecef;
          margin: 0;
        }

        .menu-items {
          padding: 0.5rem 0;
        }

        .menu-item {
          width: 100%;
          display: flex;
          align-items: center;
          gap: 0.75rem;
          padding: 0.75rem 1.5rem;
          background: none;
          border: none;
          color: #495057;
          cursor: pointer;
          transition: all 0.2s ease;
          font-size: 0.9rem;
        }

        .menu-item:hover {
          background: #f8f9fa;
          color: #2c3e50;
        }

        .menu-item.logout {
          color: #dc3545;
        }

        .menu-item.logout:hover {
          background: #f8d7da;
        }

        .menu-item svg {
          opacity: 0.7;
        }

        .menu-item:hover svg {
          opacity: 1;
        }

        /* Responsive Design */
        @media (max-width: 768px) {
          .profile-menu {
            width: 260px;
            right: -1rem;
          }

          .profile-trigger {
            padding: 0.4rem 0.6rem;
          }

          .profile-info {
            display: none;
          }

          .profile-avatar {
            width: 28px;
            height: 28px;
          }

          .menu-header {
            padding: 1rem;
          }

          .menu-avatar {
            width: 40px;
            height: 40px;
          }
        }

        @media (max-width: 480px) {
          .profile-menu {
            width: 240px;
          }

          .menu-item {
            padding: 0.6rem 1rem;
            font-size: 0.85rem;
          }
        }
      `}</style>
    </div>
  );
}

export default ProfileDropdown;