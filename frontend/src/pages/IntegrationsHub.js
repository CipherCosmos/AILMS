import React, { useEffect, useState } from "react";
import api from "../services/api";

function IntegrationsHub() {
  const [activeTab, setActiveTab] = useState("xr-vr");
  const [xrContent, setXrContent] = useState([]);
  const [jobData, setJobData] = useState(null);
  const [credentials, setCredentials] = useState([]);
  const [marketInsights, setMarketInsights] = useState(null);
  const [selectedSubject, setSelectedSubject] = useState("");
  const [selectedFramework, setSelectedFramework] = useState("");

  useEffect(() => {
    loadData();
  }, [activeTab]);

  const loadData = async () => {
    try {
      if (activeTab === "xr-vr") {
        const response = await api.get("/integrations/xr-vr-content", {
          params: selectedSubject ? { subject: selectedSubject } : {}
        });
        setXrContent(response.data);
      } else if (activeTab === "jobs") {
        const [jobResponse, insightsResponse] = await Promise.all([
          api.get("/integrations/job-market-data"),
          api.get("/integrations/market-insights")
        ]);
        setJobData(jobResponse.data);
        setMarketInsights(insightsResponse.data);
      } else if (activeTab === "credentials") {
        const response = await api.get("/integrations/credential-standards", {
          params: selectedFramework ? { framework: selectedFramework } : {}
        });
        setCredentials(response.data);
      }
    } catch (error) {
      console.error("Error loading integrations data:", error);
    }
  };

  const startXrSession = async (contentId) => {
    try {
      const response = await api.post("/integrations/xr-session", {
        content_id: contentId,
        device_type: "webxr" // Could detect actual device
      });
      alert("XR session started! Opening content...");
      // In a real implementation, this would launch the XR content
    } catch (error) {
      alert("Error starting XR session");
    }
  };

  const verifyCredential = async (credentialId, standardCode) => {
    try {
      const response = await api.post("/integrations/verify-credential", {
        credential_id: credentialId,
        standard_code: standardCode
      });
      alert("Credential verified successfully!");
    } catch (error) {
      alert("Error verifying credential");
    }
  };

  return (
    <div className="integrations-hub">
      <div className="hub-header">
        <h1>🚀 Advanced Integrations</h1>
        <p>Access XR/VR content, job market data, and credential standards</p>
      </div>

      <div className="hub-tabs">
        <button
          className={activeTab === "xr-vr" ? "active" : ""}
          onClick={() => setActiveTab("xr-vr")}
        >
          🕶️ XR/VR Content
        </button>
        <button
          className={activeTab === "jobs" ? "active" : ""}
          onClick={() => setActiveTab("jobs")}
        >
          💼 Job Market
        </button>
        <button
          className={activeTab === "credentials" ? "active" : ""}
          onClick={() => setActiveTab("credentials")}
        >
          🏆 Credentials
        </button>
      </div>

      <div className="hub-content">
        {activeTab === "xr-vr" && (
          <div className="xr-section">
            <div className="section-header">
              <h2>Immersive Learning Experiences</h2>
              <div className="filters">
                <select
                  value={selectedSubject}
                  onChange={(e) => setSelectedSubject(e.target.value)}
                >
                  <option value="">All Subjects</option>
                  <option value="Chemistry">Chemistry</option>
                  <option value="Physics">Physics</option>
                  <option value="Biology">Biology</option>
                  <option value="History">History</option>
                </select>
                <button onClick={loadData}>🔍 Filter</button>
              </div>
            </div>

            <div className="xr-grid">
              {xrContent.map(content => (
                <div key={content._id} className="xr-card">
                  <div className="xr-image">
                    <div className="content-type">{content.type}</div>
                    <img src={content.thumbnail_url} alt={content.title} />
                  </div>
                  <div className="xr-info">
                    <h3>{content.title}</h3>
                    <p className="subject">{content.subject}</p>
                    <p className="description">{content.description}</p>
                    <div className="xr-meta">
                      <span className="duration">⏱️ {content.duration} min</span>
                      <span className="difficulty">{content.difficulty}</span>
                      <span className="rating">⭐ {content.rating}</span>
                    </div>
                    <div className="compatibility">
                      <h4>Compatible Devices:</h4>
                      <div className="devices">
                        {content.compatibility.map(device => (
                          <span key={device} className="device-tag">{device}</span>
                        ))}
                      </div>
                    </div>
                    <button
                      className="btn primary"
                      onClick={() => startXrSession(content._id)}
                    >
                      Launch Experience
                    </button>
                  </div>
                </div>
              ))}
            </div>

            <div className="xr-info-section">
              <h3>Getting Started with XR Learning</h3>
              <div className="info-grid">
                <div className="info-card">
                  <h4>🎧 Device Setup</h4>
                  <p>Ensure your device supports WebXR or has compatible VR/AR hardware</p>
                </div>
                <div className="info-card">
                  <h4>🌐 Browser Requirements</h4>
                  <p>Use Chrome, Firefox, or Safari with WebXR enabled</p>
                </div>
                <div className="info-card">
                  <h4>⚡ Performance Tips</h4>
                  <p>Close other applications for best XR experience</p>
                </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === "jobs" && jobData && marketInsights && (
          <div className="jobs-section">
            <div className="section-header">
              <h2>Job Market Intelligence</h2>
              <p>Real-time insights to guide your career decisions</p>
            </div>

            <div className="market-overview">
              <div className="overview-cards">
                <div className="overview-card">
                  <h3>{jobData.market_overview.total_jobs.toLocaleString()}</h3>
                  <p>Total Job Openings</p>
                  <span className="growth">+{jobData.market_overview.growth_rate}% growth</span>
                </div>
                <div className="overview-card">
                  <h3>{jobData.salary_insights.mid_level.median.toLocaleString()}</h3>
                  <p>Average Mid-Level Salary</p>
                  <span className="range">${jobData.salary_insights.mid_level.range}</span>
                </div>
                <div className="overview-card">
                  <h3>{jobData.market_overview.top_industries[0].jobs.toLocaleString()}</h3>
                  <p>Tech Industry Jobs</p>
                  <span className="growth">+{jobData.market_overview.top_industries[0].growth}% growth</span>
                </div>
              </div>
            </div>

            <div className="skill-demand">
              <h3>🔥 High-Demand Skills</h3>
              <div className="skills-grid">
                {jobData.skill_demand.map(skill => (
                  <div key={skill.skill} className="skill-card">
                    <div className="skill-header">
                      <h4>{skill.skill}</h4>
                      <span className={`trend ${skill.trend}`}>{skill.trend}</span>
                    </div>
                    <div className="skill-metrics">
                      <div className="metric">
                        <span className="value">{skill.demand_score}%</span>
                        <span className="label">Demand</span>
                      </div>
                      <div className="metric">
                        <span className="value">${skill.avg_salary.toLocaleString()}</span>
                        <span className="label">Avg Salary</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="industry-outlook">
              <h3>📈 Industry Growth Projections</h3>
              <div className="industry-grid">
                {marketInsights.industry_outlook.map(industry => (
                  <div key={industry.industry} className="industry-card">
                    <h4>{industry.industry}</h4>
                    <div className="industry-metrics">
                      <div className="metric">
                        <span className="value">+{industry.growth_projection}%</span>
                        <span className="label">Growth</span>
                      </div>
                      <div className="metric">
                        <span className="value">{industry.job_openings_2025.toLocaleString()}</span>
                        <span className="label">Jobs in 2025</span>
                      </div>
                    </div>
                    <div className="emerging-roles">
                      <h5>Emerging Roles:</h5>
                      <ul>
                        {industry.emerging_roles.map(role => (
                          <li key={role}>{role}</li>
                        ))}
                      </ul>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="location-trends">
              <h3>📍 Geographic Salary Trends</h3>
              <div className="location-grid">
                {jobData.location_trends.map(location => (
                  <div key={location.location} className="location-card">
                    <h4>{location.location}</h4>
                    <div className="location-metrics">
                      <div className="metric">
                        <span className="value">${location.avg_salary.toLocaleString()}</span>
                        <span className="label">Avg Salary</span>
                      </div>
                      <div className="metric">
                        <span className="value">{location.job_count.toLocaleString()}</span>
                        <span className="label">Job Openings</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {activeTab === "credentials" && (
          <div className="credentials-section">
            <div className="section-header">
              <h2>Credential Standards & Frameworks</h2>
              <div className="filters">
                <select
                  value={selectedFramework}
                  onChange={(e) => setSelectedFramework(e.target.value)}
                >
                  <option value="">All Frameworks</option>
                  <option value="ISC2">ISC2</option>
                  <option value="AWS">AWS</option>
                  <option value="Google">Google</option>
                  <option value="CompTIA">CompTIA</option>
                </select>
                <button onClick={loadData}>🔍 Filter</button>
              </div>
            </div>

            <div className="credentials-grid">
              {credentials.map(credential => (
                <div key={credential._id} className="credential-card">
                  <div className="credential-header">
                    <h3>{credential.framework}</h3>
                    <span className="code">{credential.code}</span>
                  </div>
                  <p className="description">{credential.description}</p>
                  <div className="credential-meta">
                    <div className="meta-item">
                      <span className="label">Issuer:</span>
                      <span className="value">{credential.issuing_organization}</span>
                    </div>
                    <div className="meta-item">
                      <span className="label">Validity:</span>
                      <span className="value">
                        {credential.validity_period ? `${credential.validity_period} years` : 'Lifetime'}
                      </span>
                    </div>
                    <div className="meta-item">
                      <span className="label">Level:</span>
                      <span className="value">{credential.recognition_level.replace('_', ' ')}</span>
                    </div>
                  </div>

                  <div className="competencies">
                    <h4>Key Competencies:</h4>
                    <div className="competency-list">
                      {credential.competencies.slice(0, 4).map(competency => (
                        <span key={competency} className="competency-tag">{competency}</span>
                      ))}
                      {credential.competencies.length > 4 && (
                        <span className="competency-tag">+{credential.competencies.length - 4} more</span>
                      )}
                    </div>
                  </div>

                  <div className="credential-actions">
                    <button className="btn secondary">View Details</button>
                    <button
                      className="btn primary"
                      onClick={() => verifyCredential(`cred_${credential._id}`, credential.code)}
                    >
                      Verify Credential
                    </button>
                  </div>
                </div>
              ))}
            </div>

            <div className="standards-info">
              <h3>🏆 Industry Recognition</h3>
              <div className="recognition-grid">
                <div className="recognition-card">
                  <h4>ISC2 Certifications</h4>
                  <p>Globally recognized cybersecurity credentials</p>
                  <span className="recognition-badge">Industry Standard</span>
                </div>
                <div className="recognition-card">
                  <h4>AWS Certifications</h4>
                  <p>Cloud computing expertise validation</p>
                  <span className="recognition-badge">Industry Standard</span>
                </div>
                <div className="recognition-card">
                  <h4>Google Career Certificates</h4>
                  <p>Professional skill development programs</p>
                  <span className="recognition-badge">Entry Level</span>
                </div>
                <div className="recognition-card">
                  <h4>CompTIA Certifications</h4>
                  <p>Technology skill validation</p>
                  <span className="recognition-badge">Industry Standard</span>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      <style jsx>{`
        .integrations-hub {
          min-height: 100vh;
          background: #f8f9fa;
          padding: 2rem;
        }

        .hub-header {
          text-align: center;
          margin-bottom: 2rem;
        }

        .hub-header h1 {
          color: #2c3e50;
          margin-bottom: 0.5rem;
        }

        .hub-header p {
          color: #6c757d;
          font-size: 1.1rem;
        }

        .hub-tabs {
          display: flex;
          justify-content: center;
          margin-bottom: 2rem;
          background: white;
          border-radius: 12px;
          padding: 0.5rem;
          box-shadow: 0 2px 4px rgba(0,0,0,0.1);
          flex-wrap: wrap;
        }

        .hub-tabs button {
          padding: 0.75rem 1.5rem;
          border: none;
          background: transparent;
          border-radius: 8px;
          font-weight: 600;
          cursor: pointer;
          transition: all 0.3s;
          color: #6c757d;
        }

        .hub-tabs button.active {
          background: #667eea;
          color: white;
        }

        .hub-tabs button:hover {
          background: #f8f9fa;
        }

        .hub-content {
          max-width: 1400px;
          margin: 0 auto;
        }

        .section-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 2rem;
        }

        .section-header h2 {
          color: #2c3e50;
          margin: 0;
        }

        .filters {
          display: flex;
          gap: 1rem;
          align-items: center;
        }

        .filters select {
          padding: 0.5rem 1rem;
          border: 1px solid #ddd;
          border-radius: 6px;
        }

        .filters button {
          padding: 0.5rem 1rem;
          background: #667eea;
          color: white;
          border: none;
          border-radius: 6px;
          cursor: pointer;
        }

        .xr-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
          gap: 2rem;
          margin-bottom: 3rem;
        }

        .xr-card {
          background: white;
          border-radius: 12px;
          overflow: hidden;
          box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }

        .xr-image {
          position: relative;
          height: 200px;
          background: linear-gradient(135deg, #667eea, #764ba2);
        }

        .content-type {
          position: absolute;
          top: 1rem;
          right: 1rem;
          background: rgba(255,255,255,0.9);
          color: #2c3e50;
          padding: 0.25rem 0.5rem;
          border-radius: 12px;
          font-size: 0.8rem;
          font-weight: 600;
        }

        .xr-image img {
          width: 100%;
          height: 100%;
          object-fit: cover;
        }

        .xr-info {
          padding: 1.5rem;
        }

        .xr-info h3 {
          margin: 0 0 0.5rem 0;
          color: #2c3e50;
        }

        .subject {
          color: #667eea;
          font-weight: 600;
          margin: 0 0 1rem 0;
        }

        .description {
          color: #6c757d;
          margin: 0 0 1rem 0;
          line-height: 1.5;
        }

        .xr-meta {
          display: flex;
          gap: 1rem;
          margin-bottom: 1rem;
          flex-wrap: wrap;
        }

        .duration, .difficulty, .rating {
          font-size: 0.9rem;
          color: #495057;
        }

        .compatibility {
          margin-bottom: 1.5rem;
        }

        .compatibility h4 {
          margin: 0 0 0.5rem 0;
          color: #2c3e50;
          font-size: 0.9rem;
        }

        .devices {
          display: flex;
          flex-wrap: wrap;
          gap: 0.5rem;
        }

        .device-tag {
          background: #e9ecef;
          color: #495057;
          padding: 0.25rem 0.5rem;
          border-radius: 12px;
          font-size: 0.8rem;
        }

        .xr-info-section {
          background: white;
          padding: 2rem;
          border-radius: 12px;
          box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }

        .xr-info-section h3 {
          margin: 0 0 2rem 0;
          color: #2c3e50;
        }

        .info-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
          gap: 1.5rem;
        }

        .info-card {
          padding: 1.5rem;
          background: #f8f9fa;
          border-radius: 8px;
          text-align: center;
        }

        .info-card h4 {
          margin: 0 0 1rem 0;
          color: #2c3e50;
        }

        .info-card p {
          margin: 0;
          color: #6c757d;
          font-size: 0.9rem;
        }

        .market-overview {
          background: white;
          padding: 2rem;
          border-radius: 12px;
          box-shadow: 0 2px 4px rgba(0,0,0,0.1);
          margin-bottom: 2rem;
        }

        .overview-cards {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
          gap: 2rem;
        }

        .overview-card {
          text-align: center;
          padding: 2rem;
          background: #f8f9fa;
          border-radius: 8px;
        }

        .overview-card h3 {
          margin: 0 0 0.5rem 0;
          color: #667eea;
          font-size: 2rem;
        }

        .overview-card p {
          margin: 0 0 1rem 0;
          color: #6c757d;
        }

        .growth, .range {
          color: #28a745;
          font-size: 0.9rem;
          font-weight: 600;
        }

        .skill-demand, .industry-outlook, .location-trends {
          background: white;
          padding: 2rem;
          border-radius: 12px;
          box-shadow: 0 2px 4px rgba(0,0,0,0.1);
          margin-bottom: 2rem;
        }

        .skill-demand h3, .industry-outlook h3, .location-trends h3 {
          margin: 0 0 2rem 0;
          color: #2c3e50;
        }

        .skills-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
          gap: 1.5rem;
        }

        .skill-card {
          padding: 1.5rem;
          background: #f8f9fa;
          border-radius: 8px;
        }

        .skill-header {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          margin-bottom: 1rem;
        }

        .skill-header h4 {
          margin: 0;
          color: #2c3e50;
        }

        .trend {
          padding: 0.25rem 0.5rem;
          border-radius: 12px;
          font-size: 0.8rem;
          font-weight: 600;
        }

        .trend.rising { background: #d4edda; color: #155724; }
        .trend.stable { background: #fff3cd; color: #856404; }

        .skill-metrics {
          display: flex;
          gap: 2rem;
        }

        .metric {
          text-align: center;
        }

        .metric .value {
          display: block;
          font-size: 1.25rem;
          font-weight: bold;
          color: #667eea;
        }

        .metric .label {
          font-size: 0.9rem;
          color: #6c757d;
        }

        .industry-grid, .location-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
          gap: 1.5rem;
        }

        .industry-card, .location-card {
          padding: 1.5rem;
          background: #f8f9fa;
          border-radius: 8px;
        }

        .industry-card h4, .location-card h4 {
          margin: 0 0 1rem 0;
          color: #2c3e50;
        }

        .industry-metrics, .location-metrics {
          display: flex;
          gap: 2rem;
          margin-bottom: 1rem;
        }

        .emerging-roles h5 {
          margin: 1rem 0 0.5rem 0;
          color: #2c3e50;
          font-size: 0.9rem;
        }

        .emerging-roles ul {
          margin: 0;
          padding-left: 1rem;
        }

        .emerging-roles li {
          color: #6c757d;
          font-size: 0.9rem;
        }

        .credentials-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
          gap: 2rem;
          margin-bottom: 3rem;
        }

        .credential-card {
          background: white;
          padding: 2rem;
          border-radius: 12px;
          box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }

        .credential-header {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          margin-bottom: 1rem;
        }

        .credential-header h3 {
          margin: 0;
          color: #2c3e50;
        }

        .code {
          background: #667eea;
          color: white;
          padding: 0.25rem 0.5rem;
          border-radius: 12px;
          font-size: 0.8rem;
          font-weight: 600;
        }

        .description {
          color: #6c757d;
          margin: 0 0 1.5rem 0;
          line-height: 1.5;
        }

        .credential-meta {
          display: grid;
          grid-template-columns: 1fr;
          gap: 0.5rem;
          margin-bottom: 1.5rem;
        }

        .meta-item {
          display: flex;
          justify-content: space-between;
          align-items: center;
        }

        .meta-item .label {
          font-weight: 600;
          color: #2c3e50;
        }

        .meta-item .value {
          color: #6c757d;
        }

        .competencies h4 {
          margin: 0 0 0.5rem 0;
          color: #2c3e50;
          font-size: 0.9rem;
        }

        .competency-list {
          display: flex;
          flex-wrap: wrap;
          gap: 0.5rem;
        }

        .competency-tag {
          background: #e9ecef;
          color: #495057;
          padding: 0.25rem 0.5rem;
          border-radius: 12px;
          font-size: 0.8rem;
        }

        .credential-actions {
          display: flex;
          gap: 1rem;
          margin-top: 1.5rem;
        }

        .standards-info {
          background: white;
          padding: 2rem;
          border-radius: 12px;
          box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }

        .standards-info h3 {
          margin: 0 0 2rem 0;
          color: #2c3e50;
        }

        .recognition-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
          gap: 1.5rem;
        }

        .recognition-card {
          padding: 1.5rem;
          background: #f8f9fa;
          border-radius: 8px;
          text-align: center;
        }

        .recognition-card h4 {
          margin: 0 0 0.5rem 0;
          color: #2c3e50;
        }

        .recognition-card p {
          margin: 0 0 1rem 0;
          color: #6c757d;
          font-size: 0.9rem;
        }

        .recognition-badge {
          background: #28a745;
          color: white;
          padding: 0.25rem 0.5rem;
          border-radius: 12px;
          font-size: 0.8rem;
          font-weight: 600;
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
          .hub-tabs {
            flex-direction: column;
          }

          .section-header {
            flex-direction: column;
            gap: 1rem;
            text-align: center;
          }

          .xr-grid, .credentials-grid {
            grid-template-columns: 1fr;
          }

          .overview-cards, .skills-grid, .industry-grid, .location-grid {
            grid-template-columns: 1fr;
          }

          .info-grid, .recognition-grid {
            grid-template-columns: 1fr;
          }

          .filters {
            justify-content: center;
          }

          .xr-meta, .industry-metrics, .location-metrics {
            flex-direction: column;
            gap: 0.5rem;
          }

          .credential-actions {
            flex-direction: column;
          }
        }
      `}</style>
    </div>
  );
}

export default IntegrationsHub;