import React, { useEffect, useState } from "react";
import api from "../services/api";

function ReviewerDashboard({ me }) {
  const [activeTab, setActiveTab] = useState("students");
  const [students, setStudents] = useState([]);
  const [selectedStudent, setSelectedStudent] = useState(null);
  const [interviews, setInterviews] = useState([]);
  const [feedback, setFeedback] = useState([]);
  const [jobPostings, setJobPostings] = useState([]);
  const [analytics, setAnalytics] = useState(null);
  const [searchTerm, setSearchTerm] = useState("");
  const [filters, setFilters] = useState({ skills: "", availability: "" });

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [studentsRes, interviewsRes, feedbackRes, analyticsRes] = await Promise.all([
        api.get("/reviewer/student-profiles"),
        api.get("/reviewer/scheduled-interviews"),
        api.get("/reviewer/feedback-history"),
        api.get("/reviewer/analytics")
      ]);

      setStudents(studentsRes.data);
      setInterviews(interviewsRes.data);
      setFeedback(feedbackRes.data);
      setAnalytics(analyticsRes.data);

      if (me.role === "employer") {
        const jobsRes = await api.get("/reviewer/job-postings");
        setJobPostings(jobsRes.data);
      }
    } catch (error) {
      console.error("Error loading reviewer data:", error);
    }
  };

  const filteredStudents = students.filter(student =>
    student.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    student.email.toLowerCase().includes(searchTerm.toLowerCase()) ||
    student.skills.some(skill => skill.toLowerCase().includes(searchTerm.toLowerCase()))
  );

  const scheduleInterview = async (studentId) => {
    const interviewData = {
      student_id: studentId,
      scheduled_date: prompt("Enter interview date (YYYY-MM-DD HH:MM):"),
      duration: 60,
      interview_type: "technical",
      format: "virtual",
      topics: ["Technical Skills", "Problem Solving", "Communication"]
    };

    if (interviewData.scheduled_date) {
      try {
        await api.post("/reviewer/schedule-interview", interviewData);
        alert("Interview scheduled successfully!");
        loadData();
      } catch (error) {
        alert("Error scheduling interview");
      }
    }
  };

  const submitFeedback = async (studentId) => {
    const feedbackData = {
      student_id: studentId,
      overall_rating: 4.5,
      technical_skills: { programming: 5, problem_solving: 4, communication: 4 },
      soft_skills: { teamwork: 4, leadership: 3 },
      strengths: ["Strong technical foundation", "Quick learner"],
      areas_for_improvement: ["Could improve presentation skills"],
      recommendation: "Strong Hire",
      comments: "Excellent candidate with solid technical skills and great potential."
    };

    try {
      await api.post("/reviewer/submit-feedback", feedbackData);
      alert("Feedback submitted successfully!");
      loadData();
    } catch (error) {
      alert("Error submitting feedback");
    }
  };

  const endorseStudent = async (studentId) => {
    const skill = prompt("Enter skill to endorse:");
    if (skill) {
      const endorsementData = {
        student_id: studentId,
        skill: skill,
        level: "proficient",
        comment: "Based on portfolio review and technical assessment"
      };

      try {
        await api.post("/reviewer/endorse-student", endorsementData);
        alert("Student endorsed successfully!");
      } catch (error) {
        alert("Error endorsing student");
      }
    }
  };

  const createJobPosting = async () => {
    const jobData = {
      title: prompt("Job Title:"),
      description: prompt("Job Description:"),
      requirements: ["Bachelor's degree", "2+ years experience"],
      skills_required: ["Python", "JavaScript", "React"],
      location: "Remote",
      job_type: "full_time",
      salary_range: "$80,000 - $100,000",
      application_deadline: "2024-02-28"
    };

    if (jobData.title && jobData.description) {
      try {
        await api.post("/reviewer/create-job-posting", jobData);
        alert("Job posting created successfully!");
        loadData();
      } catch (error) {
        alert("Error creating job posting");
      }
    }
  };

  return (
    <div className="reviewer-dashboard">
      <div className="dashboard-header">
        <h1>🎯 {me.role === "employer" ? "Employer" : "External Reviewer"} Dashboard</h1>
        <p>Review student profiles, conduct interviews, and provide feedback</p>
      </div>

      <div className="dashboard-tabs">
        <button
          className={activeTab === "students" ? "active" : ""}
          onClick={() => setActiveTab("students")}
        >
          👥 Student Profiles
        </button>
        <button
          className={activeTab === "interviews" ? "active" : ""}
          onClick={() => setActiveTab("interviews")}
        >
          📅 Interviews
        </button>
        <button
          className={activeTab === "feedback" ? "active" : ""}
          onClick={() => setActiveTab("feedback")}
        >
          📝 Feedback
        </button>
        {me.role === "employer" && (
          <button
            className={activeTab === "jobs" ? "active" : ""}
            onClick={() => setActiveTab("jobs")}
          >
            💼 Job Postings
          </button>
        )}
        <button
          className={activeTab === "analytics" ? "active" : ""}
          onClick={() => setActiveTab("analytics")}
        >
          📊 Analytics
        </button>
      </div>

      <div className="dashboard-content">
        {activeTab === "students" && (
          <div className="students-section">
            <div className="section-header">
              <h2>Student Profiles</h2>
              <div className="header-actions">
                <input
                  type="text"
                  placeholder="Search students..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="search-input"
                />
                <select
                  value={filters.skills}
                  onChange={(e) => setFilters({...filters, skills: e.target.value})}
                >
                  <option value="">All Skills</option>
                  <option value="Python">Python</option>
                  <option value="JavaScript">JavaScript</option>
                  <option value="Java">Java</option>
                </select>
              </div>
            </div>

            <div className="students-grid">
              {filteredStudents.map(student => (
                <div key={student._id} className="student-card">
                  <div className="student-header">
                    <h3>{student.name}</h3>
                    <span className="gpa">GPA: {student.gpa}</span>
                  </div>
                  <p className="student-email">{student.email}</p>
                  <p className="student-grade">{student.grade}</p>

                  <div className="student-skills">
                    <h4>Skills:</h4>
                    <div className="skills-list">
                      {student.skills.slice(0, 3).map(skill => (
                        <span key={skill} className="skill-tag">{skill}</span>
                      ))}
                      {student.skills.length > 3 && (
                        <span className="skill-tag">+{student.skills.length - 3} more</span>
                      )}
                    </div>
                  </div>

                  <div className="student-projects">
                    <h4>Projects:</h4>
                    <ul>
                      {student.projects.slice(0, 2).map(project => (
                        <li key={project}>{project}</li>
                      ))}
                    </ul>
                  </div>

                  <div className="student-actions">
                    <button
                      className="btn small"
                      onClick={() => setSelectedStudent(student)}
                    >
                      View Profile
                    </button>
                    <button
                      className="btn small primary"
                      onClick={() => scheduleInterview(student._id)}
                    >
                      Schedule Interview
                    </button>
                    <button
                      className="btn small secondary"
                      onClick={() => endorseStudent(student._id)}
                    >
                      Endorse
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {activeTab === "interviews" && (
          <div className="interviews-section">
            <div className="section-header">
              <h2>Scheduled Interviews</h2>
              <button className="btn primary" onClick={() => alert("Schedule new interview")}>
                + Schedule Interview
              </button>
            </div>

            <div className="interviews-list">
              {interviews.map(interview => (
                <div key={interview._id} className="interview-card">
                  <div className="interview-header">
                    <h3>{interview.student_name}</h3>
                    <span className={`status ${interview.status}`}>
                      {interview.status.replace('_', ' ')}
                    </span>
                  </div>
                  <div className="interview-details">
                    <p><strong>Date:</strong> {new Date(interview.scheduled_date).toLocaleString()}</p>
                    <p><strong>Duration:</strong> {interview.duration} minutes</p>
                    <p><strong>Type:</strong> {interview.interview_type}</p>
                    <p><strong>Format:</strong> {interview.format}</p>
                  </div>
                  <div className="interview-topics">
                    <h4>Topics:</h4>
                    <div className="topics-list">
                      {interview.topics.map(topic => (
                        <span key={topic} className="topic-tag">{topic}</span>
                      ))}
                    </div>
                  </div>
                  <div className="interview-actions">
                    <button className="btn small">Join Interview</button>
                    <button className="btn small secondary">Reschedule</button>
                    <button
                      className="btn small primary"
                      onClick={() => submitFeedback(interview.student_id)}
                    >
                      Submit Feedback
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {activeTab === "feedback" && (
          <div className="feedback-section">
            <h2>Feedback History</h2>
            <div className="feedback-list">
              {feedback.map(item => (
                <div key={item._id} className="feedback-card">
                  <div className="feedback-header">
                    <h3>{item.student_name}</h3>
                    <div className="feedback-rating">
                      <span className="rating">⭐ {item.overall_rating}/5</span>
                      <span className="recommendation">{item.recommendation}</span>
                    </div>
                  </div>
                  <div className="feedback-strengths">
                    <h4>Key Strengths:</h4>
                    <div className="strengths-list">
                      {item.key_strengths.map(strength => (
                        <span key={strength} className="strength-tag">{strength}</span>
                      ))}
                    </div>
                  </div>
                  <div className="feedback-date">
                    <small>Submitted: {new Date(item.submitted_at).toLocaleDateString()}</small>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {activeTab === "jobs" && me.role === "employer" && (
          <div className="jobs-section">
            <div className="section-header">
              <h2>Job Postings</h2>
              <button className="btn primary" onClick={createJobPosting}>
                + Create Job Posting
              </button>
            </div>

            <div className="jobs-list">
              {jobPostings.map(job => (
                <div key={job._id} className="job-card">
                  <div className="job-header">
                    <h3>{job.title}</h3>
                    <span className={`status ${job.status}`}>
                      {job.status}
                    </span>
                  </div>
                  <div className="job-details">
                    <p><strong>Company:</strong> {job.company}</p>
                    <p><strong>Location:</strong> {job.location}</p>
                    <p><strong>Type:</strong> {job.job_type.replace('_', ' ')}</p>
                    <p><strong>Applications:</strong> {job.applications_count}</p>
                  </div>
                  <div className="job-actions">
                    <button className="btn small">View Applications</button>
                    <button className="btn small secondary">Edit Posting</button>
                    <button className="btn small danger">Close Posting</button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {activeTab === "analytics" && analytics && (
          <div className="analytics-section">
            <h2>Review Analytics</h2>
            <div className="analytics-grid">
              <div className="analytics-card">
                <h3>Total Reviews</h3>
                <div className="metric-value">{analytics.total_reviews}</div>
                <p>Students reviewed</p>
              </div>
              <div className="analytics-card">
                <h3>Interviews Conducted</h3>
                <div className="metric-value">{analytics.interviews_conducted}</div>
                <p>Technical interviews</p>
              </div>
              <div className="analytics-card">
                <h3>Students Endorsed</h3>
                <div className="metric-value">{analytics.students_endorsed}</div>
                <p>Skill endorsements</p>
              </div>
              <div className="analytics-card">
                <h3>Average Rating</h3>
                <div className="metric-value">{analytics.average_rating_given}/5</div>
                <p>Overall rating given</p>
              </div>
            </div>

            <div className="top-skills-section">
              <h3>Top Skills Reviewed</h3>
              <div className="skills-chart">
                {analytics.top_skills_reviewed.map(skill => (
                  <div key={skill.skill} className="skill-bar">
                    <span className="skill-name">{skill.skill}</span>
                    <div className="skill-progress">
                      <div
                        className="skill-fill"
                        style={{width: `${(skill.count / analytics.top_skills_reviewed[0].count) * 100}%`}}
                      ></div>
                    </div>
                    <span className="skill-count">{skill.count}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>

      <style jsx>{`
        .reviewer-dashboard {
          min-height: 100vh;
          background: #f8f9fa;
          padding: 2rem;
        }

        .dashboard-header {
          text-align: center;
          margin-bottom: 2rem;
        }

        .dashboard-header h1 {
          color: #2c3e50;
          margin-bottom: 0.5rem;
        }

        .dashboard-header p {
          color: #6c757d;
          font-size: 1.1rem;
        }

        .dashboard-tabs {
          display: flex;
          justify-content: center;
          margin-bottom: 2rem;
          background: white;
          border-radius: 12px;
          padding: 0.5rem;
          box-shadow: 0 2px 4px rgba(0,0,0,0.1);
          flex-wrap: wrap;
        }

        .dashboard-tabs button {
          padding: 0.75rem 1.5rem;
          border: none;
          background: transparent;
          border-radius: 8px;
          font-weight: 600;
          cursor: pointer;
          transition: all 0.3s;
          color: #6c757d;
        }

        .dashboard-tabs button.active {
          background: #667eea;
          color: white;
        }

        .dashboard-tabs button:hover {
          background: #f8f9fa;
        }

        .dashboard-content {
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

        .header-actions {
          display: flex;
          gap: 1rem;
          align-items: center;
          flex-wrap: wrap;
        }

        .search-input {
          padding: 0.5rem 1rem;
          border: 1px solid #ddd;
          border-radius: 6px;
          width: 250px;
        }

        .students-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
          gap: 2rem;
        }

        .student-card {
          background: white;
          padding: 2rem;
          border-radius: 12px;
          box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }

        .student-header {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          margin-bottom: 1rem;
        }

        .student-header h3 {
          margin: 0;
          color: #2c3e50;
        }

        .gpa {
          background: #28a745;
          color: white;
          padding: 0.25rem 0.5rem;
          border-radius: 12px;
          font-size: 0.9rem;
        }

        .student-email,
        .student-grade {
          color: #6c757d;
          margin: 0.25rem 0;
        }

        .student-skills h4,
        .student-projects h4 {
          margin: 1rem 0 0.5rem 0;
          color: #2c3e50;
          font-size: 0.9rem;
        }

        .skills-list,
        .projects-list {
          display: flex;
          flex-wrap: wrap;
          gap: 0.5rem;
        }

        .skill-tag {
          background: #667eea;
          color: white;
          padding: 0.25rem 0.5rem;
          border-radius: 12px;
          font-size: 0.8rem;
        }

        .student-projects ul {
          margin: 0;
          padding-left: 1rem;
        }

        .student-projects li {
          color: #6c757d;
          font-size: 0.9rem;
        }

        .student-actions {
          display: flex;
          gap: 0.5rem;
          margin-top: 1.5rem;
          flex-wrap: wrap;
        }

        .interviews-list,
        .feedback-list,
        .jobs-list {
          display: grid;
          gap: 1.5rem;
        }

        .interview-card,
        .feedback-card,
        .job-card {
          background: white;
          padding: 2rem;
          border-radius: 12px;
          box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }

        .interview-header,
        .feedback-header,
        .job-header {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          margin-bottom: 1rem;
        }

        .interview-header h3,
        .feedback-header h3,
        .job-header h3 {
          margin: 0;
          color: #2c3e50;
        }

        .status {
          padding: 0.25rem 0.75rem;
          border-radius: 20px;
          font-size: 0.8rem;
          font-weight: 600;
          text-transform: capitalize;
        }

        .status.scheduled { background: #fff3cd; color: #856404; }
        .status.completed { background: #d4edda; color: #155724; }
        .status.active { background: #d1ecf1; color: #0c5460; }

        .interview-details p,
        .job-details p {
          margin: 0.5rem 0;
          color: #6c757d;
        }

        .interview-topics h4 {
          margin: 1rem 0 0.5rem 0;
          color: #2c3e50;
          font-size: 0.9rem;
        }

        .topics-list {
          display: flex;
          flex-wrap: wrap;
          gap: 0.5rem;
        }

        .topic-tag {
          background: #e9ecef;
          color: #495057;
          padding: 0.25rem 0.5rem;
          border-radius: 12px;
          font-size: 0.8rem;
        }

        .interview-actions,
        .job-actions {
          display: flex;
          gap: 0.5rem;
          margin-top: 1.5rem;
          flex-wrap: wrap;
        }

        .feedback-rating {
          text-align: right;
        }

        .rating {
          display: block;
          font-size: 1.25rem;
          font-weight: bold;
          color: #ffc107;
        }

        .recommendation {
          display: block;
          font-size: 0.9rem;
          color: #28a745;
          font-weight: 600;
        }

        .feedback-strengths h4 {
          margin: 1rem 0 0.5rem 0;
          color: #2c3e50;
          font-size: 0.9rem;
        }

        .strengths-list {
          display: flex;
          flex-wrap: wrap;
          gap: 0.5rem;
        }

        .strength-tag {
          background: #28a745;
          color: white;
          padding: 0.25rem 0.5rem;
          border-radius: 12px;
          font-size: 0.8rem;
        }

        .analytics-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
          gap: 2rem;
          margin-bottom: 3rem;
        }

        .analytics-card {
          background: white;
          padding: 2rem;
          border-radius: 12px;
          box-shadow: 0 4px 6px rgba(0,0,0,0.1);
          text-align: center;
        }

        .analytics-card h3 {
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

        .analytics-card p {
          margin: 0;
          color: #6c757d;
          font-size: 0.9rem;
        }

        .top-skills-section {
          background: white;
          padding: 2rem;
          border-radius: 12px;
          box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }

        .top-skills-section h3 {
          margin: 0 0 2rem 0;
          color: #2c3e50;
        }

        .skills-chart {
          display: grid;
          gap: 1rem;
        }

        .skill-bar {
          display: flex;
          align-items: center;
          gap: 1rem;
        }

        .skill-name {
          width: 120px;
          font-weight: 600;
          color: #2c3e50;
        }

        .skill-progress {
          flex: 1;
          height: 12px;
          background: #e9ecef;
          border-radius: 6px;
          overflow: hidden;
        }

        .skill-fill {
          height: 100%;
          background: linear-gradient(90deg, #667eea, #764ba2);
          border-radius: 6px;
        }

        .skill-count {
          width: 40px;
          text-align: right;
          font-weight: 600;
          color: #667eea;
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

        .btn.danger {
          background: #dc3545;
          color: white;
        }

        .btn.small {
          padding: 0.375rem 0.75rem;
          font-size: 0.8rem;
        }

        .btn:hover {
          transform: translateY(-2px);
          box-shadow: 0 4px 12px rgba(0,0,0,0.2);
        }

        @media (max-width: 768px) {
          .dashboard-tabs {
            flex-direction: column;
          }

          .students-grid {
            grid-template-columns: 1fr;
          }

          .analytics-grid {
            grid-template-columns: 1fr;
          }

          .section-header {
            flex-direction: column;
            gap: 1rem;
            text-align: center;
          }

          .header-actions {
            justify-content: center;
          }

          .student-actions,
          .interview-actions,
          .job-actions {
            justify-content: center;
          }

          .interview-header,
          .feedback-header,
          .job-header {
            flex-direction: column;
            gap: 0.5rem;
            text-align: center;
          }
        }
      `}</style>
    </div>
  );
}

export default ReviewerDashboard;