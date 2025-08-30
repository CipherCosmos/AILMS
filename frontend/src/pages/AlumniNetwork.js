import React, { useEffect, useState } from "react";
import api from "../services/api";

function AlumniNetwork({ me }) {
  const [alumni, setAlumni] = useState([]);
  const [posts, setPosts] = useState([]);
  const [events, setEvents] = useState([]);
  const [jobs, setJobs] = useState([]);
  const [mentorshipRequests, setMentorshipRequests] = useState([]);
  const [activeTab, setActiveTab] = useState("network");
  const [newPost, setNewPost] = useState("");
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedAlumni, setSelectedAlumni] = useState(null);

  useEffect(() => {
    loadAlumni();
    loadPosts();
    loadEvents();
    loadJobs();
    loadMentorshipRequests();
  }, []);

  const loadAlumni = async () => {
    try {
      // Mock data - would come from API
      setAlumni([
        {
          id: "alumni1",
          name: "Sarah Chen",
          graduationYear: 2020,
          currentPosition: "Software Engineer at Google",
          company: "Google",
          location: "Mountain View, CA",
          skills: ["JavaScript", "Python", "Machine Learning"],
          avatar: "👩‍💻",
          linkedin: "https://linkedin.com/in/sarahchen",
          email: "sarah.chen@email.com",
          bio: "Passionate about AI and education technology. Always happy to help fellow alumni!",
          achievements: ["Dean's List 2018-2020", "AI Research Award", "Hackathon Winner"]
        },
        {
          id: "alumni2",
          name: "Marcus Rodriguez",
          graduationYear: 2019,
          currentPosition: "Product Manager at Meta",
          company: "Meta",
          location: "Menlo Park, CA",
          skills: ["Product Strategy", "Data Analysis", "UX Design"],
          avatar: "👨‍💼",
          linkedin: "https://linkedin.com/in/marcusr",
          email: "marcus.rodriguez@email.com",
          bio: "Product management enthusiast. Love mentoring students interested in tech product roles.",
          achievements: ["Outstanding Graduate", "Product Launch Success", "Mentor of the Year"]
        },
        {
          id: "alumni3",
          name: "Dr. Emily Watson",
          graduationYear: 2015,
          currentPosition: "Research Scientist at DeepMind",
          company: "DeepMind",
          location: "London, UK",
          skills: ["AI Research", "Neural Networks", "Academic Writing"],
          avatar: "👩‍🔬",
          linkedin: "https://linkedin.com/in/emilywatson",
          email: "emily.watson@email.com",
          bio: "AI researcher with a passion for advancing machine learning. Available for research discussions.",
          achievements: ["PhD in AI", "Published 15+ Papers", "Best Researcher Award"]
        }
      ]);
    } catch (error) {
      console.error("Error loading alumni:", error);
    }
  };

  const loadPosts = async () => {
    try {
      // Mock data - would come from API
      setPosts([
        {
          id: "post1",
          author: "Sarah Chen",
          authorId: "alumni1",
          content: "Excited to announce that our startup just raised $2M in Series A funding! Big thanks to the entrepreneurial spirit I developed during my time at the university. #Entrepreneurship #Success",
          timestamp: "2024-01-25T10:30:00Z",
          likes: 24,
          comments: 8,
          tags: ["entrepreneurship", "success", "startup"],
          type: "achievement"
        },
        {
          id: "post2",
          author: "Marcus Rodriguez",
          authorId: "alumni2",
          content: "Looking for talented product managers to join our team at Meta! If you're a recent graduate with PM aspirations, I'd love to chat about opportunities. DM me for more details.",
          timestamp: "2024-01-24T15:45:00Z",
          likes: 18,
          comments: 12,
          tags: ["job", "mentorship", "product"],
          type: "opportunity"
        },
        {
          id: "post3",
          author: "Dr. Emily Watson",
          authorId: "alumni3",
          content: "Just published a new paper on 'Ethical AI in Education' in Nature Machine Intelligence. The research builds on my thesis work from grad school. Proud to see how far the field has come! 📄🤖",
          timestamp: "2024-01-23T09:15:00Z",
          likes: 31,
          comments: 15,
          tags: ["research", "ai", "ethics"],
          type: "academic"
        }
      ]);
    } catch (error) {
      console.error("Error loading posts:", error);
    }
  };

  const loadEvents = async () => {
    try {
      // Mock data - would come from API
      setEvents([
        {
          id: "event1",
          title: "Alumni Networking Mixer",
          date: "2024-02-15T18:00:00Z",
          location: "San Francisco, CA",
          description: "Connect with fellow alumni over drinks and appetizers. Network, share experiences, and build lasting professional relationships.",
          attendees: 45,
          maxAttendees: 100,
          organizer: "Alumni Association",
          type: "networking"
        },
        {
          id: "event2",
          title: "Tech Career Panel",
          date: "2024-02-20T14:00:00Z",
          location: "Virtual",
          description: "Hear from successful alumni in tech careers. Panel includes engineers, product managers, and startup founders sharing their journeys and advice.",
          attendees: 120,
          maxAttendees: 200,
          organizer: "Career Services",
          type: "career"
        },
        {
          id: "event3",
          title: "AI & ML Workshop",
          date: "2024-03-05T10:00:00Z",
          location: "New York, NY",
          description: "Hands-on workshop on latest AI/ML techniques. Perfect for staying current with industry trends.",
          attendees: 25,
          maxAttendees: 50,
          organizer: "Tech Committee",
          type: "workshop"
        }
      ]);
    } catch (error) {
      console.error("Error loading events:", error);
    }
  };

  const loadJobs = async () => {
    try {
      // Mock data - would come from API
      setJobs([
        {
          id: "job1",
          title: "Senior Software Engineer",
          company: "Google",
          location: "Mountain View, CA",
          type: "Full-time",
          salary: "$150k - $220k",
          description: "Join our team building the next generation of AI-powered applications. Looking for experienced engineers with a passion for machine learning.",
          requirements: ["5+ years experience", "Python, JavaScript", "ML/AI experience"],
          postedBy: "Sarah Chen",
          postedDate: "2024-01-20",
          applicationDeadline: "2024-02-20"
        },
        {
          id: "job2",
          title: "Product Manager",
          company: "Meta",
          location: "Menlo Park, CA",
          type: "Full-time",
          salary: "$130k - $180k",
          description: "Drive product strategy for our education technology initiatives. Work with cross-functional teams to deliver innovative solutions.",
          requirements: ["3+ years PM experience", "Technical background", "Education domain knowledge"],
          postedBy: "Marcus Rodriguez",
          postedDate: "2024-01-22",
          applicationDeadline: "2024-02-15"
        }
      ]);
    } catch (error) {
      console.error("Error loading jobs:", error);
    }
  };

  const loadMentorshipRequests = async () => {
    try {
      // Mock data - would come from API
      setMentorshipRequests([
        {
          id: "request1",
          menteeName: "Alex Johnson",
          menteeYear: "Junior",
          requestedSkills: ["Career Advice", "Interview Prep", "Networking"],
          message: "Hi! I'm interested in pursuing a career in tech and would love some guidance on breaking into the industry.",
          status: "pending"
        },
        {
          id: "request2",
          menteeName: "Maria Garcia",
          menteeYear: "Senior",
          requestedSkills: ["Research", "Academic Writing", "PhD Applications"],
          message: "I'm considering graduate school and would appreciate advice on the application process and research opportunities.",
          status: "accepted"
        }
      ]);
    } catch (error) {
      console.error("Error loading mentorship requests:", error);
    }
  };

  const createPost = async () => {
    if (!newPost.trim()) return;

    try {
      // In a real implementation, this would call the API
      const post = {
        id: Date.now().toString(),
        author: me?.name || "Anonymous",
        authorId: me?.id || "anonymous",
        content: newPost,
        timestamp: new Date().toISOString(),
        likes: 0,
        comments: 0,
        tags: [],
        type: "general"
      };

      setPosts(prev => [post, ...prev]);
      setNewPost("");
    } catch (error) {
      console.error("Error creating post:", error);
    }
  };

  const connectWithAlumni = async (alumniId) => {
    try {
      // In a real implementation, this would send a connection request
      alert(`Connection request sent to ${alumni.find(a => a.id === alumniId)?.name}!`);
    } catch (error) {
      console.error("Error sending connection request:", error);
    }
  };

  const filteredAlumni = alumni.filter(alumni =>
    alumni.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    alumni.company.toLowerCase().includes(searchTerm.toLowerCase()) ||
    alumni.skills.some(skill => skill.toLowerCase().includes(searchTerm.toLowerCase()))
  );

  return (
    <div className="alumni-network">
      <div className="network-header">
        <h1>🎓 Alumni Network</h1>
        <p>Stay connected, grow your network, and give back to the community</p>
      </div>

      <div className="network-tabs">
        <button
          className={activeTab === "network" ? "active" : ""}
          onClick={() => setActiveTab("network")}
        >
          Network
        </button>
        <button
          className={activeTab === "feed" ? "active" : ""}
          onClick={() => setActiveTab("feed")}
        >
          Feed
        </button>
        <button
          className={activeTab === "events" ? "active" : ""}
          onClick={() => setActiveTab("events")}
        >
          Events
        </button>
        <button
          className={activeTab === "jobs" ? "active" : ""}
          onClick={() => setActiveTab("jobs")}
        >
          Jobs
        </button>
        <button
          className={activeTab === "mentorship" ? "active" : ""}
          onClick={() => setActiveTab("mentorship")}
        >
          Mentorship
        </button>
      </div>

      <div className="network-content">
        {activeTab === "network" && (
          <div className="network-section">
            <div className="search-section">
              <input
                type="text"
                placeholder="Search alumni by name, company, or skills..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="search-input"
              />
            </div>

            <div className="alumni-grid">
              {filteredAlumni.map(alumni => (
                <div key={alumni.id} className="alumni-card">
                  <div className="alumni-header">
                    <div className="alumni-avatar">{alumni.avatar}</div>
                    <div className="alumni-basic">
                      <h3>{alumni.name}</h3>
                      <p className="graduation">Class of {alumni.graduationYear}</p>
                    </div>
                  </div>

                  <div className="alumni-details">
                    <div className="current-role">
                      <h4>{alumni.currentPosition}</h4>
                      <p>{alumni.company} • {alumni.location}</p>
                    </div>

                    <div className="skills-section">
                      <h5>Skills & Expertise</h5>
                      <div className="skills-list">
                        {alumni.skills.map(skill => (
                          <span key={skill} className="skill-tag">{skill}</span>
                        ))}
                      </div>
                    </div>

                    <div className="bio-section">
                      <p className="bio">{alumni.bio}</p>
                    </div>

                    <div className="achievements-section">
                      <h5>Achievements</h5>
                      <ul className="achievements-list">
                        {alumni.achievements.map((achievement, index) => (
                          <li key={index}>{achievement}</li>
                        ))}
                      </ul>
                    </div>
                  </div>

                  <div className="alumni-actions">
                    <button
                      className="btn primary"
                      onClick={() => connectWithAlumni(alumni.id)}
                    >
                      Connect
                    </button>
                    <button
                      className="btn secondary"
                      onClick={() => setSelectedAlumni(alumni)}
                    >
                      View Profile
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {activeTab === "feed" && (
          <div className="feed-section">
            <div className="create-post">
              <textarea
                value={newPost}
                onChange={(e) => setNewPost(e.target.value)}
                placeholder="Share your achievements, opportunities, or insights with the alumni community..."
                rows={3}
                className="post-input"
              />
              <button
                className="btn primary"
                onClick={createPost}
                disabled={!newPost.trim()}
              >
                Post
              </button>
            </div>

            <div className="posts-feed">
              {posts.map(post => (
                <div key={post.id} className="post-card">
                  <div className="post-header">
                    <div className="post-author">
                      <div className="author-avatar">
                        {alumni.find(a => a.id === post.authorId)?.avatar || "👤"}
                      </div>
                      <div className="author-info">
                        <h4>{post.author}</h4>
                        <span className="post-time">
                          {new Date(post.timestamp).toLocaleDateString()}
                        </span>
                      </div>
                    </div>
                    <div className="post-type">
                      {post.type === "achievement" && "🏆"}
                      {post.type === "opportunity" && "💼"}
                      {post.type === "academic" && "📚"}
                    </div>
                  </div>

                  <div className="post-content">
                    <p>{post.content}</p>
                    {post.tags.length > 0 && (
                      <div className="post-tags">
                        {post.tags.map(tag => (
                          <span key={tag} className="tag">#{tag}</span>
                        ))}
                      </div>
                    )}
                  </div>

                  <div className="post-actions">
                    <button className="action-btn">
                      👍 {post.likes}
                    </button>
                    <button className="action-btn">
                      💬 {post.comments}
                    </button>
                    <button className="action-btn">
                      🔗 Share
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {activeTab === "events" && (
          <div className="events-section">
            <h2>Upcoming Events</h2>
            <div className="events-grid">
              {events.map(event => (
                <div key={event.id} className="event-card">
                  <div className="event-header">
                    <h3>{event.title}</h3>
                    <div className="event-type">{event.type}</div>
                  </div>

                  <div className="event-details">
                    <div className="event-date">
                      📅 {new Date(event.date).toLocaleDateString()}
                    </div>
                    <div className="event-location">
                      📍 {event.location}
                    </div>
                    <div className="event-attendees">
                      👥 {event.attendees}/{event.maxAttendees} attending
                    </div>
                  </div>

                  <div className="event-description">
                    <p>{event.description}</p>
                  </div>

                  <div className="event-organizer">
                    <small>Organized by: {event.organizer}</small>
                  </div>

                  <div className="event-actions">
                    <button className="btn primary">RSVP</button>
                    <button className="btn secondary">Learn More</button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {activeTab === "jobs" && (
          <div className="jobs-section">
            <h2>Job Opportunities</h2>
            <div className="jobs-list">
              {jobs.map(job => (
                <div key={job.id} className="job-card">
                  <div className="job-header">
                    <h3>{job.title}</h3>
                    <div className="job-company">{job.company}</div>
                  </div>

                  <div className="job-details">
                    <div className="job-location">📍 {job.location}</div>
                    <div className="job-type">💼 {job.type}</div>
                    <div className="job-salary">💰 {job.salary}</div>
                  </div>

                  <div className="job-description">
                    <p>{job.description}</p>
                  </div>

                  <div className="job-requirements">
                    <h4>Requirements:</h4>
                    <ul>
                      {job.requirements.map((req, index) => (
                        <li key={index}>{req}</li>
                      ))}
                    </ul>
                  </div>

                  <div className="job-footer">
                    <div className="job-poster">
                      Posted by {job.postedBy} • {new Date(job.postedDate).toLocaleDateString()}
                    </div>
                    <div className="job-deadline">
                      Apply by {new Date(job.applicationDeadline).toLocaleDateString()}
                    </div>
                  </div>

                  <div className="job-actions">
                    <button className="btn primary">Apply Now</button>
                    <button className="btn secondary">Save Job</button>
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
              <p>Connect with experienced alumni for career guidance and professional development</p>
            </div>

            <div className="mentorship-content">
              <div className="mentorship-requests">
                <h3>Mentorship Requests</h3>
                <div className="requests-list">
                  {mentorshipRequests.map(request => (
                    <div key={request.id} className="request-card">
                      <div className="request-header">
                        <h4>{request.menteeName}</h4>
                        <span className={`status ${request.status}`}>{request.status}</span>
                      </div>

                      <div className="request-details">
                        <p><strong>Year:</strong> {request.menteeYear}</p>
                        <p><strong>Interested in:</strong> {request.requestedSkills.join(", ")}</p>
                        <p><strong>Message:</strong> {request.message}</p>
                      </div>

                      <div className="request-actions">
                        {request.status === "pending" && (
                          <>
                            <button className="btn primary">Accept</button>
                            <button className="btn secondary">Decline</button>
                          </>
                        )}
                        {request.status === "accepted" && (
                          <button className="btn primary">Schedule Meeting</button>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="mentorship-stats">
                <h3>Your Impact</h3>
                <div className="stats-grid">
                  <div className="stat-card">
                    <div className="stat-number">12</div>
                    <div className="stat-label">Mentees Helped</div>
                  </div>
                  <div className="stat-card">
                    <div className="stat-number">48</div>
                    <div className="stat-label">Hours Mentored</div>
                  </div>
                  <div className="stat-card">
                    <div className="stat-number">95%</div>
                    <div className="stat-label">Satisfaction Rate</div>
                  </div>
                </div>
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

        .network-header {
          text-align: center;
          margin-bottom: 2rem;
        }

        .network-header h1 {
          color: #2c3e50;
          margin-bottom: 0.5rem;
        }

        .network-header p {
          color: #6c757d;
          font-size: 1.1rem;
        }

        .network-tabs {
          display: flex;
          background: white;
          border-radius: 12px;
          padding: 0.5rem;
          margin-bottom: 2rem;
          box-shadow: 0 2px 10px rgba(0,0,0,0.1);
          overflow-x: auto;
        }

        .network-tabs button {
          flex: 1;
          padding: 0.75rem 1rem;
          border: none;
          background: none;
          color: #6c757d;
          cursor: pointer;
          border-radius: 8px;
          font-weight: 500;
          transition: all 0.3s;
          white-space: nowrap;
        }

        .network-tabs button.active {
          background: #667eea;
          color: white;
        }

        .network-content {
          max-width: 1200px;
          margin: 0 auto;
        }

        .search-section {
          margin-bottom: 2rem;
        }

        .search-input {
          width: 100%;
          padding: 1rem;
          border: 1px solid #ddd;
          border-radius: 8px;
          font-size: 1rem;
        }

        .alumni-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
          gap: 2rem;
        }

        .alumni-card {
          background: white;
          border-radius: 12px;
          padding: 2rem;
          box-shadow: 0 4px 6px rgba(0,0,0,0.1);
          transition: transform 0.3s;
        }

        .alumni-card:hover {
          transform: translateY(-5px);
        }

        .alumni-header {
          display: flex;
          align-items: center;
          gap: 1rem;
          margin-bottom: 1.5rem;
        }

        .alumni-avatar {
          font-size: 3rem;
        }

        .alumni-basic h3 {
          margin: 0 0 0.25rem 0;
          color: #2c3e50;
        }

        .graduation {
          color: #6c757d;
          font-size: 0.9rem;
        }

        .current-role h4 {
          margin: 0 0 0.5rem 0;
          color: #2c3e50;
        }

        .current-role p {
          margin: 0;
          color: #6c757d;
        }

        .skills-section h5 {
          margin: 0 0 0.75rem 0;
          color: #2c3e50;
          font-size: 0.9rem;
        }

        .skills-list {
          display: flex;
          flex-wrap: wrap;
          gap: 0.5rem;
        }

        .skill-tag {
          background: #e3f2fd;
          color: #1976d2;
          padding: 0.25rem 0.75rem;
          border-radius: 12px;
          font-size: 0.8rem;
          font-weight: 500;
        }

        .bio-section {
          margin: 1.5rem 0;
        }

        .bio {
          color: #495057;
          line-height: 1.5;
          font-style: italic;
        }

        .achievements-section h5 {
          margin: 0 0 0.75rem 0;
          color: #2c3e50;
          font-size: 0.9rem;
        }

        .achievements-list {
          list-style: none;
          padding: 0;
          margin: 0;
        }

        .achievements-list li {
          padding: 0.25rem 0;
          color: #6c757d;
          font-size: 0.9rem;
          border-bottom: 1px solid #f8f9fa;
        }

        .achievements-list li:last-child {
          border-bottom: none;
        }

        .alumni-actions {
          display: flex;
          gap: 1rem;
          margin-top: 1.5rem;
        }

        .create-post {
          background: white;
          padding: 2rem;
          border-radius: 12px;
          box-shadow: 0 4px 6px rgba(0,0,0,0.1);
          margin-bottom: 2rem;
        }

        .post-input {
          width: 100%;
          padding: 1rem;
          border: 1px solid #ddd;
          border-radius: 8px;
          font-family: inherit;
          font-size: 1rem;
          margin-bottom: 1rem;
          resize: vertical;
        }

        .posts-feed {
          display: grid;
          gap: 1.5rem;
        }

        .post-card {
          background: white;
          border-radius: 12px;
          padding: 2rem;
          box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }

        .post-header {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          margin-bottom: 1rem;
        }

        .post-author {
          display: flex;
          align-items: center;
          gap: 1rem;
        }

        .author-avatar {
          font-size: 2rem;
        }

        .author-info h4 {
          margin: 0 0 0.25rem 0;
          color: #2c3e50;
        }

        .post-time {
          color: #6c757d;
          font-size: 0.8rem;
        }

        .post-content {
          margin-bottom: 1.5rem;
        }

        .post-content p {
          margin: 0 0 1rem 0;
          color: #495057;
          line-height: 1.6;
        }

        .post-tags {
          display: flex;
          flex-wrap: wrap;
          gap: 0.5rem;
        }

        .tag {
          color: #667eea;
          font-size: 0.9rem;
          font-weight: 500;
        }

        .post-actions {
          display: flex;
          gap: 1rem;
          padding-top: 1rem;
          border-top: 1px solid #e9ecef;
        }

        .action-btn {
          background: none;
          border: none;
          color: #6c757d;
          cursor: pointer;
          display: flex;
          align-items: center;
          gap: 0.5rem;
          font-size: 0.9rem;
        }

        .events-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
          gap: 2rem;
        }

        .event-card {
          background: white;
          border-radius: 12px;
          padding: 2rem;
          box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }

        .event-header {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          margin-bottom: 1rem;
        }

        .event-header h3 {
          margin: 0;
          color: #2c3e50;
        }

        .event-type {
          background: #e3f2fd;
          color: #1976d2;
          padding: 0.25rem 0.75rem;
          border-radius: 12px;
          font-size: 0.8rem;
          font-weight: 500;
        }

        .event-details {
          margin-bottom: 1.5rem;
        }

        .event-details > div {
          margin-bottom: 0.5rem;
          color: #6c757d;
        }

        .event-description p {
          color: #495057;
          line-height: 1.5;
          margin-bottom: 1rem;
        }

        .event-organizer {
          margin-bottom: 1.5rem;
        }

        .event-actions {
          display: flex;
          gap: 1rem;
        }

        .jobs-list {
          display: grid;
          gap: 2rem;
        }

        .job-card {
          background: white;
          border-radius: 12px;
          padding: 2rem;
          box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }

        .job-header {
          margin-bottom: 1rem;
        }

        .job-header h3 {
          margin: 0 0 0.5rem 0;
          color: #2c3e50;
        }

        .job-company {
          color: #667eea;
          font-weight: 500;
        }

        .job-details {
          display: flex;
          gap: 2rem;
          margin-bottom: 1.5rem;
          flex-wrap: wrap;
        }

        .job-details > div {
          color: #6c757d;
        }

        .job-description p {
          color: #495057;
          line-height: 1.5;
          margin-bottom: 1.5rem;
        }

        .job-requirements h4 {
          margin: 0 0 0.75rem 0;
          color: #2c3e50;
        }

        .job-requirements ul {
          margin: 0;
          padding-left: 1.5rem;
        }

        .job-requirements li {
          color: #6c757d;
          margin-bottom: 0.25rem;
        }

        .job-footer {
          display: flex;
          justify-content: space-between;
          margin-bottom: 1.5rem;
          font-size: 0.9rem;
          color: #6c757d;
        }

        .job-actions {
          display: flex;
          gap: 1rem;
        }

        .mentorship-content {
          display: grid;
          grid-template-columns: 2fr 1fr;
          gap: 2rem;
        }

        .requests-list {
          display: grid;
          gap: 1rem;
        }

        .request-card {
          background: white;
          border-radius: 12px;
          padding: 1.5rem;
          box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }

        .request-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 1rem;
        }

        .request-header h4 {
          margin: 0;
          color: #2c3e50;
        }

        .status {
          padding: 0.25rem 0.75rem;
          border-radius: 12px;
          font-size: 0.8rem;
          font-weight: 500;
        }

        .status.pending {
          background: #fff3cd;
          color: #856404;
        }

        .status.accepted {
          background: #d4edda;
          color: #155724;
        }

        .request-details p {
          margin: 0.5rem 0;
          color: #6c757d;
          font-size: 0.9rem;
        }

        .request-actions {
          display: flex;
          gap: 1rem;
          margin-top: 1rem;
        }

        .stats-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
          gap: 1rem;
        }

        .stat-card {
          background: white;
          padding: 1.5rem;
          border-radius: 8px;
          box-shadow: 0 2px 4px rgba(0,0,0,0.1);
          text-align: center;
        }

        .stat-number {
          font-size: 2rem;
          font-weight: bold;
          color: #667eea;
          margin-bottom: 0.5rem;
        }

        .stat-label {
          color: #6c757d;
          font-size: 0.9rem;
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

        .btn.primary:hover {
          background: #5a67d8;
        }

        .btn.secondary {
          background: #6c757d;
          color: white;
        }

        .btn.secondary:hover {
          background: #5a6268;
        }

        @media (max-width: 768px) {
          .network-tabs {
            flex-direction: column;
          }

          .alumni-grid {
            grid-template-columns: 1fr;
          }

          .events-grid {
            grid-template-columns: 1fr;
          }

          .mentorship-content {
            grid-template-columns: 1fr;
          }

          .job-details {
            flex-direction: column;
            gap: 0.5rem;
          }

          .job-footer {
            flex-direction: column;
            gap: 0.5rem;
          }
        }
      `}</style>
    </div>
  );
}

export default AlumniNetwork;