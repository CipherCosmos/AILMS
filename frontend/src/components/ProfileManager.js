import React, { useState, useEffect } from "react";
import api from "../services/api";

function ProfileManager({ user, onProfileUpdate }) {
  const [activeTab, setActiveTab] = useState("profile");
  const [profile, setProfile] = useState({});
  const [preferences, setPreferences] = useState({});
  const [achievements, setAchievements] = useState([]);
  const [streak, setStreak] = useState({});
  const [stats, setStats] = useState({});
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");

  useEffect(() => {
    loadProfileData();
  }, []);

  const loadProfileData = async () => {
    try {
      const [profileRes, prefsRes, achievementsRes, streakRes, statsRes] = await Promise.all([
        api.get("/profile/profile"),
        api.get("/profile/preferences"),
        api.get("/profile/achievements"),
        api.get("/profile/streak"),
        api.get("/profile/stats")
      ]);

      setProfile(profileRes.data);
      setPreferences(prefsRes.data);
      setAchievements(achievementsRes.data);
      setStreak(streakRes.data);
      setStats(statsRes.data);
    } catch (error) {
      console.error("Error loading profile data:", error);
    }
  };

  const updateProfile = async (updates) => {
    setLoading(true);
    try {
      await api.put("/profile/profile", updates);
      setProfile({ ...profile, ...updates });
      setMessage("Profile updated successfully!");
      if (onProfileUpdate) onProfileUpdate();
      setTimeout(() => setMessage(""), 3000);
    } catch (error) {
      setMessage("Error updating profile");
    }
    setLoading(false);
  };

  const updatePreferences = async (updates) => {
    setLoading(true);
    try {
      await api.put("/profile/preferences", updates);
      setPreferences({ ...preferences, ...updates });
      setMessage("Preferences updated successfully!");
      setTimeout(() => setMessage(""), 3000);
    } catch (error) {
      setMessage("Error updating preferences");
    }
    setLoading(false);
  };

  const uploadAvatar = async (file) => {
    const formData = new FormData();
    formData.append("file", file);

    setLoading(true);
    try {
      const response = await api.post("/profile/avatar", formData, {
        headers: { "Content-Type": "multipart/form-data" }
      });
      setProfile({ ...profile, avatar_url: response.data.avatar_url });
      setMessage("Avatar uploaded successfully!");
      setTimeout(() => setMessage(""), 3000);
    } catch (error) {
      setMessage("Error uploading avatar");
    }
    setLoading(false);
  };

  return (
    <div className="profile-manager">
      <div className="profile-header">
        <h2>Profile & Settings</h2>
        {message && <div className={`message ${message.includes("Error") ? "error" : "success"}`}>{message}</div>}
      </div>

      <div className="profile-tabs">
        <button
          className={activeTab === "profile" ? "active" : ""}
          onClick={() => setActiveTab("profile")}
        >
          Profile
        </button>
        <button
          className={activeTab === "preferences" ? "active" : ""}
          onClick={() => setActiveTab("preferences")}
        >
          Preferences
        </button>
        <button
          className={activeTab === "achievements" ? "active" : ""}
          onClick={() => setActiveTab("achievements")}
        >
          Achievements
        </button>
        <button
          className={activeTab === "stats" ? "active" : ""}
          onClick={() => setActiveTab("stats")}
        >
          Statistics
        </button>
      </div>

      <div className="profile-content">
        {activeTab === "profile" && (
          <div className="profile-section">
            <div className="avatar-section">
              <div className="avatar-container">
                {profile.avatar_url ? (
                  <img src={profile.avatar_url} alt="Avatar" className="avatar" />
                ) : (
                  <div className="avatar-placeholder">
                    {user?.name?.charAt(0)?.toUpperCase() || "U"}
                  </div>
                )}
                <label className="avatar-upload">
                  <input
                    type="file"
                    accept="image/*"
                    onChange={(e) => e.target.files[0] && uploadAvatar(e.target.files[0])}
                    style={{ display: "none" }}
                  />
                  <span>Change Avatar</span>
                </label>
              </div>
            </div>

            <div className="profile-form">
              <div className="form-group">
                <label>Bio</label>
                <textarea
                  value={profile.bio || ""}
                  onChange={(e) => setProfile({ ...profile, bio: e.target.value })}
                  placeholder="Tell us about yourself..."
                  rows={4}
                />
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label>Location</label>
                  <input
                    type="text"
                    value={profile.location || ""}
                    onChange={(e) => setProfile({ ...profile, location: e.target.value })}
                    placeholder="City, Country"
                  />
                </div>
                <div className="form-group">
                  <label>Website</label>
                  <input
                    type="url"
                    value={profile.website || ""}
                    onChange={(e) => setProfile({ ...profile, website: e.target.value })}
                    placeholder="https://yourwebsite.com"
                  />
                </div>
              </div>

              <div className="form-group">
                <label>Skills (comma-separated)</label>
                <input
                  type="text"
                  value={profile.skills?.join(", ") || ""}
                  onChange={(e) => setProfile({
                    ...profile,
                    skills: e.target.value.split(",").map(s => s.trim()).filter(s => s)
                  })}
                  placeholder="Python, JavaScript, Data Analysis..."
                />
              </div>

              <div className="form-group">
                <label>Learning Goals</label>
                <textarea
                  value={profile.learning_goals?.join("\n") || ""}
                  onChange={(e) => setProfile({
                    ...profile,
                    learning_goals: e.target.value.split("\n").filter(g => g.trim())
                  })}
                  placeholder="Complete advanced React course&#10;Learn machine learning&#10;Build portfolio projects"
                  rows={3}
                />
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label>Preferred Learning Style</label>
                  <select
                    value={profile.preferred_learning_style || ""}
                    onChange={(e) => setProfile({ ...profile, preferred_learning_style: e.target.value })}
                  >
                    <option value="">Select style</option>
                    <option value="visual">Visual</option>
                    <option value="auditory">Auditory</option>
                    <option value="kinesthetic">Kinesthetic</option>
                    <option value="reading">Reading/Writing</option>
                  </select>
                </div>
                <div className="form-group">
                  <label>Timezone</label>
                  <input
                    type="text"
                    value={profile.timezone || ""}
                    onChange={(e) => setProfile({ ...profile, timezone: e.target.value })}
                    placeholder="UTC+5:30"
                  />
                </div>
              </div>

              <button
                className="btn primary"
                onClick={() => updateProfile(profile)}
                disabled={loading}
              >
                {loading ? "Saving..." : "Save Profile"}
              </button>
            </div>
          </div>
        )}

        {activeTab === "preferences" && (
          <div className="preferences-section">
            <div className="preference-group">
              <h3>Appearance</h3>
              <div className="form-group">
                <label>Theme</label>
                <select
                  value={preferences.theme || "light"}
                  onChange={(e) => setPreferences({ ...preferences, theme: e.target.value })}
                >
                  <option value="light">Light</option>
                  <option value="dark">Dark</option>
                  <option value="auto">Auto</option>
                </select>
              </div>
            </div>

            <div className="preference-group">
              <h3>Notifications</h3>
              {Object.entries(preferences.email_notifications || {}).map(([key, value]) => (
                <div key={key} className="checkbox-group">
                  <label>
                    <input
                      type="checkbox"
                      checked={value}
                      onChange={(e) => setPreferences({
                        ...preferences,
                        email_notifications: {
                          ...preferences.email_notifications,
                          [key]: e.target.checked
                        }
                      })}
                    />
                    {key.replace(/_/g, " ").replace(/\b\w/g, l => l.toUpperCase())}
                  </label>
                </div>
              ))}
            </div>

            <div className="preference-group">
              <h3>Study Preferences</h3>
              <div className="form-group">
                <label>Study Reminder Time</label>
                <input
                  type="time"
                  value={preferences.reminder_time || "09:00"}
                  onChange={(e) => setPreferences({ ...preferences, reminder_time: e.target.value })}
                />
              </div>
              <div className="checkbox-group">
                <label>
                  <input
                    type="checkbox"
                    checked={preferences.study_reminders || false}
                    onChange={(e) => setPreferences({ ...preferences, study_reminders: e.target.checked })}
                  />
                  Enable study reminders
                </label>
              </div>
            </div>

            <div className="preference-group">
              <h3>Accessibility</h3>
              <div className="form-group">
                <label>Font Size</label>
                <select
                  value={preferences.accessibility?.font_size || "medium"}
                  onChange={(e) => setPreferences({
                    ...preferences,
                    accessibility: {
                      ...preferences.accessibility,
                      font_size: e.target.value
                    }
                  })}
                >
                  <option value="small">Small</option>
                  <option value="medium">Medium</option>
                  <option value="large">Large</option>
                </select>
              </div>
              <div className="checkbox-group">
                <label>
                  <input
                    type="checkbox"
                    checked={preferences.accessibility?.high_contrast || false}
                    onChange={(e) => setPreferences({
                      ...preferences,
                      accessibility: {
                        ...preferences.accessibility,
                        high_contrast: e.target.checked
                      }
                    })}
                  />
                  High contrast mode
                </label>
              </div>
            </div>

            <button
              className="btn primary"
              onClick={() => updatePreferences(preferences)}
              disabled={loading}
            >
              {loading ? "Saving..." : "Save Preferences"}
            </button>
          </div>
        )}

        {activeTab === "achievements" && (
          <div className="achievements-section">
            <div className="streak-display">
              <div className="streak-card">
                <div className="streak-icon">🔥</div>
                <div className="streak-info">
                  <h3>{streak.current_streak || 0}</h3>
                  <p>Day Streak</p>
                </div>
              </div>
              <div className="streak-card">
                <div className="streak-icon">🏆</div>
                <div className="streak-info">
                  <h3>{streak.longest_streak || 0}</h3>
                  <p>Longest Streak</p>
                </div>
              </div>
              <div className="streak-card">
                <div className="streak-icon">📅</div>
                <div className="streak-info">
                  <h3>{streak.total_study_days || 0}</h3>
                  <p>Total Study Days</p>
                </div>
              </div>
            </div>

            <div className="achievements-grid">
              {achievements.map(achievement => (
                <div key={achievement.id} className="achievement-card">
                  <div className="achievement-icon">{achievement.icon}</div>
                  <h4>{achievement.title}</h4>
                  <p>{achievement.description}</p>
                  <small>{new Date(achievement.earned_at).toLocaleDateString()}</small>
                  {achievement.points > 0 && (
                    <div className="achievement-points">+{achievement.points} points</div>
                  )}
                </div>
              ))}

              {achievements.length === 0 && (
                <div className="empty-state">
                  <h3>No achievements yet</h3>
                  <p>Complete courses and assignments to earn achievements!</p>
                </div>
              )}
            </div>
          </div>
        )}

        {activeTab === "stats" && (
          <div className="stats-section">
            <div className="stats-overview">
              <div className="stat-card">
                <h3>Level</h3>
                <div className="stat-value">{stats.level || 1}</div>
                <p>Learning Level</p>
              </div>
              <div className="stat-card">
                <h3>Points</h3>
                <div className="stat-value">{stats.points || 0}</div>
                <p>Total Points</p>
              </div>
              <div className="stat-card">
                <h3>Completion Rate</h3>
                <div className="stat-value">{stats.completion_rate?.toFixed(1) || 0}%</div>
                <p>Course Completion</p>
              </div>
              <div className="stat-card">
                <h3>Average Grade</h3>
                <div className="stat-value">{stats.average_grade?.toFixed(1) || 0}%</div>
                <p>Assignment Average</p>
              </div>
            </div>

            <div className="detailed-stats">
              <div className="stat-row">
                <span>Courses Enrolled:</span>
                <span>{stats.enrolled_courses || 0}</span>
              </div>
              <div className="stat-row">
                <span>Courses Completed:</span>
                <span>{stats.completed_courses || 0}</span>
              </div>
              <div className="stat-row">
                <span>Total Submissions:</span>
                <span>{stats.total_submissions || 0}</span>
              </div>
              <div className="stat-row">
                <span>Estimated Study Sessions:</span>
                <span>{stats.estimated_study_sessions || 0}</span>
              </div>
            </div>

            <div className="progress-chart">
              <h3>Learning Progress</h3>
              <div className="progress-bar">
                <div
                  className="progress-fill"
                  style={{ width: `${stats.completion_rate || 0}%` }}
                ></div>
              </div>
              <p>{stats.completion_rate?.toFixed(1) || 0}% of enrolled courses completed</p>
            </div>
          </div>
        )}
      </div>

      <style jsx>{`
        .profile-manager {
          max-width: 1000px;
          margin: 0 auto;
          padding: 2rem;
        }

        .profile-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 2rem;
        }

        .profile-header h2 {
          margin: 0;
          color: #2c3e50;
        }

        .message {
          padding: 0.75rem 1rem;
          border-radius: 6px;
          font-weight: 500;
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

        .profile-tabs {
          display: flex;
          border-bottom: 1px solid #e9ecef;
          margin-bottom: 2rem;
        }

        .profile-tabs button {
          padding: 1rem 2rem;
          border: none;
          background: none;
          color: #6c757d;
          cursor: pointer;
          border-bottom: 3px solid transparent;
          transition: all 0.3s;
        }

        .profile-tabs button.active {
          color: #667eea;
          border-bottom-color: #667eea;
        }

        .profile-content {
          background: white;
          border-radius: 12px;
          padding: 2rem;
          box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }

        .avatar-section {
          text-align: center;
          margin-bottom: 2rem;
        }

        .avatar-container {
          position: relative;
          display: inline-block;
        }

        .avatar {
          width: 120px;
          height: 120px;
          border-radius: 50%;
          object-fit: cover;
          border: 4px solid #667eea;
        }

        .avatar-placeholder {
          width: 120px;
          height: 120px;
          border-radius: 50%;
          background: linear-gradient(135deg, #667eea, #764ba2);
          color: white;
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 3rem;
          font-weight: bold;
          border: 4px solid #ddd;
        }

        .avatar-upload {
          position: absolute;
          bottom: 0;
          right: 0;
          background: #667eea;
          color: white;
          padding: 0.5rem 1rem;
          border-radius: 20px;
          cursor: pointer;
          font-size: 0.9rem;
          transition: background 0.3s;
        }

        .avatar-upload:hover {
          background: #5a67d8;
        }

        .profile-form {
          display: grid;
          gap: 1.5rem;
        }

        .form-row {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 1rem;
        }

        .form-group {
          display: flex;
          flex-direction: column;
        }

        .form-group label {
          margin-bottom: 0.5rem;
          font-weight: 500;
          color: #2c3e50;
        }

        .form-group input,
        .form-group select,
        .form-group textarea {
          padding: 0.75rem;
          border: 1px solid #ddd;
          border-radius: 6px;
          font-size: 1rem;
        }

        .form-group textarea {
          resize: vertical;
          min-height: 100px;
        }

        .checkbox-group {
          margin: 0.5rem 0;
        }

        .checkbox-group label {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          cursor: pointer;
        }

        .preference-group {
          margin-bottom: 2rem;
          padding-bottom: 2rem;
          border-bottom: 1px solid #eee;
        }

        .preference-group:last-child {
          border-bottom: none;
        }

        .preference-group h3 {
          margin: 0 0 1rem 0;
          color: #2c3e50;
        }

        .streak-display {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
          gap: 1rem;
          margin-bottom: 2rem;
        }

        .streak-card {
          background: linear-gradient(135deg, #667eea, #764ba2);
          color: white;
          padding: 1.5rem;
          border-radius: 12px;
          display: flex;
          align-items: center;
          gap: 1rem;
        }

        .streak-icon {
          font-size: 2rem;
        }

        .streak-info h3 {
          margin: 0;
          font-size: 2rem;
        }

        .streak-info p {
          margin: 0.25rem 0 0 0;
          opacity: 0.9;
        }

        .achievements-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
          gap: 1rem;
        }

        .achievement-card {
          background: white;
          border: 1px solid #eee;
          border-radius: 8px;
          padding: 1.5rem;
          text-align: center;
          transition: transform 0.3s, box-shadow 0.3s;
        }

        .achievement-card:hover {
          transform: translateY(-2px);
          box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        }

        .achievement-icon {
          font-size: 3rem;
          margin-bottom: 1rem;
        }

        .achievement-card h4 {
          margin: 0 0 0.5rem 0;
          color: #2c3e50;
        }

        .achievement-card p {
          margin: 0.5rem 0;
          color: #6c757d;
          font-size: 0.9rem;
        }

        .achievement-points {
          background: #667eea;
          color: white;
          padding: 0.25rem 0.75rem;
          border-radius: 12px;
          font-size: 0.8rem;
          display: inline-block;
          margin-top: 0.5rem;
        }

        .stats-overview {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
          gap: 1rem;
          margin-bottom: 2rem;
        }

        .stat-card {
          background: white;
          border: 1px solid #eee;
          border-radius: 8px;
          padding: 1.5rem;
          text-align: center;
        }

        .stat-card h3 {
          margin: 0 0 1rem 0;
          color: #6c757d;
          font-size: 0.9rem;
          text-transform: uppercase;
          letter-spacing: 0.5px;
        }

        .stat-value {
          font-size: 2.5rem;
          font-weight: bold;
          color: #667eea;
          margin-bottom: 0.5rem;
        }

        .stat-card p {
          margin: 0;
          color: #6c757d;
          font-size: 0.9rem;
        }

        .detailed-stats {
          background: #f8f9fa;
          border-radius: 8px;
          padding: 1.5rem;
          margin-bottom: 2rem;
        }

        .stat-row {
          display: flex;
          justify-content: space-between;
          padding: 0.75rem 0;
          border-bottom: 1px solid #eee;
        }

        .stat-row:last-child {
          border-bottom: none;
        }

        .progress-chart {
          background: white;
          border: 1px solid #eee;
          border-radius: 8px;
          padding: 1.5rem;
        }

        .progress-chart h3 {
          margin: 0 0 1rem 0;
          color: #2c3e50;
        }

        .progress-bar {
          width: 100%;
          height: 12px;
          background: #e9ecef;
          border-radius: 6px;
          margin-bottom: 1rem;
          overflow: hidden;
        }

        .progress-fill {
          height: 100%;
          background: linear-gradient(90deg, #667eea, #764ba2);
          border-radius: 6px;
          transition: width 0.3s;
        }

        .btn {
          padding: 0.75rem 1.5rem;
          border: none;
          border-radius: 6px;
          cursor: pointer;
          font-weight: 500;
          transition: all 0.3s;
          align-self: flex-start;
        }

        .btn.primary {
          background: #667eea;
          color: white;
        }

        .btn.primary:hover {
          background: #5a67d8;
        }

        .btn:disabled {
          opacity: 0.6;
          cursor: not-allowed;
        }

        .empty-state {
          text-align: center;
          padding: 3rem;
          color: #6c757d;
        }

        .empty-state h3 {
          margin: 0 0 1rem 0;
        }
      `}</style>
    </div>
  );
}

export default ProfileManager;