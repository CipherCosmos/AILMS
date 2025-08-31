import React, { useEffect, useState } from "react";
import api from "../services/api";

function AlumniNetwork() {
  const [activeTab, setActiveTab] = useState("directory");
  const [alumni, setAlumni] = useState([]);
  const [mentorshipRequests, setMentorshipRequests] = useState([]);
  const [events, setEvents] = useState([]);
  const [searchTerm, setSearchTerm] = useState("");
  const [filters, setFilters] = useState({
    industry: "",
    graduation_year: "",
    location: "",
    skills: ""
  });

  useEffect(() => {
    loadAlumniData();
  }, [activeTab]);

  const loadAlumniData = async () => {
    try {
      const [alumniRes, mentorshipRes, eventsRes] = await Promise.all([
        api.get("/alumni/directory", { params: { search: searchTerm, ...filters } }),
        api.get("/alumni/mentorship/requests"),
        api.get("/alumni/events")
      ]);
      setAlumni(alumniRes.data);
      setMentorshipRequests(mentorshipRes.data);
      setEvents(eventsRes.data);
    } catch (error) {
      console.error("Error loading alumni data:", error);
    }
  };

  const requestMentorship = async (alumniId) => {
    try {
      await api.post(`/alumni/mentorship/request/${alumniId}`, {
        message: "I'd like to connect with you for career guidance."
      });
      alert("Mentorship request sent!");
      loadAlumniData();
    } catch (error) {
      alert("Error sending mentorship request");
    }
  };

  const joinEvent = async (eventId) => {
    try {
      await api.post(`/alumni/events/${eventId}/join`);
      alert("Successfully joined the event!");
      loadAlumniData();
    } catch (error) {
      alert("Error joining event");
    }
  };

  const filteredAlumni = alumni.filter(person =>
    person.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    person.industry?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    person.current_position?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="alumni-network">
      <div className="alumni-header">
        <h1>🎓 Alumni Network</h1>
        <p>Connect with fellow graduates, find mentors, and build your professional network</p>
      </div>

      <div className="alumni-tabs">
        <button
          className={activeTab === "directory" ? "active" : ""}
          onClick={() => setActiveTab("directory")}
        >
          Alumni Directory
        </button>
        <button
          className={activeTab === "mentorship" ? "active" : ""}
          onClick={() => setActiveTab("mentorship")}
        >
          Mentorship
        </button>
        <button
          className={activeTab === "events" ? "active" : ""}
          onClick={() => setActiveTab("events")}
        >
          Events & Reunions
        </button>
        <button
          className={activeTab === "opportunities" ? "active" : ""}
          onClick={() => setActiveTab("opportunities")}
        >
          Opportunities
        </button>
      </div>

      <div className="alumni-content">
        {activeTab === "directory" && (
          <div className="directory-section">
            <div className="directory-header">
              <h2>Alumni Directory</h2>
              <div className="directory-controls">
                <input
                  type="text"
                  placeholder="Search alumni..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="search-input"
                />
                <select
                  value={filters.industry}
                  onChange={(e) => setFilters({...filters, industry: e.target.value})}
                >
                  <option value="">All Industries</option>
                  <option value="technology">Technology</option>
                  <option value="finance">Finance</option>
                  <option value="healthcare">Healthcare</option>
                  <option value="education">Education</option>
                </select>
              </div>
            </div>

            <div className="alumni-grid">
              {filteredAlumni.map(person => (
                <div key={person.id} className="alumni-card">
                  <div className="alumni-avatar">
                    <span>{person.name.charAt(0).toUpperCase()}</span>
                  </div>
                  <div className="alumni-info">
                    <h3>{person.name}</h3>
                    <p className="current-position">{person.current_position}</p>
                    <p className="company">{person.company}</p>
                    <div className="alumni-details">
                      <span className="graduation-year">🎓 {person.graduation_year}</span>
                      <span className="location">📍 {person.location}</span>
                    </div>
                    <div className="alumni-skills">
                      {person.skills?.slice(0, 3).map(skill => (
                        <span key={skill} className="skill-tag">{skill}</span>
                      ))}
                    </div>
                    <div className="alumni-actions">
                      <button
                        className="btn small primary"
                        onClick={() => requestMentorship(person.id)}
                      >
                        Request Mentorship
                      </button>
                      <button className="btn small secondary">
                        View Profile
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {activeTab === "mentorship" && (
          <div className="mentorship-section">
            <div className="mentorship-header">
              <h2>Mentorship Program</h2>
              <p>Connect with experienced alumni for career guidance</p>
            </div>

            <div className="mentorship-stats">
              <div className="stat-card">
                <h3>Active Mentors</h3>
                <div className="stat-value">{alumni.filter(a => a.available_for_mentoring).length}</div>
              </div>
              <div className="stat-card">
                <h3>Mentorship Requests</h3>
                <div className="stat-value">{mentorshipRequests.length}</div>
              </div>
              <div className="stat-card">
                <h3>Success Rate</h3>
                <div className="stat-value">85%</div>
              </div>
            </div>

            <div className="mentorship-requests">
              <h3>Your Mentorship Requests</h3>
              {mentorshipRequests.map(request => (
                <div key={request.id} className="request-card">
                  <div className="request-info">
                    <h4>{request.mentor_name}</h4>
                    <p>{request.message}</p>
                    <span className={`status ${request.status}`}>{request.status}</span>
                  </div>
                  <div className="request-date">
                    {new Date(request.created_at).toLocaleDateString()}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {activeTab === "events" && (
          <div className="events-section">
            <div className="events-header">
              <h2>Alumni Events & Reunions</h2>
              <p>Stay connected through virtual and in-person events</p>
            </div>

            <div className="events-grid">
              {events.map(event => (
                <div key={event.id} className="event-card">
                  <div className="event-image">
                    <span>{event.type === "virtual" ? "💻" : "🏛️"}</span>
                  </div>
                  <div className="event-info">
                    <h3>{event.title}</h3>
                    <p>{event.description}</p>
                    <div className="event-details">
                      <span>📅 {new Date(event.date).toLocaleDateString()}</span>
                      <span>🕐 {event.time}</span>
                      <span>📍 {event.location || "Virtual"}</span>
                    </div>
                    <div className="event-attendees">
                      <span>{event.attendee_count} attending</span>
                    </div>
                    <button
                      className="btn primary"
                      onClick={() => joinEvent(event.id)}
                    >
                      {event.is_registered ? "Registered" : "Join Event"}
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {activeTab === "opportunities" && (
          <div className="opportunities-section">
            <h2>Career Opportunities</h2>
            <p>Exclusive job opportunities shared by alumni</p>

            <div className="opportunities-grid">
              <div className="opportunity-card">
                <h3>Software Engineer at TechCorp</h3>
                <p>Posted by Sarah Johnson (Class of 2018)</p>
                <div className="opportunity-details">
                  <span>📍 San Francisco, CA</span>
                  <span>💰 $120k - $150k</span>
                  <span>🏢 Full-time</span>
                </div>
                <button className="btn primary">Apply Now</button>
              </div>

              <div className="opportunity-card">
                <h3>Marketing Manager at GrowthCo</h3>
                <p>Posted by Michael Chen (Class of 2019)</p>
                <div className="opportunity-details">
                  <span>📍 New York, NY</span>
                  <span>💰 $90k - $110k</span>
                  <span>🏢 Full-time</span>
                </div>
                <button className="btn primary">Apply Now</button>
              </div>
            </div>
          </div>
        )}
      </div>

      <style jsx>{`
        .alumni-network {
          min-height: 100vh;
          background: #f8f9fa;
          padding: 2rem;
        }

        .alumni-header {
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          color: white;
          padding: 2rem;
          border-radius: 12px;
          margin-bottom: 2rem;
        }

        .alumni-tabs {
          display: flex;
          background: white;
          border-radius: 12px;
          padding: 0.5rem;
          margin-bottom: 2rem;
          box-shadow: 0 2px 4px rgba(0,0,0,0.1);
          overflow-x: auto;
        }

        .alumni-tabs button {
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

        .alumni-tabs button.active {
          background: #667eea;
          color: white;
        }

        .alumni-content {
          background: white;
          border-radius: 12px;
          padding: 2rem;
          box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }

        .directory-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 2rem;
        }

        .directory-controls {
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

        .alumni-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
          gap: 1.5rem;
        }

        .alumni-card {
          border: 1px solid #e9ecef;
          border-radius: 12px;
          padding: 1.5rem;
          background: white;
          transition: transform 0.3s;
        }

        .alumni-card:hover {
          transform: translateY(-2px);
          box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        }

        .alumni-avatar {
          width: 60px;
          height: 60px;
          border-radius: 50%;
          background: linear-gradient(135deg, #667eea, #764ba2);
          display: flex;
          align-items: center;
          justify-content: center;
          color: white;
          font-size: 1.5rem;
          font-weight: bold;
          margin-bottom: 1rem;
        }

        .alumni-info h3 {
          margin: 0 0 0.5rem 0;
          color: #2c3e50;
        }

        .current-position {
          color: #667eea;
          font-weight: 600;
          margin: 0.25rem 0;
        }

        .company {
          color: #6c757d;
          margin: 0.25rem 0;
        }

        .alumni-details {
          display: flex;
          gap: 1rem;
          margin: 1rem 0;
          font-size: 0.9rem;
          color: #6c757d;
        }

        .alumni-skills {
          display: flex;
          flex-wrap: wrap;
          gap: 0.5rem;
          margin: 1rem 0;
        }

        .skill-tag {
          padding: 0.25rem 0.5rem;
          background: #e9ecef;
          color: #495057;
          border-radius: 12px;
          font-size: 0.8rem;
        }

        .alumni-actions {
          display: flex;
          gap: 0.5rem;
          margin-top: 1rem;
        }

        .mentorship-stats {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
          gap: 1rem;
          margin: 2rem 0;
        }

        .stat-card {
          background: white;
          padding: 1.5rem;
          border-radius: 8px;
          box-shadow: 0 2px 4px rgba(0,0,0,0.1);
          text-align: center;
        }

        .stat-card h3 {
          margin: 0 0 1rem 0;
          color: #6c757d;
          font-size: 0.9rem;
        }

        .stat-value {
          font-size: 2rem;
          font-weight: bold;
          color: #667eea;
        }

        .mentorship-requests {
          margin-top: 2rem;
        }

        .request-card {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 1rem;
          border: 1px solid #e9ecef;
          border-radius: 8px;
          margin-bottom: 1rem;
        }

        .request-info h4 {
          margin: 0 0 0.5rem 0;
          color: #2c3e50;
        }

        .status {
          padding: 0.25rem 0.75rem;
          border-radius: 12px;
          font-size: 0.8rem;
          font-weight: 600;
        }

        .status.pending {
          background: #fff3cd;
          color: #856404;
        }

        .status.accepted {
          background: #d4edda;
          color: #155724;
        }

        .events-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(400px, 1fr));
          gap: 1.5rem;
        }

        .event-card {
          border: 1px solid #e9ecef;
          border-radius: 12px;
          overflow: hidden;
          background: white;
        }

        .event-image {
          height: 150px;
          background: linear-gradient(135deg, #667eea, #764ba2);
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 3rem;
          color: white;
        }

        .event-info {
          padding: 1.5rem;
        }

        .event-info h3 {
          margin: 0 0 0.5rem 0;
          color: #2c3e50;
        }

        .event-details {
          display: flex;
          flex-direction: column;
          gap: 0.5rem;
          margin: 1rem 0;
          font-size: 0.9rem;
          color: #6c757d;
        }

        .event-attendees {
          margin: 1rem 0;
          font-size: 0.9rem;
          color: #6c757d;
        }

        .opportunities-grid {
          display: grid;
          gap: 1rem;
          margin-top: 2rem;
        }

        .opportunity-card {
          border: 1px solid #e9ecef;
          border-radius: 8px;
          padding: 1.5rem;
          background: white;
        }

        .opportunity-card h3 {
          margin: 0 0 0.5rem 0;
          color: #2c3e50;
        }

        .opportunity-details {
          display: flex;
          gap: 1rem;
          margin: 1rem 0;
          font-size: 0.9rem;
          color: #6c757d;
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
          background: #667eea;
          color: white;
        }

        .btn.secondary {
          background: #6c757d;
          color: white;
        }

        .btn.small {
          padding: 0.375rem 0.75rem;
          font-size: 0.875rem;
        }

        @media (max-width: 768px) {
          .alumni-network {
            padding: 1rem;
          }

          .alumni-grid {
            grid-template-columns: 1fr;
          }

          .events-grid {
            grid-template-columns: 1fr;
          }

          .directory-header {
            flex-direction: column;
            align-items: flex-start;
            gap: 1rem;
          }

          .directory-controls {
            flex-direction: column;
            width: 100%;
          }

          .search-input {
            width: 100%;
          }

          .alumni-details {
            flex-direction: column;
            gap: 0.5rem;
          }

          .event-details {
            gap: 0.25rem;
          }

          .opportunity-details {
            flex-direction: column;
            gap: 0.25rem;
          }
        }
      `}</style>
    </div>
  );
}

export default AlumniNetwork;