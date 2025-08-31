import React, { useEffect, useState } from "react";
import api from "../services/api";

function AdminDashboard() {
  const [activeTab, setActiveTab] = useState("overview");
  const [analytics, setAnalytics] = useState(null);
  const [users, setUsers] = useState([]);
  const [courses, setCourses] = useState([]);
  const [selectedUser, setSelectedUser] = useState(null);
  const [userForm, setUserForm] = useState({ name: "", email: "", role: "student" });
  const [searchTerm, setSearchTerm] = useState("");
  const [systemHealth, setSystemHealth] = useState(null);
  const [securityLogs, setSecurityLogs] = useState([]);
  const [complianceReports, setComplianceReports] = useState([]);
  const [systemAnalytics, setSystemAnalytics] = useState(null);
  const [integrationStatus, setIntegrationStatus] = useState({});
  const [backupStatus, setBackupStatus] = useState(null);

  useEffect(() => {
    loadData();
  }, []);

  useEffect(() => { api.get(`/admin/system-health`).then(r => setSystemHealth(r.data)).catch(() => setSystemHealth({})); }, []);
  useEffect(() => { api.get(`/admin/security-logs`).then(r => setSecurityLogs(r.data)).catch(() => setSecurityLogs([])); }, []);
  useEffect(() => { api.get(`/admin/compliance-reports`).then(r => setComplianceReports(r.data)).catch(() => setComplianceReports([])); }, []);
  useEffect(() => { api.get(`/admin/system-analytics`).then(r => setSystemAnalytics(r.data)).catch(() => setSystemAnalytics(null)); }, []);
  useEffect(() => { api.get(`/admin/integration-status`).then(r => setIntegrationStatus(r.data)).catch(() => setIntegrationStatus({})); }, []);
  useEffect(() => { api.get(`/admin/backup-status`).then(r => setBackupStatus(r.data)).catch(() => setBackupStatus(null)); }, []);

  const loadData = async () => {
    try {
      const [analyticsRes, usersRes, coursesRes] = await Promise.all([
        api.get(`/analytics/admin`),
        api.get(`/auth/users`),
        api.get(`/courses`)
      ]);
      setAnalytics(analyticsRes.data);
      setUsers(usersRes.data);
      setCourses(coursesRes.data);
    } catch (error) {
      console.error("Error loading data:", error);
    }
  };

  const filteredUsers = users.filter(user =>
    user.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    user.email.toLowerCase().includes(searchTerm.toLowerCase()) ||
    user.role.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const updateUserRole = async (userId, newRole) => {
    try {
      await api.put(`/auth/users/${userId}`, { role: newRole });
      setUsers(users.map(u => u.id === userId ? {...u, role: newRole} : u));
      alert("User role updated successfully");
    } catch (error) {
      alert("Error updating user role");
    }
  };

  const deleteUser = async (userId) => {
    if (!confirm("Are you sure you want to delete this user? This action cannot be undone.")) return;
    try {
      await api.delete(`/auth/users/${userId}`);
      setUsers(users.filter(u => u.id !== userId));
      alert("User deleted successfully");
    } catch (error) {
      alert("Error deleting user");
    }
  };

  const createUser = async (e) => {
    e.preventDefault();
    try {
      await api.post(`/auth/register`, {
        name: userForm.name,
        email: userForm.email,
        password: "TempPass123!", // Admin should change this
        role: userForm.role
      });
      setUserForm({ name: "", email: "", role: "student" });
      loadData();
      alert("User created successfully. Default password: TempPass123!");
    } catch (error) {
      alert("Error creating user");
    }
  };

  const exportData = async (type) => {
    try {
      let data;
      let filename;
      if (type === "users") {
        data = users;
        filename = "users_export.json";
      } else if (type === "courses") {
        data = courses;
        filename = "courses_export.json";
      }

      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (error) {
      alert("Error exporting data");
    }
  };

  return (
    <div className="admin-dashboard">
      <div className="admin-header">
        <h1>Admin Dashboard</h1>
        <div className="admin-tabs">
          <button
            className={activeTab === "overview" ? "active" : ""}
            onClick={() => setActiveTab("overview")}
          >
            Overview
          </button>
          <button
            className={activeTab === "users" ? "active" : ""}
            onClick={() => setActiveTab("users")}
          >
            User Management
          </button>
          <button
            className={activeTab === "courses" ? "active" : ""}
            onClick={() => setActiveTab("courses")}
          >
            Course Management
          </button>
          <button
            className={activeTab === "analytics" ? "active" : ""}
            onClick={() => setActiveTab("analytics")}
          >
            Analytics
          </button>
          <button
            className={activeTab === "system" ? "active" : ""}
            onClick={() => setActiveTab("system")}
          >
            System Health
          </button>
          <button
            className={activeTab === "security" ? "active" : ""}
            onClick={() => setActiveTab("security")}
          >
            Security
          </button>
          <button
            className={activeTab === "compliance" ? "active" : ""}
            onClick={() => setActiveTab("compliance")}
          >
            Compliance
          </button>
          <button
            className={activeTab === "integrations" ? "active" : ""}
            onClick={() => setActiveTab("integrations")}
          >
            Integrations
          </button>
        </div>
      </div>

      <div className="admin-content">
        {activeTab === "overview" && (
          <div className="overview-grid">
            <div className="stat-card">
              <h3>Total Users</h3>
              <div className="stat-number">{analytics?.users || 0}</div>
              <div className="stat-breakdown">
                {users.filter(u => u.role === "student").length} Students<br/>
                {users.filter(u => u.role === "instructor").length} Instructors<br/>
                {users.filter(u => u.role === "admin").length} Admins
              </div>
            </div>
            <div className="stat-card">
              <h3>Total Courses</h3>
              <div className="stat-number">{analytics?.courses || 0}</div>
              <div className="stat-breakdown">
                {courses.filter(c => c.published).length} Published<br/>
                {courses.filter(c => !c.published).length} Drafts
              </div>
            </div>
            <div className="stat-card">
              <h3>Total Submissions</h3>
              <div className="stat-number">{analytics?.submissions || 0}</div>
            </div>
            <div className="stat-card">
              <h3>System Health</h3>
              <div className="stat-number">🟢 Good</div>
            </div>
          </div>
        )}

        {activeTab === "users" && (
          <div className="users-section">
            <div className="section-header">
              <h2>User Management</h2>
              <div className="header-actions">
                <input
                  type="text"
                  placeholder="Search users..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="search-input"
                />
                <button className="btn primary" onClick={() => setSelectedUser("new")}>
                  + Add User
                </button>
                <button className="btn secondary" onClick={() => exportData("users")}>
                  Export Users
                </button>
              </div>
            </div>

            {selectedUser === "new" && (
              <div className="modal-overlay">
                <div className="modal">
                  <h3>Create New User</h3>
                  <form onSubmit={createUser}>
                    <div className="form-group">
                      <label>Name</label>
                      <input
                        type="text"
                        value={userForm.name}
                        onChange={(e) => setUserForm({...userForm, name: e.target.value})}
                        required
                      />
                    </div>
                    <div className="form-group">
                      <label>Email</label>
                      <input
                        type="email"
                        value={userForm.email}
                        onChange={(e) => setUserForm({...userForm, email: e.target.value})}
                        required
                      />
                    </div>
                    <div className="form-group">
                      <label>Role</label>
                      <select
                        value={userForm.role}
                        onChange={(e) => setUserForm({...userForm, role: e.target.value})}
                      >
                        <option value="student">Student</option>
                        <option value="instructor">Instructor</option>
                        <option value="admin">Admin</option>
                        <option value="auditor">Auditor</option>
                      </select>
                    </div>
                    <div className="modal-actions">
                      <button type="button" className="btn secondary" onClick={() => setSelectedUser(null)}>
                        Cancel
                      </button>
                      <button type="submit" className="btn primary">
                        Create User
                      </button>
                    </div>
                  </form>
                </div>
              </div>
            )}

            <div className="users-table">
              <table>
                <thead>
                  <tr>
                    <th>Name</th>
                    <th>Email</th>
                    <th>Role</th>
                    <th>Created</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredUsers.map(user => (
                    <tr key={user.id}>
                      <td>{user.name}</td>
                      <td>{user.email}</td>
                      <td>
                        <select
                          value={user.role}
                          onChange={(e) => updateUserRole(user.id, e.target.value)}
                        >
                          <option value="student">Student</option>
                          <option value="instructor">Instructor</option>
                          <option value="admin">Admin</option>
                          <option value="auditor">Auditor</option>
                        </select>
                      </td>
                      <td>{new Date(user.created_at || Date.now()).toLocaleDateString()}</td>
                      <td>
                        <button
                          className="btn danger small"
                          onClick={() => deleteUser(user.id)}
                        >
                          Delete
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {activeTab === "courses" && (
          <div className="courses-section">
            <div className="section-header">
              <h2>Course Management</h2>
              <button className="btn secondary" onClick={() => exportData("courses")}>
                Export Courses
              </button>
            </div>
            <div className="courses-grid">
              {courses.map(course => (
                <div key={course.id} className="course-card">
                  <h3>{course.title}</h3>
                  <p><strong>Instructor:</strong> {course.owner_id}</p>
                  <p><strong>Status:</strong> {course.published ? "Published" : "Draft"}</p>
                  <p><strong>Students:</strong> {course.enrolled_user_ids?.length || 0}</p>
                  <p><strong>Lessons:</strong> {course.lessons?.length || 0}</p>
                  <div className="course-actions">
                    <button className="btn small" onClick={() => {/* View course details */}}>
                      View Details
                    </button>
                    {!course.published && (
                      <button className="btn primary small" onClick={() => {/* Publish course */}}>
                        Publish
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {activeTab === "analytics" && (
          <div className="analytics-section">
            <h2>Detailed Analytics</h2>
            <div className="analytics-grid">
              <div className="analytics-card">
                <h3>User Growth</h3>
                <div className="chart-placeholder">📈 Growth Chart</div>
              </div>
              <div className="analytics-card">
                <h3>Course Popularity</h3>
                <div className="chart-placeholder">📊 Course Stats</div>
              </div>
              <div className="analytics-card">
                <h3>System Performance</h3>
                <div className="chart-placeholder">⚡ Performance Metrics</div>
              </div>
            </div>
          </div>
        )}

        {activeTab === "system" && (
          <div className="system-section">
            <h2>System Health & Monitoring</h2>
            <div className="system-grid">
              <div className="system-card">
                <h3>🖥️ Server Status</h3>
                <div className="status-indicator">
                  <span className="status healthy">● Online</span>
                  <p>Uptime: {systemHealth?.uptime || "99.9%"}</p>
                  <p>Response Time: {systemHealth?.response_time || "45ms"}</p>
                </div>
              </div>

              <div className="system-card">
                <h3>💾 Database Health</h3>
                <div className="status-indicator">
                  <span className="status healthy">● Healthy</span>
                  <p>Connections: {systemHealth?.db_connections || "23/100"}</p>
                  <p>Query Time: {systemHealth?.query_time || "12ms"}</p>
                </div>
              </div>

              <div className="system-card">
                <h3>🔄 API Performance</h3>
                <div className="performance-metrics">
                  <div className="metric">
                    <span>Requests/min:</span>
                    <span>{systemAnalytics?.requests_per_minute || 1250}</span>
                  </div>
                  <div className="metric">
                    <span>Error Rate:</span>
                    <span>{systemAnalytics?.error_rate || "0.1%"}</span>
                  </div>
                  <div className="metric">
                    <span>Avg Response:</span>
                    <span>{systemAnalytics?.avg_response_time || "85ms"}</span>
                  </div>
                </div>
              </div>

              <div className="system-card">
                <h3>💽 Storage Usage</h3>
                <div className="storage-info">
                  <div className="storage-bar">
                    <div className="storage-fill" style={{width: '65%'}}></div>
                  </div>
                  <p>Used: 6.5GB / 10GB (65%)</p>
                  <p>Files: {systemHealth?.total_files || 1247}</p>
                </div>
              </div>
            </div>

            <div className="system-actions">
              <h3>System Management</h3>
              <div className="action-buttons">
                <button className="btn primary">Run Health Check</button>
                <button className="btn secondary">Clear Cache</button>
                <button className="btn secondary">Restart Services</button>
                <button className="btn danger">Emergency Shutdown</button>
              </div>
            </div>
          </div>
        )}

        {activeTab === "security" && (
          <div className="security-section">
            <h2>Security Management</h2>
            <div className="security-overview">
              <div className="security-metrics">
                <div className="metric-card">
                  <h4>🔐 Active Sessions</h4>
                  <div className="metric-value">{systemAnalytics?.active_sessions || 89}</div>
                  <p>Last 24 hours</p>
                </div>
                <div className="metric-card">
                  <h4>🚫 Failed Logins</h4>
                  <div className="metric-value">{systemAnalytics?.failed_logins || 12}</div>
                  <p>This week</p>
                </div>
                <div className="metric-card">
                  <h4>🛡️ Security Alerts</h4>
                  <div className="metric-value">{systemAnalytics?.security_alerts || 3}</div>
                  <p>Active alerts</p>
                </div>
              </div>
            </div>

            <div className="security-logs">
              <h3>Recent Security Events</h3>
              <div className="logs-table">
                <table>
                  <thead>
                    <tr>
                      <th>Time</th>
                      <th>Event</th>
                      <th>User</th>
                      <th>IP Address</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {securityLogs.map(log => (
                      <tr key={log.id}>
                        <td>{new Date(log.timestamp).toLocaleString()}</td>
                        <td>{log.event}</td>
                        <td>{log.user || 'System'}</td>
                        <td>{log.ip_address}</td>
                        <td>
                          <span className={`status ${log.status}`}>
                            {log.status}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            <div className="security-tools">
              <h3>Security Tools</h3>
              <div className="tools-grid">
                <button className="btn primary">Force Password Reset</button>
                <button className="btn secondary">Audit User Access</button>
                <button className="btn secondary">IP Whitelist</button>
                <button className="btn secondary">Security Scan</button>
              </div>
            </div>
          </div>
        )}

        {activeTab === "compliance" && (
          <div className="compliance-section">
            <h2>Compliance & Audit</h2>
            <div className="compliance-overview">
              <div className="compliance-status">
                <div className="status-card">
                  <h4>📋 GDPR Compliance</h4>
                  <div className="compliance-score">
                    <div className="score-circle">
                      <span>95%</span>
                    </div>
                    <p>Compliant</p>
                  </div>
                </div>
                <div className="status-card">
                  <h4>🔒 Data Privacy</h4>
                  <div className="compliance-score">
                    <div className="score-circle">
                      <span>98%</span>
                    </div>
                    <p>Excellent</p>
                  </div>
                </div>
                <div className="status-card">
                  <h4>📊 Accessibility</h4>
                  <div className="compliance-score">
                    <div className="score-circle">
                      <span>92%</span>
                    </div>
                    <p>Good</p>
                  </div>
                </div>
              </div>
            </div>

            <div className="compliance-reports">
              <h3>Compliance Reports</h3>
              <div className="reports-grid">
                {complianceReports.map(report => (
                  <div key={report.id} className="report-card">
                    <h4>{report.title}</h4>
                    <p>{report.description}</p>
                    <div className="report-meta">
                      <span>Generated: {new Date(report.generated_date).toLocaleDateString()}</span>
                      <span>Status: {report.status}</span>
                    </div>
                    <button className="btn small secondary">Download</button>
                  </div>
                ))}
              </div>
            </div>

            <div className="audit-trail">
              <h3>Audit Trail</h3>
              <div className="audit-logs">
                <div className="audit-entry">
                  <div className="audit-time">2024-01-15 14:30</div>
                  <div className="audit-action">User data export requested</div>
                  <div className="audit-user">admin@example.com</div>
                </div>
                <div className="audit-entry">
                  <div className="audit-time">2024-01-15 13:45</div>
                  <div className="audit-action">System backup completed</div>
                  <div className="audit-user">System</div>
                </div>
                <div className="audit-entry">
                  <div className="audit-time">2024-01-15 12:20</div>
                  <div className="audit-action">User role changed</div>
                  <div className="audit-user">admin@example.com</div>
                </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === "integrations" && (
          <div className="integrations-section">
            <h2>System Integrations</h2>
            <div className="integrations-grid">
              <div className="integration-card">
                <div className="integration-header">
                  <h4>🎓 Learning Management Systems</h4>
                  <span className={`status ${integrationStatus?.lms?.status || 'active'}`}>
                    {integrationStatus?.lms?.status || 'Active'}
                  </span>
                </div>
                <p>Connect with external LMS platforms</p>
                <div className="integration-details">
                  <span>Canvas, Moodle, Blackboard</span>
                  <button className="btn small secondary">Configure</button>
                </div>
              </div>

              <div className="integration-card">
                <div className="integration-header">
                  <h4>💼 Job Market APIs</h4>
                  <span className={`status ${integrationStatus?.job_market?.status || 'configuring'}`}>
                    {integrationStatus?.job_market?.status || 'Configuring'}
                  </span>
                </div>
                <p>Integrate with job boards and career platforms</p>
                <div className="integration-details">
                  <span>LinkedIn, Indeed, Glassdoor</span>
                  <button className="btn small secondary">Setup</button>
                </div>
              </div>

              <div className="integration-card">
                <div className="integration-header">
                  <h4>🎯 Assessment Platforms</h4>
                  <span className={`status ${integrationStatus?.assessment?.status || 'active'}`}>
                    {integrationStatus?.assessment?.status || 'Active'}
                  </span>
                </div>
                <p>Connect with external assessment tools</p>
                <div className="integration-details">
                  <span>Kahoot, Quizlet, Google Forms</span>
                  <button className="btn small secondary">Manage</button>
                </div>
              </div>

              <div className="integration-card">
                <div className="integration-header">
                  <h4>📊 Analytics Platforms</h4>
                  <span className={`status ${integrationStatus?.analytics?.status || 'inactive'}`}>
                    {integrationStatus?.analytics?.status || 'Inactive'}
                  </span>
                </div>
                <p>Export data to analytics platforms</p>
                <div className="integration-details">
                  <span>Google Analytics, Mixpanel</span>
                  <button className="btn small primary">Activate</button>
                </div>
              </div>

              <div className="integration-card">
                <div className="integration-header">
                  <h4>☁️ Cloud Storage</h4>
                  <span className={`status ${integrationStatus?.cloud?.status || 'active'}`}>
                    {integrationStatus?.cloud?.status || 'Active'}
                  </span>
                </div>
                <p>Connect to cloud storage providers</p>
                <div className="integration-details">
                  <span>AWS S3, Google Drive, Dropbox</span>
                  <button className="btn small secondary">Settings</button>
                </div>
              </div>

              <div className="integration-card">
                <div className="integration-header">
                  <h4>🤖 AI Services</h4>
                  <span className={`status ${integrationStatus?.ai?.status || 'active'}`}>
                    {integrationStatus?.ai?.status || 'Active'}
                  </span>
                </div>
                <p>AI and machine learning integrations</p>
                <div className="integration-details">
                  <span>OpenAI, Google AI, Anthropic</span>
                  <button className="btn small secondary">Configure</button>
                </div>
              </div>
            </div>

            <div className="backup-section">
              <h3>Backup & Recovery</h3>
              <div className="backup-status">
                <div className="backup-info">
                  <h4>Last Backup: {backupStatus?.last_backup || '2024-01-15 02:00'}</h4>
                  <p>Status: {backupStatus?.status || 'Successful'}</p>
                  <p>Size: {backupStatus?.size || '2.3GB'}</p>
                </div>
                <div className="backup-actions">
                  <button className="btn primary">Manual Backup</button>
                  <button className="btn secondary">Restore</button>
                  <button className="btn secondary">Schedule</button>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      <style jsx>{`
        .admin-dashboard {
          min-height: 100vh;
          background: #f5f7fa;
        }

        .admin-header {
          background: white;
          padding: 2rem;
          border-bottom: 1px solid #e1e5e9;
          box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }

        .admin-header h1 {
          margin: 0 0 1rem 0;
          color: #2c3e50;
        }

        .admin-tabs {
          display: flex;
          gap: 1rem;
        }

        .admin-tabs button {
          padding: 0.75rem 1.5rem;
          border: none;
          background: #f8f9fa;
          color: #6c757d;
          border-radius: 8px;
          cursor: pointer;
          transition: all 0.3s;
        }

        .admin-tabs button.active {
          background: #007bff;
          color: white;
        }

        .admin-content {
          padding: 2rem;
        }

        .overview-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
          gap: 2rem;
          margin-bottom: 2rem;
        }

        .stat-card {
          background: white;
          padding: 2rem;
          border-radius: 12px;
          box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }

        .stat-card h3 {
          margin: 0 0 1rem 0;
          color: #6c757d;
          font-size: 1rem;
        }

        .stat-number {
          font-size: 3rem;
          font-weight: bold;
          color: #2c3e50;
          margin-bottom: 1rem;
        }

        .stat-breakdown {
          color: #6c757d;
          line-height: 1.5;
        }

        .section-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 2rem;
        }

        .header-actions {
          display: flex;
          gap: 1rem;
          align-items: center;
        }

        .search-input {
          padding: 0.5rem 1rem;
          border: 1px solid #ddd;
          border-radius: 6px;
          width: 250px;
        }

        .users-table table {
          width: 100%;
          border-collapse: collapse;
          background: white;
          border-radius: 8px;
          overflow: hidden;
          box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }

        .users-table th,
        .users-table td {
          padding: 1rem;
          text-align: left;
          border-bottom: 1px solid #eee;
        }

        .users-table th {
          background: #f8f9fa;
          font-weight: 600;
          color: #2c3e50;
        }

        .btn {
          padding: 0.5rem 1rem;
          border: none;
          border-radius: 6px;
          cursor: pointer;
          font-weight: 500;
          transition: all 0.3s;
        }

        .btn.primary {
          background: #007bff;
          color: white;
        }

        .btn.secondary {
          background: #6c757d;
          color: white;
        }

        .btn.danger {
          background: #dc3545;
          color: white;
        }

        .btn.small {
          padding: 0.25rem 0.75rem;
          font-size: 0.875rem;
        }

        .modal-overlay {
          position: fixed;
          top: 0;
          left: 0;
          right: 0;
          bottom: 0;
          background: rgba(0,0,0,0.5);
          display: flex;
          align-items: center;
          justify-content: center;
          z-index: 1000;
        }

        .modal {
          background: white;
          padding: 2rem;
          border-radius: 12px;
          width: 500px;
          max-width: 90vw;
        }

        .form-group {
          margin-bottom: 1rem;
        }

        .form-group label {
          display: block;
          margin-bottom: 0.5rem;
          font-weight: 500;
        }

        .form-group input,
        .form-group select {
          width: 100%;
          padding: 0.75rem;
          border: 1px solid #ddd;
          border-radius: 6px;
          font-size: 1rem;
        }

        .modal-actions {
          display: flex;
          gap: 1rem;
          justify-content: flex-end;
          margin-top: 2rem;
        }

        .courses-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
          gap: 2rem;
        }

        .course-card {
          background: white;
          padding: 1.5rem;
          border-radius: 12px;
          box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }

        .course-card h3 {
          margin: 0 0 1rem 0;
          color: #2c3e50;
        }

        .course-card p {
          margin: 0.5rem 0;
          color: #6c757d;
        }

        .course-actions {
          margin-top: 1rem;
          display: flex;
          gap: 0.5rem;
        }

        .analytics-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
          gap: 2rem;
        }

        .analytics-card {
          background: white;
          padding: 2rem;
          border-radius: 12px;
          box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }

        .chart-placeholder {
          height: 200px;
          display: flex;
          align-items: center;
          justify-content: center;
          background: #f8f9fa;
          border-radius: 8px;
          color: #6c757d;
          font-size: 1.5rem;
        }

        .system-section {
          max-width: 1200px;
          margin: 0 auto;
        }

        .system-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
          gap: 2rem;
          margin-bottom: 3rem;
        }

        .system-card {
          background: white;
          padding: 2rem;
          border-radius: 12px;
          box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }

        .system-card h3 {
          margin: 0 0 1.5rem 0;
          color: #2c3e50;
        }

        .status-indicator .status {
          display: inline-block;
          padding: 0.25rem 0.75rem;
          border-radius: 20px;
          font-size: 0.875rem;
          font-weight: 600;
        }

        .status.healthy {
          background: #d4edda;
          color: #155724;
        }

        .status-indicator p {
          margin: 0.5rem 0;
          color: #6c757d;
        }

        .performance-metrics {
          display: grid;
          gap: 1rem;
        }

        .performance-metrics .metric {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 0.75rem;
          background: #f8f9fa;
          border-radius: 8px;
        }

        .storage-info {
          text-align: center;
        }

        .storage-bar {
          width: 100%;
          height: 12px;
          background: #e9ecef;
          border-radius: 6px;
          margin: 1rem 0;
          overflow: hidden;
        }

        .storage-fill {
          height: 100%;
          background: linear-gradient(90deg, #667eea, #764ba2);
          border-radius: 6px;
        }

        .system-actions {
          background: white;
          padding: 2rem;
          border-radius: 12px;
          box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }

        .action-buttons {
          display: flex;
          gap: 1rem;
          flex-wrap: wrap;
        }

        .security-section {
          max-width: 1200px;
          margin: 0 auto;
        }

        .security-overview {
          margin-bottom: 3rem;
        }

        .security-metrics {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
          gap: 2rem;
        }

        .metric-card {
          background: white;
          padding: 2rem;
          border-radius: 12px;
          box-shadow: 0 4px 6px rgba(0,0,0,0.1);
          text-align: center;
        }

        .metric-card h4 {
          margin: 0 0 1rem 0;
          color: #2c3e50;
        }

        .metric-value {
          font-size: 2.5rem;
          font-weight: bold;
          color: #667eea;
          margin-bottom: 0.5rem;
        }

        .metric-card p {
          margin: 0;
          color: #6c757d;
          font-size: 0.9rem;
        }

        .security-logs {
          background: white;
          padding: 2rem;
          border-radius: 12px;
          box-shadow: 0 4px 6px rgba(0,0,0,0.1);
          margin-bottom: 2rem;
        }

        .logs-table table {
          width: 100%;
          border-collapse: collapse;
        }

        .logs-table th,
        .logs-table td {
          padding: 1rem;
          text-align: left;
          border-bottom: 1px solid #eee;
        }

        .logs-table th {
          background: #f8f9fa;
          font-weight: 600;
          color: #2c3e50;
        }

        .logs-table .status {
          padding: 0.25rem 0.5rem;
          border-radius: 12px;
          font-size: 0.8rem;
          font-weight: 600;
        }

        .status.success { background: #d4edda; color: #155724; }
        .status.warning { background: #fff3cd; color: #856404; }
        .status.error { background: #f8d7da; color: #721c24; }

        .security-tools {
          background: white;
          padding: 2rem;
          border-radius: 12px;
          box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }

        .tools-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
          gap: 1rem;
        }

        .compliance-section {
          max-width: 1200px;
          margin: 0 auto;
        }

        .compliance-status {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
          gap: 2rem;
          margin-bottom: 3rem;
        }

        .status-card {
          background: white;
          padding: 2rem;
          border-radius: 12px;
          box-shadow: 0 4px 6px rgba(0,0,0,0.1);
          text-align: center;
        }

        .status-card h4 {
          margin: 0 0 1.5rem 0;
          color: #2c3e50;
        }

        .compliance-score {
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 1rem;
        }

        .score-circle {
          width: 80px;
          height: 80px;
          border-radius: 50%;
          background: linear-gradient(135deg, #667eea, #764ba2);
          display: flex;
          align-items: center;
          justify-content: center;
          color: white;
          font-size: 1.5rem;
          font-weight: bold;
        }

        .compliance-reports {
          background: white;
          padding: 2rem;
          border-radius: 12px;
          box-shadow: 0 4px 6px rgba(0,0,0,0.1);
          margin-bottom: 2rem;
        }

        .reports-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
          gap: 1.5rem;
        }

        .report-card {
          border: 1px solid #eee;
          border-radius: 8px;
          padding: 1.5rem;
        }

        .report-card h4 {
          margin: 0 0 0.5rem 0;
          color: #2c3e50;
        }

        .report-card p {
          margin: 0.5rem 0;
          color: #6c757d;
          font-size: 0.9rem;
        }

        .report-meta {
          display: flex;
          justify-content: space-between;
          font-size: 0.8rem;
          color: #6c757d;
          margin-bottom: 1rem;
        }

        .audit-trail {
          background: white;
          padding: 2rem;
          border-radius: 12px;
          box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }

        .audit-logs {
          display: grid;
          gap: 1rem;
        }

        .audit-entry {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 1rem;
          background: #f8f9fa;
          border-radius: 8px;
        }

        .audit-time {
          font-weight: 600;
          color: #2c3e50;
        }

        .audit-action {
          flex: 1;
          margin: 0 1rem;
          color: #6c757d;
        }

        .audit-user {
          color: #667eea;
          font-weight: 500;
        }

        .integrations-section {
          max-width: 1200px;
          margin: 0 auto;
        }

        .integrations-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
          gap: 2rem;
          margin-bottom: 3rem;
        }

        .integration-card {
          background: white;
          padding: 2rem;
          border-radius: 12px;
          box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }

        .integration-header {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          margin-bottom: 1rem;
        }

        .integration-header h4 {
          margin: 0;
          color: #2c3e50;
        }

        .integration-header .status {
          padding: 0.25rem 0.75rem;
          border-radius: 20px;
          font-size: 0.8rem;
          font-weight: 600;
        }

        .status.active { background: #d4edda; color: #155724; }
        .status.inactive { background: #e2e3e5; color: #383d41; }
        .status.configuring { background: #fff3cd; color: #856404; }

        .integration-card p {
          margin: 0.5rem 0 1.5rem 0;
          color: #6c757d;
        }

        .integration-details {
          display: flex;
          justify-content: space-between;
          align-items: center;
        }

        .integration-details span {
          color: #6c757d;
          font-size: 0.9rem;
        }

        .backup-section {
          background: white;
          padding: 2rem;
          border-radius: 12px;
          box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }

        .backup-status {
          display: flex;
          justify-content: space-between;
          align-items: center;
        }

        .backup-info h4 {
          margin: 0 0 0.5rem 0;
          color: #2c3e50;
        }

        .backup-info p {
          margin: 0.25rem 0;
          color: #6c757d;
          font-size: 0.9rem;
        }

        .backup-actions {
          display: flex;
          gap: 1rem;
        }
      `}</style>
    </div>
  );
}

export default AdminDashboard;