import React, { useEffect, useState } from "react";
import api from "../services/api";

function AIEthicsDashboard({ me }) {
  const [activeTab, setActiveTab] = useState("overview");
  const [policy, setPolicy] = useState(null);
  const [transparencyLog, setTransparencyLog] = useState([]);
  const [privacyControls, setPrivacyControls] = useState({});
  const [ethicsDashboard, setEthicsDashboard] = useState(null);
  const [guardrailsStatus, setGuardrailsStatus] = useState(null);
  const [guidelines, setGuidelines] = useState(null);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [policyRes, logRes, privacyRes, dashboardRes, guardrailsRes, guidelinesRes] = await Promise.all([
        api.get("/ai-ethics/ai-usage-policy"),
        api.get("/ai-ethics/ai-transparency-log"),
        api.get("/ai-ethics/ai-privacy-controls"),
        me.role === "admin" ? api.get("/ai-ethics/ai-ethics-dashboard") : Promise.resolve(null),
        api.get("/ai-ethics/ai-guardrails-status"),
        api.get("/ai-ethics/responsible-ai-guidelines")
      ]);

      setPolicy(policyRes.data);
      setTransparencyLog(logRes.data);
      setPrivacyControls(privacyRes.data);
      if (dashboardRes) setEthicsDashboard(dashboardRes.data);
      setGuardrailsStatus(guardrailsRes.data);
      setGuidelines(guidelinesRes.data);
    } catch (error) {
      console.error("Error loading AI ethics data:", error);
    }
  };

  const acceptPolicy = async () => {
    try {
      await api.post("/ai-ethics/accept-ai-policy", { version: policy.version });
      alert("AI usage policy accepted!");
      loadData();
    } catch (error) {
      alert("Error accepting policy");
    }
  };

  const updatePrivacyControls = async (controls) => {
    try {
      await api.put("/ai-ethics/update-privacy-controls", controls);
      alert("Privacy controls updated!");
      loadData();
    } catch (error) {
      alert("Error updating privacy controls");
    }
  };

  const reportIssue = async () => {
    const issueData = {
      issue_type: "bias_concern",
      severity: "medium",
      ai_feature: "content_generation",
      description: "Detected potential bias in generated content",
      expected_behavior: "Neutral, inclusive content",
      actual_behavior: "Content showed cultural bias",
      impact_assessment: "Medium - affects user experience",
      suggested_fix: "Implement additional bias detection filters"
    };

    try {
      await api.post("/ai-ethics/report-ai-issue", issueData);
      alert("Issue reported successfully!");
    } catch (error) {
      alert("Error reporting issue");
    }
  };

  const checkContentBias = async () => {
    const content = prompt("Enter content to check for bias:");
    if (content) {
      try {
        const response = await api.get("/ai-ethics/ai-bias-check", {
          params: { content, content_type: "educational_content" }
        });
        alert(`Bias analysis complete. Score: ${response.data.bias_score}`);
      } catch (error) {
        alert("Error checking content bias");
      }
    }
  };

  return (
    <div className="ai-ethics-dashboard">
      <div className="ethics-header">
        <h1>🛡️ Responsible AI Dashboard</h1>
        <p>Monitor and manage ethical AI usage in education</p>
      </div>

      <div className="ethics-tabs">
        <button
          className={activeTab === "overview" ? "active" : ""}
          onClick={() => setActiveTab("overview")}
        >
          Overview
        </button>
        <button
          className={activeTab === "policy" ? "active" : ""}
          onClick={() => setActiveTab("policy")}
        >
          AI Policy
        </button>
        <button
          className={activeTab === "transparency" ? "active" : ""}
          onClick={() => setActiveTab("transparency")}
        >
          Transparency
        </button>
        <button
          className={activeTab === "privacy" ? "active" : ""}
          onClick={() => setActiveTab("privacy")}
        >
          Privacy
        </button>
        {me.role === "admin" && (
          <button
            className={activeTab === "compliance" ? "active" : ""}
            onClick={() => setActiveTab("compliance")}
          >
            Compliance
          </button>
        )}
        <button
          className={activeTab === "guardrails" ? "active" : ""}
          onClick={() => setActiveTab("guardrails")}
        >
          Guardrails
        </button>
      </div>

      <div className="ethics-content">
        {activeTab === "overview" && (
          <div className="overview-section">
            <div className="ethics-cards">
              <div className="ethics-card">
                <h3>AI Usage Status</h3>
                <div className="status-indicator active">
                  <span>🟢 Active & Compliant</span>
                </div>
                <p>All AI features are operating within ethical guidelines</p>
              </div>
              <div className="ethics-card">
                <h3>Policy Acceptance</h3>
                <div className="metric">{policy?.last_accepted_version ? "✅ Accepted" : "❌ Not Accepted"}</div>
                <p>Version {policy?.version} - {policy?.effective_date}</p>
              </div>
              <div className="ethics-card">
                <h3>Recent AI Interactions</h3>
                <div className="metric">{transparencyLog.length}</div>
                <p>Tracked in the last 7 days</p>
              </div>
              <div className="ethics-card">
                <h3>Privacy Controls</h3>
                <div className="metric">
                  {Object.values(privacyControls).filter(v => v).length}/{Object.keys(privacyControls).length}
                </div>
                <p>Privacy settings configured</p>
              </div>
            </div>

            <div className="quick-actions">
              <h3>Quick Actions</h3>
              <div className="action-buttons">
                <button className="btn secondary" onClick={checkContentBias}>
                  Check Content Bias
                </button>
                <button className="btn secondary" onClick={reportIssue}>
                  Report AI Issue
                </button>
                {!policy?.last_accepted_version && (
                  <button className="btn primary" onClick={acceptPolicy}>
                    Accept AI Policy
                  </button>
                )}
              </div>
            </div>
          </div>
        )}

        {activeTab === "policy" && policy && (
          <div className="policy-section">
            <div className="policy-header">
              <h2>AI Usage Policy</h2>
              <div className="policy-meta">
                <span>Version {policy.version}</span>
                <span>Effective: {policy.effective_date}</span>
                {policy.last_accepted_version ? (
                  <span className="accepted">✅ Accepted</span>
                ) : (
                  <span className="not-accepted">❌ Not Accepted</span>
                )}
              </div>
            </div>

            <div className="policy-content">
              {policy.sections.map((section, index) => (
                <div key={index} className="policy-section">
                  <h3>{section.title}</h3>
                  <p>{section.content}</p>
                  {section.principles && (
                    <ul>
                      {section.principles.map((principle, i) => (
                        <li key={i}>{principle}</li>
                      ))}
                    </ul>
                  )}
                  {section.rights && (
                    <ul>
                      {section.rights.map((right, i) => (
                        <li key={i}>{right}</li>
                      ))}
                    </ul>
                  )}
                </div>
              ))}
            </div>

            {!policy.last_accepted_version && (
              <div className="policy-acceptance">
                <button className="btn primary" onClick={acceptPolicy}>
                  Accept AI Usage Policy
                </button>
              </div>
            )}
          </div>
        )}

        {activeTab === "transparency" && (
          <div className="transparency-section">
            <h2>AI Transparency Log</h2>
            <div className="transparency-log">
              {transparencyLog.map(entry => (
                <div key={entry._id} className="log-entry">
                  <div className="log-header">
                    <h4>{entry.ai_feature.replace('_', ' ')}</h4>
                    <span className="timestamp">
                      {new Date(entry.timestamp).toLocaleString()}
                    </span>
                  </div>
                  <div className="log-details">
                    <p><strong>Action:</strong> {entry.action.replace('_', ' ')}</p>
                    <p><strong>Model:</strong> {entry.model_used}</p>
                    <p><strong>Processing Time:</strong> {entry.processing_time}s</p>
                    <p><strong>Confidence:</strong> {(entry.confidence_score * 100).toFixed(1)}%</p>
                  </div>
                  <div className="log-explanation">
                    <p>{entry.explanation}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {activeTab === "privacy" && (
          <div className="privacy-section">
            <h2>AI Privacy Controls</h2>
            <div className="privacy-controls">
              <div className="control-group">
                <h3>Data Collection</h3>
                <label>
                  <input
                    type="checkbox"
                    checked={privacyControls.data_collection_consent || false}
                    onChange={(e) => updatePrivacyControls({
                      ai_data_collection_consent: e.target.checked
                    })}
                  />
                  Consent to AI data collection for personalization
                </label>
              </div>

              <div className="control-group">
                <h3>Personalization</h3>
                <label>
                  <input
                    type="checkbox"
                    checked={privacyControls.personalization_enabled || false}
                    onChange={(e) => updatePrivacyControls({
                      ai_personalization_enabled: e.target.checked
                    })}
                  />
                  Enable AI-powered personalization
                </label>
              </div>

              <div className="control-group">
                <h3>Analytics Sharing</h3>
                <label>
                  <input
                    type="checkbox"
                    checked={privacyControls.analytics_sharing || false}
                    onChange={(e) => updatePrivacyControls({
                      ai_analytics_sharing: e.target.checked
                    })}
                  />
                  Share anonymized analytics for research
                </label>
              </div>

              <div className="control-group">
                <h3>Data Retention</h3>
                <select
                  value={privacyControls.data_retention_period || 365}
                  onChange={(e) => updatePrivacyControls({
                    ai_data_retention_period: parseInt(e.target.value)
                  })}
                >
                  <option value={30}>30 days</option>
                  <option value={90}>90 days</option>
                  <option value={365}>1 year</option>
                  <option value={730}>2 years</option>
                </select>
                <p>Data retention period for AI interactions</p>
              </div>

              <div className="control-group">
                <h3>Model Training Opt-out</h3>
                <label>
                  <input
                    type="checkbox"
                    checked={privacyControls.model_training_opt_out || false}
                    onChange={(e) => updatePrivacyControls({
                      ai_model_training_opt_out: e.target.checked
                    })}
                  />
                  Opt-out of using my data for AI model training
                </label>
              </div>
            </div>
          </div>
        )}

        {activeTab === "compliance" && me.role === "admin" && ethicsDashboard && (
          <div className="compliance-section">
            <h2>AI Ethics Compliance Dashboard</h2>
            <div className="compliance-metrics">
              <div className="metric-card">
                <h3>Overall Compliance</h3>
                <div className="metric-value">{ethicsDashboard.overall_compliance_score}%</div>
                <div className={`status ${ethicsDashboard.overall_compliance_score >= 90 ? 'good' : 'warning'}`}>
                  {ethicsDashboard.overall_compliance_score >= 90 ? 'Excellent' : 'Needs Attention'}
                </div>
              </div>
              <div className="metric-card">
                <h3>Active Issues</h3>
                <div className="metric-value">{ethicsDashboard.active_issues}</div>
                <div className="status warning">Under Review</div>
              </div>
              <div className="metric-card">
                <h3>Policy Acceptance</h3>
                <div className="metric-value">{ethicsDashboard.policy_acceptance_rate}%</div>
                <div className="status good">Good</div>
              </div>
              <div className="metric-card">
                <h3>AI Interactions</h3>
                <div className="metric-value">{ethicsDashboard.ai_usage_metrics.total_ai_interactions.toLocaleString()}</div>
                <div className="status info">This Month</div>
              </div>
            </div>

            <div className="recent-issues">
              <h3>Recent Issues</h3>
              <div className="issues-list">
                {ethicsDashboard.recent_issues.map(issue => (
                  <div key={issue.id} className="issue-item">
                    <div className="issue-header">
                      <h4>{issue.type.replace('_', ' ')}</h4>
                      <span className={`severity ${issue.severity}`}>{issue.severity}</span>
                    </div>
                    <p>Status: {issue.status}</p>
                    <small>Reported: {new Date(issue.reported_at).toLocaleDateString()}</small>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {activeTab === "guardrails" && guardrailsStatus && (
          <div className="guardrails-section">
            <h2>AI Guardrails Status</h2>
            <div className="guardrails-grid">
              {Object.entries(guardrailsStatus).map(([key, status]) => (
                <div key={key} className="guardrail-card">
                  <div className="guardrail-header">
                    <h3>{key.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}</h3>
                    <span className={`status ${status.status === 'active' ? 'active' : 'inactive'}`}>
                      {status.status}
                    </span>
                  </div>
                  <div className="guardrail-details">
                    <p>Last Updated: {new Date(status.last_updated).toLocaleString()}</p>
                    {status.filtered_content && (
                      <p>Content Filtered: {status.filtered_content.toLocaleString()}</p>
                    )}
                    {status.scanned_content && (
                      <p>Content Scanned: {status.scanned_content.toLocaleString()}</p>
                    )}
                    {status.models_monitored && (
                      <p>Models: {status.models_monitored.join(', ')}</p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      <style jsx>{`
        .ai-ethics-dashboard {
          min-height: 100vh;
          background: #f8f9fa;
          padding: 2rem;
        }

        .ethics-header {
          text-align: center;
          margin-bottom: 2rem;
        }

        .ethics-header h1 {
          color: #2c3e50;
          margin-bottom: 0.5rem;
        }

        .ethics-header p {
          color: #6c757d;
          font-size: 1.1rem;
        }

        .ethics-tabs {
          display: flex;
          justify-content: center;
          margin-bottom: 2rem;
          background: white;
          border-radius: 12px;
          padding: 0.5rem;
          box-shadow: 0 2px 4px rgba(0,0,0,0.1);
          flex-wrap: wrap;
        }

        .ethics-tabs button {
          padding: 0.75rem 1.5rem;
          border: none;
          background: transparent;
          border-radius: 8px;
          font-weight: 600;
          cursor: pointer;
          transition: all 0.3s;
          color: #6c757d;
        }

        .ethics-tabs button.active {
          background: #667eea;
          color: white;
        }

        .ethics-tabs button:hover {
          background: #f8f9fa;
        }

        .ethics-content {
          max-width: 1400px;
          margin: 0 auto;
        }

        .ethics-cards {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
          gap: 2rem;
          margin-bottom: 3rem;
        }

        .ethics-card {
          background: white;
          padding: 2rem;
          border-radius: 12px;
          box-shadow: 0 4px 6px rgba(0,0,0,0.1);
          text-align: center;
        }

        .ethics-card h3 {
          margin: 0 0 1rem 0;
          color: #2c3e50;
        }

        .status-indicator {
          margin-bottom: 1rem;
        }

        .status-indicator.active {
          color: #28a745;
          font-weight: 600;
        }

        .metric {
          font-size: 2rem;
          font-weight: bold;
          color: #667eea;
          margin-bottom: 0.5rem;
        }

        .quick-actions {
          background: white;
          padding: 2rem;
          border-radius: 12px;
          box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }

        .quick-actions h3 {
          margin: 0 0 1.5rem 0;
          color: #2c3e50;
        }

        .action-buttons {
          display: flex;
          gap: 1rem;
          flex-wrap: wrap;
        }

        .policy-section {
          background: white;
          padding: 2rem;
          border-radius: 12px;
          box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }

        .policy-header {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          margin-bottom: 2rem;
        }

        .policy-header h2 {
          margin: 0;
          color: #2c3e50;
        }

        .policy-meta {
          text-align: right;
        }

        .policy-meta span {
          display: block;
          color: #6c757d;
          font-size: 0.9rem;
        }

        .accepted {
          color: #28a745 !important;
        }

        .not-accepted {
          color: #dc3545 !important;
        }

        .policy-content .policy-section {
          margin-bottom: 2rem;
          padding-bottom: 2rem;
          border-bottom: 1px solid #eee;
        }

        .policy-content .policy-section:last-child {
          border-bottom: none;
        }

        .policy-content h3 {
          color: #2c3e50;
          margin-bottom: 1rem;
        }

        .policy-content ul {
          margin: 1rem 0;
          padding-left: 1.5rem;
        }

        .policy-content li {
          margin-bottom: 0.5rem;
          color: #6c757d;
        }

        .policy-acceptance {
          text-align: center;
          margin-top: 2rem;
        }

        .transparency-log {
          background: white;
          border-radius: 12px;
          box-shadow: 0 2px 4px rgba(0,0,0,0.1);
          overflow: hidden;
        }

        .transparency-section h2 {
          padding: 2rem 2rem 0 2rem;
          margin: 0 0 2rem 0;
          color: #2c3e50;
        }

        .log-entry {
          padding: 1.5rem 2rem;
          border-bottom: 1px solid #eee;
        }

        .log-entry:last-child {
          border-bottom: none;
        }

        .log-header {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          margin-bottom: 1rem;
        }

        .log-header h4 {
          margin: 0;
          color: #2c3e50;
          text-transform: capitalize;
        }

        .timestamp {
          color: #6c757d;
          font-size: 0.9rem;
        }

        .log-details {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
          gap: 1rem;
          margin-bottom: 1rem;
        }

        .log-details p {
          margin: 0.25rem 0;
          font-size: 0.9rem;
        }

        .log-explanation {
          background: #f8f9fa;
          padding: 1rem;
          border-radius: 6px;
        }

        .log-explanation p {
          margin: 0;
          color: #6c757d;
          font-size: 0.9rem;
        }

        .privacy-controls {
          background: white;
          padding: 2rem;
          border-radius: 12px;
          box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }

        .privacy-section h2 {
          margin-bottom: 2rem;
          color: #2c3e50;
        }

        .control-group {
          margin-bottom: 2rem;
          padding-bottom: 2rem;
          border-bottom: 1px solid #eee;
        }

        .control-group:last-child {
          border-bottom: none;
        }

        .control-group h3 {
          margin: 0 0 1rem 0;
          color: #2c3e50;
        }

        .control-group label {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          cursor: pointer;
          margin-bottom: 0.5rem;
        }

        .control-group select {
          padding: 0.5rem 1rem;
          border: 1px solid #ddd;
          border-radius: 6px;
          font-size: 1rem;
        }

        .control-group p {
          margin: 0.5rem 0 0 0;
          color: #6c757d;
          font-size: 0.9rem;
        }

        .compliance-metrics {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
          gap: 2rem;
          margin-bottom: 3rem;
        }

        .metric-card {
          background: white;
          padding: 2rem;
          border-radius: 12px;
          box-shadow: 0 2px 4px rgba(0,0,0,0.1);
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
          margin-bottom: 0.5rem;
        }

        .status {
          padding: 0.25rem 0.5rem;
          border-radius: 12px;
          font-size: 0.8rem;
          font-weight: 600;
        }

        .status.good { background: #d4edda; color: #155724; }
        .status.warning { background: #fff3cd; color: #856404; }
        .status.info { background: #d1ecf1; color: #0c5460; }

        .recent-issues {
          background: white;
          padding: 2rem;
          border-radius: 12px;
          box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }

        .recent-issues h3 {
          margin: 0 0 2rem 0;
          color: #2c3e50;
        }

        .issues-list {
          display: grid;
          gap: 1rem;
        }

        .issue-item {
          padding: 1.5rem;
          background: #f8f9fa;
          border-radius: 8px;
        }

        .issue-header {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          margin-bottom: 1rem;
        }

        .issue-header h4 {
          margin: 0;
          color: #2c3e50;
          text-transform: capitalize;
        }

        .severity {
          padding: 0.25rem 0.5rem;
          border-radius: 12px;
          font-size: 0.8rem;
          font-weight: 600;
        }

        .severity.low { background: #d4edda; color: #155724; }
        .severity.medium { background: #fff3cd; color: #856404; }
        .severity.high { background: #f8d7da; color: #721c24; }

        .guardrails-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
          gap: 2rem;
        }

        .guardrail-card {
          background: white;
          padding: 2rem;
          border-radius: 12px;
          box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }

        .guardrail-header {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          margin-bottom: 1rem;
        }

        .guardrail-header h3 {
          margin: 0;
          color: #2c3e50;
        }

        .guardrail-header .status {
          padding: 0.25rem 0.5rem;
          border-radius: 12px;
          font-size: 0.8rem;
          font-weight: 600;
        }

        .guardrail-header .status.active { background: #d4edda; color: #155724; }
        .guardrail-header .status.inactive { background: #f8d7da; color: #721c24; }

        .guardrail-details p {
          margin: 0.5rem 0;
          color: #6c757d;
          font-size: 0.9rem;
        }

        .btn {
          padding: 0.5rem 1rem;
          border: none;
          border-radius: 6px;
          cursor: pointer;
          font-weight: 500;
          font-size: 0.9rem;
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

        .btn:hover {
          transform: translateY(-2px);
          box-shadow: 0 4px 12px rgba(0,0,0,0.2);
        }

        @media (max-width: 768px) {
          .ethics-tabs {
            flex-direction: column;
          }

          .ethics-cards, .compliance-metrics {
            grid-template-columns: 1fr;
          }

          .policy-header {
            flex-direction: column;
            gap: 1rem;
            text-align: center;
          }

          .log-details {
            grid-template-columns: 1fr;
          }

          .action-buttons {
            justify-content: center;
          }

          .guardrails-grid {
            grid-template-columns: 1fr;
          }

          .issue-header {
            flex-direction: column;
            gap: 0.5rem;
            text-align: center;
          }
        }
      `}</style>
    </div>
  );
}

export default AIEthicsDashboard;