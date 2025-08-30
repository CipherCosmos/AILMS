import React, { useState, useEffect } from "react";
import api from "../services/api";

function SettingsPage({ me, onProfileUpdate }) {
  const [activeTab, setActiveTab] = useState("profile");
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");

  // Profile settings
  const [profileData, setProfileData] = useState({
    name: me?.name || "",
    email: me?.email || ""
  });

  // Password settings
  const [passwordData, setPasswordData] = useState({
    currentPassword: "",
    newPassword: "",
    confirmPassword: ""
  });

  // Notification preferences
  const [notificationPrefs, setNotificationPrefs] = useState({
    emailNotifications: true,
    assignmentReminders: true,
    courseUpdates: true,
    systemAnnouncements: false
  });

  useEffect(() => {
    loadUserPreferences();
  }, []);

  const loadUserPreferences = async () => {
    try {
      // Load user preferences from backend
      const response = await api.get("/profile/preferences");
      setNotificationPrefs(response.data || notificationPrefs);
    } catch (error) {
      console.error("Error loading preferences:", error);
    }
  };

  const updateProfile = async (e) => {
    e.preventDefault();
    setLoading(true);
    setMessage("");

    try {
      await api.put("/auth/me", profileData);
      setMessage("Profile updated successfully!");
      if (onProfileUpdate) {
        onProfileUpdate();
      }
    } catch (error) {
      setMessage(error.response?.data?.detail || "Error updating profile");
    } finally {
      setLoading(false);
    }
  };

  const changePassword = async (e) => {
    e.preventDefault();
    setLoading(true);
    setMessage("");

    if (passwordData.newPassword !== passwordData.confirmPassword) {
      setMessage("New passwords don't match");
      setLoading(false);
      return;
    }

    if (passwordData.newPassword.length < 6) {
      setMessage("Password must be at least 6 characters long");
      setLoading(false);
      return;
    }

    try {
      await api.put("/auth/me", {
        password: passwordData.newPassword
      });
      setMessage("Password changed successfully!");
      setPasswordData({
        currentPassword: "",
        newPassword: "",
        confirmPassword: ""
      });
    } catch (error) {
      setMessage(error.response?.data?.detail || "Error changing password");
    } finally {
      setLoading(false);
    }
  };

  const updateNotificationPreferences = async () => {
    setLoading(true);
    setMessage("");

    try {
      await api.put("/profile/preferences", notificationPrefs);
      setMessage("Notification preferences updated!");
    } catch (error) {
      setMessage("Error updating preferences");
    } finally {
      setLoading(false);
    }
  };

  const deleteAccount = async () => {
    if (!confirm("Are you sure you want to delete your account? This action cannot be undone.")) {
      return;
    }

    if (!confirm("This will permanently delete all your data. Are you absolutely sure?")) {
      return;
    }

    setLoading(true);
    try {
      await api.delete("/profile/account");
      // Redirect to login or handle logout
      localStorage.clear();
      window.location.href = "/";
    } catch (error) {
      setMessage("Error deleting account");
      setLoading(false);
    }
  };

  return (
    <div className="settings-page">
      <div className="settings-header">
        <h1>Account Settings</h1>
        <p>Manage your account preferences and information</p>
      </div>

      <div className="settings-content">
        <div className="settings-tabs">
          <button
            className={activeTab === "profile" ? "active" : ""}
            onClick={() => setActiveTab("profile")}
          >
            Profile
          </button>
          <button
            className={activeTab === "security" ? "active" : ""}
            onClick={() => setActiveTab("security")}
          >
            Security
          </button>
          <button
            className={activeTab === "notifications" ? "active" : ""}
            onClick={() => setActiveTab("notifications")}
          >
            Notifications
          </button>
          <button
            className={activeTab === "danger" ? "active" : ""}
            onClick={() => setActiveTab("danger")}
          >
            Danger Zone
          </button>
        </div>

        <div className="settings-panel">
          {message && (
            <div className={`message ${message.includes("Error") ? "error" : "success"}`}>
              {message}
            </div>
          )}

          {activeTab === "profile" && (
            <div className="profile-settings">
              <h2>Profile Information</h2>
              <form onSubmit={updateProfile}>
                <div className="form-group">
                  <label htmlFor="name">Full Name</label>
                  <input
                    type="text"
                    id="name"
                    value={profileData.name}
                    onChange={(e) => setProfileData({...profileData, name: e.target.value})}
                    required
                  />
                </div>

                <div className="form-group">
                  <label htmlFor="email">Email Address</label>
                  <input
                    type="email"
                    id="email"
                    value={profileData.email}
                    onChange={(e) => setProfileData({...profileData, email: e.target.value})}
                    required
                  />
                </div>

                <div className="form-group">
                  <label>Role</label>
                  <input
                    type="text"
                    value={me?.role || ""}
                    disabled
                    className="disabled-input"
                  />
                  <small>Your account role (cannot be changed)</small>
                </div>

                <button type="submit" className="btn primary" disabled={loading}>
                  {loading ? "Updating..." : "Update Profile"}
                </button>
              </form>
            </div>
          )}

          {activeTab === "security" && (
            <div className="security-settings">
              <h2>Change Password</h2>
              <form onSubmit={changePassword}>
                <div className="form-group">
                  <label htmlFor="currentPassword">Current Password</label>
                  <input
                    type="password"
                    id="currentPassword"
                    value={passwordData.currentPassword}
                    onChange={(e) => setPasswordData({...passwordData, currentPassword: e.target.value})}
                    required
                  />
                </div>

                <div className="form-group">
                  <label htmlFor="newPassword">New Password</label>
                  <input
                    type="password"
                    id="newPassword"
                    value={passwordData.newPassword}
                    onChange={(e) => setPasswordData({...passwordData, newPassword: e.target.value})}
                    required
                    minLength={6}
                  />
                  <small>Password must be at least 6 characters long</small>
                </div>

                <div className="form-group">
                  <label htmlFor="confirmPassword">Confirm New Password</label>
                  <input
                    type="password"
                    id="confirmPassword"
                    value={passwordData.confirmPassword}
                    onChange={(e) => setPasswordData({...passwordData, confirmPassword: e.target.value})}
                    required
                  />
                </div>

                <button type="submit" className="btn primary" disabled={loading}>
                  {loading ? "Changing..." : "Change Password"}
                </button>
              </form>
            </div>
          )}

          {activeTab === "notifications" && (
            <div className="notification-settings">
              <h2>Notification Preferences</h2>
              <div className="preferences-list">
                <div className="preference-item">
                  <div className="preference-info">
                    <h3>Email Notifications</h3>
                    <p>Receive email notifications for important updates</p>
                  </div>
                  <label className="toggle">
                    <input
                      type="checkbox"
                      checked={notificationPrefs.emailNotifications}
                      onChange={(e) => setNotificationPrefs({
                        ...notificationPrefs,
                        emailNotifications: e.target.checked
                      })}
                    />
                    <span className="toggle-slider"></span>
                  </label>
                </div>

                <div className="preference-item">
                  <div className="preference-info">
                    <h3>Assignment Reminders</h3>
                    <p>Get reminded about upcoming assignment deadlines</p>
                  </div>
                  <label className="toggle">
                    <input
                      type="checkbox"
                      checked={notificationPrefs.assignmentReminders}
                      onChange={(e) => setNotificationPrefs({
                        ...notificationPrefs,
                        assignmentReminders: e.target.checked
                      })}
                    />
                    <span className="toggle-slider"></span>
                  </label>
                </div>

                <div className="preference-item">
                  <div className="preference-info">
                    <h3>Course Updates</h3>
                    <p>Notifications about course content updates and announcements</p>
                  </div>
                  <label className="toggle">
                    <input
                      type="checkbox"
                      checked={notificationPrefs.courseUpdates}
                      onChange={(e) => setNotificationPrefs({
                        ...notificationPrefs,
                        courseUpdates: e.target.checked
                      })}
                    />
                    <span className="toggle-slider"></span>
                  </label>
                </div>

                <div className="preference-item">
                  <div className="preference-info">
                    <h3>System Announcements</h3>
                    <p>Important system updates and maintenance notifications</p>
                  </div>
                  <label className="toggle">
                    <input
                      type="checkbox"
                      checked={notificationPrefs.systemAnnouncements}
                      onChange={(e) => setNotificationPrefs({
                        ...notificationPrefs,
                        systemAnnouncements: e.target.checked
                      })}
                    />
                    <span className="toggle-slider"></span>
                  </label>
                </div>
              </div>

              <button
                className="btn primary"
                onClick={updateNotificationPreferences}
                disabled={loading}
              >
                {loading ? "Saving..." : "Save Preferences"}
              </button>
            </div>
          )}

          {activeTab === "danger" && (
            <div className="danger-zone">
              <h2>Danger Zone</h2>
              <div className="danger-item">
                <div className="danger-info">
                  <h3>Delete Account</h3>
                  <p>
                    Permanently delete your account and all associated data.
                    This action cannot be undone.
                  </p>
                </div>
                <button
                  className="btn danger"
                  onClick={deleteAccount}
                  disabled={loading}
                >
                  {loading ? "Deleting..." : "Delete Account"}
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      <style dangerouslySetInnerHTML={{
        __html: `
        .settings-page {
          min-height: 100vh;
          background: #f8f9fa;
          padding: 2rem;
        }

        .settings-header {
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          color: white;
          padding: 2rem;
          border-radius: 12px;
          margin-bottom: 2rem;
        }

        .settings-header h1 {
          margin: 0 0 0.5rem 0;
          font-size: 2rem;
        }

        .settings-header p {
          margin: 0;
          opacity: 0.9;
        }

        .settings-content {
          display: grid;
          grid-template-columns: 250px 1fr;
          gap: 2rem;
        }

        .settings-tabs {
          background: white;
          border-radius: 12px;
          box-shadow: 0 2px 4px rgba(0,0,0,0.1);
          overflow: hidden;
        }

        .settings-tabs button {
          width: 100%;
          padding: 1rem;
          border: none;
          background: none;
          text-align: left;
          cursor: pointer;
          border-bottom: 1px solid #eee;
          transition: all 0.3s;
        }

        .settings-tabs button:last-child {
          border-bottom: none;
        }

        .settings-tabs button.active {
          background: #667eea;
          color: white;
        }

        .settings-tabs button:hover:not(.active) {
          background: #f8f9fa;
        }

        .settings-panel {
          background: white;
          border-radius: 12px;
          box-shadow: 0 2px 4px rgba(0,0,0,0.1);
          padding: 2rem;
        }

        .message {
          padding: 1rem;
          border-radius: 6px;
          margin-bottom: 2rem;
        }

        .message.success {
          background: #d4edda;
          color: #155724;
          border: 1px solid #c3e6cb;
        }

        .message.error {
          background: #f8d7da;
          color: #721c24;
          border: 1px solid #f5c6cb;
        }

        .profile-settings h2,
        .security-settings h2,
        .notification-settings h2,
        .danger-zone h2 {
          margin: 0 0 2rem 0;
          color: #2c3e50;
        }

        .form-group {
          margin-bottom: 1.5rem;
        }

        .form-group label {
          display: block;
          margin-bottom: 0.5rem;
          font-weight: 500;
          color: #2c3e50;
        }

        .form-group input {
          width: 100%;
          padding: 0.75rem;
          border: 1px solid #ddd;
          border-radius: 6px;
          font-size: 1rem;
        }

        .form-group input:focus {
          outline: none;
          border-color: #667eea;
          box-shadow: 0 0 0 2px rgba(102, 126, 234, 0.2);
        }

        .disabled-input {
          background: #f8f9fa;
          cursor: not-allowed;
        }

        .form-group small {
          display: block;
          margin-top: 0.25rem;
          color: #6c757d;
          font-size: 0.875rem;
        }

        .btn {
          padding: 0.75rem 1.5rem;
          border: none;
          border-radius: 6px;
          cursor: pointer;
          font-weight: 500;
          transition: all 0.3s;
        }

        .btn.primary {
          background: #667eea;
          color: white;
        }

        .btn.primary:hover:not(:disabled) {
          background: #5a67d8;
        }

        .btn.danger {
          background: #dc3545;
          color: white;
        }

        .btn.danger:hover:not(:disabled) {
          background: #c82333;
        }

        .btn:disabled {
          opacity: 0.6;
          cursor: not-allowed;
        }

        .preferences-list {
          margin-bottom: 2rem;
        }

        .preference-item {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 1.5rem 0;
          border-bottom: 1px solid #eee;
        }

        .preference-item:last-child {
          border-bottom: none;
        }

        .preference-info h3 {
          margin: 0 0 0.5rem 0;
          color: #2c3e50;
        }

        .preference-info p {
          margin: 0;
          color: #6c757d;
        }

        .toggle {
          position: relative;
          display: inline-block;
          width: 50px;
          height: 24px;
        }

        .toggle input {
          opacity: 0;
          width: 0;
          height: 0;
        }

        .toggle-slider {
          position: absolute;
          cursor: pointer;
          top: 0;
          left: 0;
          right: 0;
          bottom: 0;
          background-color: #ccc;
          transition: 0.4s;
          border-radius: 24px;
        }

        .toggle-slider:before {
          position: absolute;
          content: "";
          height: 18px;
          width: 18px;
          left: 3px;
          bottom: 3px;
          background-color: white;
          transition: 0.4s;
          border-radius: 50%;
        }

        .toggle input:checked + .toggle-slider {
          background-color: #667eea;
        }

        .toggle input:checked + .toggle-slider:before {
          transform: translateX(26px);
        }

        .danger-zone {
          border: 2px solid #dc3545;
          border-radius: 8px;
          padding: 2rem;
        }

        .danger-item {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          gap: 2rem;
        }

        .danger-info h3 {
          margin: 0 0 1rem 0;
          color: #dc3545;
        }

        .danger-info p {
          margin: 0;
          color: #6c757d;
          line-height: 1.5;
        }

        /* Responsive Design */
        @media (max-width: 768px) {
          .settings-page {
            padding: 1rem;
          }

          .settings-content {
            grid-template-columns: 1fr;
            gap: 1rem;
          }

          .settings-header {
            padding: 1.5rem;
          }

          .settings-header h1 {
            font-size: 1.5rem;
          }

          .settings-panel {
            padding: 1.5rem;
          }

          .danger-item {
            flex-direction: column;
            gap: 1rem;
          }

          .preference-item {
            flex-direction: column;
            align-items: flex-start;
            gap: 1rem;
          }
        }

        @media (max-width: 480px) {
          .settings-tabs button {
            padding: 0.75rem;
            font-size: 0.9rem;
          }

          .form-group input {
            padding: 0.625rem;
          }

          .btn {
            padding: 0.625rem 1.25rem;
            font-size: 0.9rem;
          }
        }
      `}} />
    </div>
  );
}

export default SettingsPage;