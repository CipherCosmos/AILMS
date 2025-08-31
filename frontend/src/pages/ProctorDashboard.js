import React, { useEffect, useState } from "react";
import api from "../services/api";

function ProctorDashboard() {
  const [activeTab, setActiveTab] = useState("active");
  const [sessions, setSessions] = useState([]);
  const [incidents, setIncidents] = useState([]);
  const [analytics, setAnalytics] = useState({});

  useEffect(() => {
    loadProctoringData();
  }, [activeTab]);

  const loadProctoringData = async () => {
    try {
      const [sessionsRes, incidentsRes, analyticsRes] = await Promise.all([
        api.get("/proctoring/sessions"),
        api.get("/proctoring/incidents"),
        api.get("/proctoring/analytics")
      ]);
      setSessions(sessionsRes.data);
      setIncidents(incidentsRes.data);
      setAnalytics(analyticsRes.data);
    } catch (error) {
      console.error("Error loading proctoring data:", error);
    }
  };

  const handleSessionAction = async (sessionId, action) => {
    try {
      await api.post(`/proctoring/sessions/${sessionId}/${action}`);
      loadProctoringData();
    } catch (error) {
      console.error("Error performing session action:", error);
    }
  };

  const reportIncident = async (sessionId, incidentType, description) => {
    try {
      await api.post("/proctoring/incidents", {
        session_id: sessionId,
        incident_type: incidentType,
        description: description
      });
      loadProctoringData();
    } catch (error) {
      console.error("Error reporting incident:", error);
    }
  };

  return (
    <div className="proctor-dashboard">
      <div className="proctor-header">
        <h1>🛡️ Proctoring Dashboard</h1>
        <p>Monitor and manage exam integrity</p>
      </div>

      <div className="proctor-tabs">
        <button
          className={activeTab === "active" ? "active" : ""}
          onClick={() => setActiveTab("active")}
        >
          Active Sessions ({sessions.filter(s => s.status === "active").length})
        </button>
        <button
          className={activeTab === "completed" ? "active" : ""}
          onClick={() => setActiveTab("completed")}
        >
          Completed Sessions
        </button>
        <button
          className={activeTab === "incidents" ? "active" : ""}
          onClick={() => setActiveTab("incidents")}
        >
          Incidents ({incidents.length})
        </button>
        <button
          className={activeTab === "analytics" ? "active" : ""}
          onClick={() => setActiveTab("analytics")}
        >
          Analytics
        </button>
      </div>

      <div className="proctor-content">
        {activeTab === "active" && (
          <div className="active-sessions">
            <h2>Active Proctoring Sessions</h2>
            <div className="sessions-grid">
              {sessions.filter(s => s.status === "active").map(session => (
                <div key={session.id} className="session-card">
                  <div className="session-header">
                    <h3>{session.student_name}</h3>
                    <span className="exam-title">{session.exam_title}</span>
                  </div>
                  <div className="session-details">
                    <div className="detail-item">
                      <span>Duration:</span>
                      <span>{session.duration_minutes} min</span>
                    </div>
                    <div className="detail-item">
                      <span>Start Time:</span>
                      <span>{new Date(session.start_time).toLocaleTimeString()}</span>
                    </div>
                    <div className="detail-item">
                      <span>AI Monitoring:</span>
                      <span className={session.ai_monitoring ? "enabled" : "disabled"}>
                        {session.ai_monitoring ? "🟢 Enabled" : "🔴 Disabled"}
                      </span>
                    </div>
                  </div>
                  <div className="session-actions">
                    <button
                      className="btn small"
                      onClick={() => window.open(`/proctoring/session/${session.id}`, '_blank')}
                    >
                      Monitor
                    </button>
                    <button
                      className="btn small warning"
                      onClick={() => handleSessionAction(session.id, "pause")}
                    >
                      Pause
                    </button>
                    <button
                      className="btn small danger"
                      onClick={() => handleSessionAction(session.id, "terminate")}
                    >
                      Terminate
                    </button>
                  </div>
                  {session.behavioral_flags && session.behavioral_flags.length > 0 && (
                    <div className="behavioral-flags">
                      <h4>⚠️ Behavioral Flags:</h4>
                      <ul>
                        {session.behavioral_flags.map((flag, index) => (
                          <li key={index}>{flag}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {activeTab === "incidents" && (
          <div className="incidents-section">
            <h2>Reported Incidents</h2>
            <div className="incidents-list">
              {incidents.map(incident => (
                <div key={incident.id} className="incident-card">
                  <div className="incident-header">
                    <h3>{incident.incident_type}</h3>
                    <span className="severity">{incident.severity}</span>
                  </div>
                  <p>{incident.description}</p>
                  <div className="incident-details">
                    <span>Student: {incident.student_name}</span>
                    <span>Time: {new Date(incident.timestamp).toLocaleString()}</span>
                    <span>Status: {incident.status}</span>
                  </div>
                  {incident.status === "pending" && (
                    <div className="incident-actions">
                      <button className="btn small">Review</button>
                      <button className="btn small danger">Dismiss</button>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {activeTab === "analytics" && (
          <div className="analytics-section">
            <h2>Proctoring Analytics</h2>
            <div className="analytics-grid">
              <div className="metric-card">
                <h3>Total Sessions</h3>
                <div className="metric-value">{analytics.total_sessions || 0}</div>
              </div>
              <div className="metric-card">
                <h3>Incidents Reported</h3>
                <div className="metric-value">{analytics.total_incidents || 0}</div>
              </div>
              <div className="metric-card">
                <h3>Average Session Time</h3>
                <div className="metric-value">{analytics.avg_session_time || 0} min</div>
              </div>
              <div className="metric-card">
                <h3>AI Detections</h3>
                <div className="metric-value">{analytics.ai_detections || 0}</div>
              </div>
            </div>
          </div>
        )}
      </div>

      <style jsx>{`
        .proctor-dashboard {
          min-height: 100vh;
          background: #f8f9fa;
          padding: 2rem;
        }

        .proctor-header {
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          color: white;
          padding: 2rem;
          border-radius: 12px;
          margin-bottom: 2rem;
        }

        .proctor-tabs {
          display: flex;
          background: white;
          border-radius: 12px;
          padding: 0.5rem;
          margin-bottom: 2rem;
          box-shadow: 0 2px 4px rgba(0,0,0,0.1);
          overflow-x: auto;
        }

        .proctor-tabs button {
          padding: 0.75rem 1.5rem;
          border: none;
          background: transparent;
          border-radius: 8px;
          cursor: pointer;
          font-weight: 600;
          color: #6c757d;
          transition: all 0.3s;
          white-space: nowrap;
        }

        .proctor-tabs button.active {
          background: #667eea;
          color: white;
        }

        .proctor-content {
          background: white;
          border-radius: 12px;
          padding: 2rem;
          box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }

        .sessions-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(400px, 1fr));
          gap: 1.5rem;
        }

        .session-card {
          border: 1px solid #e9ecef;
          border-radius: 8px;
          padding: 1.5rem;
          background: white;
        }

        .session-header h3 {
          margin: 0 0 0.5rem 0;
          color: #2c3e50;
        }

        .exam-title {
          color: #667eea;
          font-weight: 500;
        }

        .session-details {
          margin: 1rem 0;
        }

        .detail-item {
          display: flex;
          justify-content: space-between;
          margin-bottom: 0.5rem;
          font-size: 0.9rem;
        }

        .session-actions {
          display: flex;
          gap: 0.5rem;
          margin-top: 1rem;
        }

        .behavioral-flags {
          margin-top: 1rem;
          padding: 1rem;
          background: #fff3cd;
          border-radius: 6px;
          border-left: 4px solid #ffc107;
        }

        .behavioral-flags h4 {
          margin: 0 0 0.5rem 0;
          color: #856404;
        }

        .behavioral-flags ul {
          margin: 0;
          padding-left: 1rem;
        }

        .incidents-list {
          display: grid;
          gap: 1rem;
        }

        .incident-card {
          border: 1px solid #e9ecef;
          border-radius: 8px;
          padding: 1.5rem;
          background: white;
        }

        .incident-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 1rem;
        }

        .incident-header h3 {
          margin: 0;
          color: #2c3e50;
        }

        .severity {
          padding: 0.25rem 0.75rem;
          border-radius: 12px;
          font-size: 0.8rem;
          font-weight: 600;
        }

        .incident-details {
          display: flex;
          gap: 2rem;
          margin: 1rem 0;
          font-size: 0.9rem;
          color: #6c757d;
        }

        .incident-actions {
          display: flex;
          gap: 0.5rem;
          margin-top: 1rem;
        }

        .analytics-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
          gap: 2rem;
          margin-top: 2rem;
        }

        .metric-card {
          background: white;
          padding: 2rem;
          border-radius: 12px;
          box-shadow: 0 4px 6px rgba(0,0,0,0.1);
          text-align: center;
        }

        .metric-card h3 {
          margin: 0 0 1rem 0;
          color: #6c757d;
          font-size: 1rem;
        }

        .metric-value {
          font-size: 2.5rem;
          font-weight: bold;
          color: #667eea;
        }

        .btn {
          padding: 0.5rem 1rem;
          border: none;
          border-radius: 6px;
          cursor: pointer;
          font-weight: 500;
          transition: all 0.3s;
        }

        .btn.small {
          padding: 0.375rem 0.75rem;
          font-size: 0.875rem;
        }

        .btn.warning {
          background: #ffc107;
          color: #212529;
        }

        .btn.danger {
          background: #dc3545;
          color: white;
        }

        .enabled {
          color: #28a745;
          font-weight: 600;
        }

        .disabled {
          color: #dc3545;
          font-weight: 600;
        }

        @media (max-width: 768px) {
          .proctor-dashboard {
            padding: 1rem;
          }

          .sessions-grid {
            grid-template-columns: 1fr;
          }

          .analytics-grid {
            grid-template-columns: 1fr;
          }

          .incident-details {
            flex-direction: column;
            gap: 0.5rem;
          }

          .session-actions {
            flex-direction: column;
          }
        }
      `}</style>
    </div>
  );
}

export default ProctorDashboard;