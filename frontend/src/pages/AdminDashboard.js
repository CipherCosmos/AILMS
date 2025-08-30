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

  useEffect(() => {
    loadData();
  }, []);

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
      `}</style>
    </div>
  );
}

export default AdminDashboard;