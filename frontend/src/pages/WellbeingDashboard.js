import React, { useEffect, useState } from "react";
import api from "../services/api";

function WellbeingDashboard() {
  const [checkinData, setCheckinData] = useState({
    stress_level: 5,
    sleep_hours: 8,
    exercise_frequency: "rarely",
    study_hours: 4,
    social_connections: 5,
    mood: "neutral",
    notes: ""
  });
  const [dashboard, setDashboard] = useState(null);
  const [trends, setTrends] = useState(null);
  const [resources, setResources] = useState([]);
  const [coaching, setCoaching] = useState(null);
  const [studyBreak, setStudyBreak] = useState(null);

  useEffect(() => {
    loadDashboard();
    loadResources();
  }, []);

  const loadDashboard = async () => {
    try {
      const [dashboardRes, trendsRes] = await Promise.all([
        api.get("/wellbeing/dashboard"),
        api.get("/wellbeing/trends")
      ]);
      setDashboard(dashboardRes.data);
      setTrends(trendsRes.data);
    } catch (error) {
      console.error("Failed to load wellbeing dashboard:", error);
    }
  };

  const loadResources = async () => {
    try {
      const res = await api.get("/wellbeing/resources");
      setResources(res.data);
    } catch (error) {
      console.error("Failed to load resources:", error);
    }
  };

  const submitCheckin = async () => {
    try {
      const res = await api.post("/wellbeing/checkin", checkinData);
      alert("Check-in submitted! " + res.data.recommendations[0]?.title || "");
      loadDashboard();
    } catch (error) {
      alert("Failed to submit check-in");
    }
  };

  const requestCoaching = async () => {
    const request = prompt("What would you like coaching on?");
    if (!request) return;

    try {
      const res = await api.post("/wellbeing/ai/coach", { request });
      setCoaching(res.data);
    } catch (error) {
      alert("Failed to get coaching");
    }
  };

  const scheduleBreak = async () => {
    try {
      const res = await api.post("/wellbeing/study-break", {
        duration_minutes: 10,
        activity_type: "breathing"
      });
      setStudyBreak(res.data);
      alert("Study break scheduled!");
    } catch (error) {
      alert("Failed to schedule break");
    }
  };

  const completeBreak = async () => {
    if (!studyBreak) return;
    try {
      await api.post(`/wellbeing/study-break/${studyBreak._id}/complete`);
      alert("Great job taking a break!");
      setStudyBreak(null);
    } catch (error) {
      alert("Failed to complete break");
    }
  };

  return (
    <div className="wellbeing-dashboard">
      <div className="wellbeing-header">
        <h1>🧘‍♀️ Well-being & Mental Health Hub</h1>
        <p>Your personal wellness companion for academic success</p>
      </div>

      <div className="wellbeing-grid">
        {/* Daily Check-in */}
        <div className="wellbeing-card checkin-card">
          <h3>📝 Daily Check-in</h3>
          <div className="checkin-form">
            <div className="form-row">
              <label>Stress Level (1-10):</label>
              <input
                type="range"
                min="1"
                max="10"
                value={checkinData.stress_level}
                onChange={(e) => setCheckinData({...checkinData, stress_level: parseInt(e.target.value)})}
              />
              <span>{checkinData.stress_level}</span>
            </div>

            <div className="form-row">
              <label>Sleep Hours:</label>
              <input
                type="number"
                min="0"
                max="24"
                step="0.5"
                value={checkinData.sleep_hours}
                onChange={(e) => setCheckinData({...checkinData, sleep_hours: parseFloat(e.target.value)})}
              />
            </div>

            <div className="form-row">
              <label>Exercise Frequency:</label>
              <select
                value={checkinData.exercise_frequency}
                onChange={(e) => setCheckinData({...checkinData, exercise_frequency: e.target.value})}
              >
                <option value="daily">Daily</option>
                <option value="weekly">Weekly</option>
                <option value="rarely">Rarely</option>
                <option value="never">Never</option>
              </select>
            </div>

            <div className="form-row">
              <label>Mood:</label>
              <select
                value={checkinData.mood}
                onChange={(e) => setCheckinData({...checkinData, mood: e.target.value})}
              >
                <option value="excellent">Excellent</option>
                <option value="good">Good</option>
                <option value="neutral">Neutral</option>
                <option value="challenging">Challenging</option>
                <option value="difficult">Difficult</option>
              </select>
            </div>

            <div className="form-row">
              <label>Notes:</label>
              <textarea
                value={checkinData.notes}
                onChange={(e) => setCheckinData({...checkinData, notes: e.target.value})}
                placeholder="How are you feeling today?"
                rows="3"
              />
            </div>

            <button className="btn primary" onClick={submitCheckin}>
              Submit Check-in
            </button>
          </div>
        </div>

        {/* Well-being Overview */}
        {dashboard && (
          <div className="wellbeing-card overview-card">
            <h3>📊 Your Well-being Overview</h3>
            <div className="stats-grid">
              <div className="stat-item">
                <span className="stat-value">{dashboard.streak_data?.current_streak || 0}</span>
                <span className="stat-label">Day Streak</span>
              </div>
              <div className="stat-item">
                <span className="stat-value">{dashboard.recent_checkins?.length || 0}</span>
                <span className="stat-label">Recent Check-ins</span>
              </div>
              <div className="stat-item">
                <span className="stat-value">
                  {dashboard.recent_checkins?.length > 0 ?
                    (dashboard.recent_checkins.reduce((sum, c) => sum + (c.stress_level || 5), 0) / dashboard.recent_checkins.length).toFixed(1) :
                    "N/A"}
                </span>
                <span className="stat-label">Avg Stress</span>
              </div>
            </div>

            {dashboard.insights?.insights?.length > 0 && (
              <div className="insights">
                <h4>💡 Insights</h4>
                {dashboard.insights.insights.map((insight, index) => (
                  <p key={index} className="insight">{insight}</p>
                ))}
              </div>
            )}
          </div>
        )}

        {/* AI Coaching */}
        <div className="wellbeing-card coaching-card">
          <h3>🤖 AI Wellness Coach</h3>
          <p>Get personalized mental health and productivity advice</p>
          <button className="btn secondary" onClick={requestCoaching}>
            Get Coaching
          </button>

          {coaching && (
            <div className="coaching-response">
              <h4>Your Coaching Session</h4>
              <div className="advice">{coaching.advice}</div>
              <div className="suggestions">
                <h5>Suggested Actions:</h5>
                <ul>
                  {coaching.suggested_actions?.map((action, index) => (
                    <li key={index}>{action}</li>
                  ))}
                </ul>
              </div>
            </div>
          )}
        </div>

        {/* Study Breaks */}
        <div className="wellbeing-card break-card">
          <h3>⏰ Study Break Scheduler</h3>
          <p>Schedule wellness-focused breaks to maintain productivity</p>
          <button className="btn accent" onClick={scheduleBreak}>
            Schedule 10-Min Break
          </button>

          {studyBreak && (
            <div className="scheduled-break">
              <h4>Break Scheduled!</h4>
              <p>Duration: {studyBreak.duration_minutes} minutes</p>
              <p>Activities: {studyBreak.activities?.map(a => a.name).join(", ")}</p>
              <button className="btn success" onClick={completeBreak}>
                Mark as Completed
              </button>
            </div>
          )}
        </div>

        {/* Resources */}
        <div className="wellbeing-card resources-card">
          <h3>📚 Wellness Resources</h3>
          <div className="resources-list">
            {resources.slice(0, 3).map(resource => (
              <div key={resource._id} className="resource-item">
                <h4>{resource.title}</h4>
                <p>{resource.content?.substring(0, 100)}...</p>
                <span className="category">{resource.category}</span>
              </div>
            ))}
          </div>
          <button className="btn light" onClick={() => alert("View all resources")}>
            View All Resources
          </button>
        </div>

        {/* Trends */}
        {trends && (
          <div className="wellbeing-card trends-card">
            <h3>📈 Well-being Trends</h3>
            <div className="trend-stats">
              <div className="trend-item">
                <span className="trend-label">Stress Trend:</span>
                <span className={`trend-value ${trends.insights?.stress_trend}`}>
                  {trends.insights?.stress_trend || "stable"}
                </span>
              </div>
              <div className="trend-item">
                <span className="trend-label">Consistency:</span>
                <span className="trend-value">
                  {((trends.insights?.consistency_score || 0) * 100).toFixed(0)}%
                </span>
              </div>
            </div>

            {trends.insights?.recommendations && (
              <div className="recommendations">
                <h4>Recommendations</h4>
                <ul>
                  {trends.insights.recommendations.map((rec, index) => (
                    <li key={index}>{rec}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}

        {/* Crisis Support */}
        <div className="wellbeing-card crisis-card">
          <h3>🚨 Crisis Support</h3>
          <p>If you're experiencing a mental health crisis, help is available 24/7</p>
          <div className="crisis-buttons">
            <button
              className="btn danger"
              onClick={() => {
                const reason = prompt("Please briefly describe what's happening:");
                if (reason) {
                  api.post("/wellbeing/crisis-support", { reason, urgency: "high" })
                    .then(() => alert("Support request submitted. Help is on the way."))
                    .catch(() => alert("Please call emergency services if you're in immediate danger."));
                }
              }}
            >
              Request Immediate Support
            </button>
            <div className="hotlines">
              <p><strong>Emergency:</strong> Call 911 (US) or local emergency services</p>
              <p><strong>Crisis Text:</strong> Text HOME to 741741</p>
              <p><strong>Suicide Prevention:</strong> 988</p>
            </div>
          </div>
        </div>
      </div>

      <style dangerouslySetInnerHTML={{
        __html: `
        .wellbeing-dashboard {
          min-height: 100vh;
          background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
          padding: 2rem;
        }

        .wellbeing-header {
          text-align: center;
          color: #2c3e50;
          margin-bottom: 2rem;
        }

        .wellbeing-header h1 {
          font-size: 2.5rem;
          margin-bottom: 0.5rem;
          background: linear-gradient(135deg, #667eea, #764ba2);
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
          background-clip: text;
        }

        .wellbeing-header p {
          font-size: 1.1rem;
          color: #6c757d;
        }

        .wellbeing-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
          gap: 2rem;
          max-width: 1200px;
          margin: 0 auto;
        }

        .wellbeing-card {
          background: white;
          border-radius: 16px;
          padding: 2rem;
          box-shadow: 0 8px 32px rgba(0,0,0,0.1);
          transition: transform 0.3s;
        }

        .wellbeing-card:hover {
          transform: translateY(-5px);
        }

        .wellbeing-card h3 {
          color: #2c3e50;
          margin-bottom: 1.5rem;
          font-size: 1.5rem;
        }

        .checkin-form {
          display: flex;
          flex-direction: column;
          gap: 1.5rem;
        }

        .form-row {
          display: flex;
          flex-direction: column;
          gap: 0.5rem;
        }

        .form-row label {
          font-weight: 600;
          color: #495057;
        }

        .form-row input, .form-row select, .form-row textarea {
          padding: 0.75rem;
          border: 2px solid #e9ecef;
          border-radius: 8px;
          font-size: 1rem;
        }

        .form-row input[type="range"] {
          width: 100%;
          height: 6px;
          border-radius: 3px;
          background: #ddd;
          outline: none;
        }

        .stats-grid {
          display: grid;
          grid-template-columns: repeat(3, 1fr);
          gap: 1rem;
          margin-bottom: 2rem;
        }

        .stat-item {
          text-align: center;
          padding: 1rem;
          background: #f8f9fa;
          border-radius: 8px;
        }

        .stat-value {
          display: block;
          font-size: 2rem;
          font-weight: bold;
          color: #667eea;
        }

        .stat-label {
          color: #6c757d;
          font-size: 0.9rem;
        }

        .insights {
          background: #f8f9fa;
          padding: 1rem;
          border-radius: 8px;
        }

        .insights h4 {
          margin: 0 0 1rem 0;
          color: #495057;
        }

        .insight {
          margin: 0.5rem 0;
          color: #6c757d;
          font-style: italic;
        }

        .coaching-response {
          margin-top: 1rem;
          padding: 1rem;
          background: #f8f9fa;
          border-radius: 8px;
        }

        .advice {
          margin-bottom: 1rem;
          line-height: 1.6;
        }

        .suggestions ul {
          margin: 0;
          padding-left: 1.5rem;
        }

        .suggestions li {
          margin: 0.5rem 0;
        }

        .scheduled-break {
          margin-top: 1rem;
          padding: 1rem;
          background: #d4edda;
          border-radius: 8px;
          border: 1px solid #c3e6cb;
        }

        .resources-list {
          display: flex;
          flex-direction: column;
          gap: 1rem;
          margin-bottom: 1rem;
        }

        .resource-item {
          padding: 1rem;
          background: #f8f9fa;
          border-radius: 8px;
          border-left: 4px solid #667eea;
        }

        .resource-item h4 {
          margin: 0 0 0.5rem 0;
          color: #495057;
        }

        .resource-item p {
          margin: 0.5rem 0;
          color: #6c757d;
        }

        .category {
          display: inline-block;
          padding: 0.25rem 0.5rem;
          background: #667eea;
          color: white;
          border-radius: 12px;
          font-size: 0.8rem;
        }

        .trend-stats {
          display: flex;
          flex-direction: column;
          gap: 1rem;
          margin-bottom: 1rem;
        }

        .trend-item {
          display: flex;
          justify-content: space-between;
          align-items: center;
        }

        .trend-label {
          font-weight: 600;
          color: #495057;
        }

        .trend-value {
          padding: 0.25rem 0.5rem;
          border-radius: 12px;
          font-weight: 600;
        }

        .trend-value.stable {
          background: #d1ecf1;
          color: #0c5460;
        }

        .trend-value.increasing {
          background: #f8d7da;
          color: #721c24;
        }

        .trend-value.decreasing {
          background: #d4edda;
          color: #155724;
        }

        .recommendations {
          background: #fff3cd;
          padding: 1rem;
          border-radius: 8px;
          border: 1px solid #ffeaa7;
        }

        .recommendations h4 {
          margin: 0 0 1rem 0;
          color: #856404;
        }

        .recommendations ul {
          margin: 0;
          padding-left: 1.5rem;
        }

        .crisis-card {
          background: linear-gradient(135deg, #ff6b6b, #ee5a24);
          color: white;
        }

        .crisis-card h3 {
          color: white;
        }

        .crisis-buttons {
          display: flex;
          flex-direction: column;
          gap: 1rem;
        }

        .hotlines {
          background: rgba(255,255,255,0.1);
          padding: 1rem;
          border-radius: 8px;
        }

        .hotlines p {
          margin: 0.5rem 0;
          font-size: 0.9rem;
        }

        .btn {
          padding: 0.75rem 1.5rem;
          border: none;
          border-radius: 8px;
          font-weight: 600;
          cursor: pointer;
          transition: all 0.3s;
        }

        .btn.primary {
          background: #667eea;
          color: white;
        }

        .btn.secondary {
          background: #6c757d;
          color: white;
        }

        .btn.accent {
          background: #28a745;
          color: white;
        }

        .btn.success {
          background: #28a745;
          color: white;
        }

        .btn.danger {
          background: #dc3545;
          color: white;
        }

        .btn.light {
          background: #f8f9fa;
          color: #6c757d;
          border: 1px solid #dee2e6;
        }

        .btn:hover {
          transform: translateY(-2px);
          box-shadow: 0 4px 12px rgba(0,0,0,0.2);
        }

        @media (max-width: 768px) {
          .wellbeing-grid {
            grid-template-columns: 1fr;
          }

          .stats-grid {
            grid-template-columns: 1fr;
          }

          .wellbeing-header h1 {
            font-size: 2rem;
          }
        }
      `}} />
    </div>
  );
}

export default WellbeingDashboard;