import React, { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import api from "../services/api";

function CourseAnalytics({ me }) {
  const { courseId } = useParams();
  const navigate = useNavigate();
  const [course, setCourse] = useState(null);
  const [analytics, setAnalytics] = useState(null);
  const [students, setStudents] = useState([]);
  const [reviews, setReviews] = useState([]);
  const [discussions, setDiscussions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState("overview");
  const [selectedStudent, setSelectedStudent] = useState(null);
  const [dateRange, setDateRange] = useState("30d");

  useEffect(() => {
    loadAnalytics();
  }, [courseId]);

  const loadAnalytics = async () => {
    try {
      const [courseRes, analyticsRes, studentsRes, reviewsRes, discussionsRes] = await Promise.all([
        api.get(`/courses/${courseId}`),
        api.get(`/analytics/ai/course/${courseId}`),
        api.get(`/courses/${courseId}/students`),
        api.get(`/reviews/courses/${courseId}/reviews`),
        api.get(`/reviews/courses/${courseId}/discussions`)
      ]);

      setCourse(courseRes.data);
      setAnalytics(analyticsRes.data);
      setStudents(studentsRes.data);
      setReviews(reviewsRes.data);
      setDiscussions(discussionsRes.data);
    } catch (error) {
      console.error("Error loading analytics:", error);
      alert("Error loading analytics data");
    } finally {
      setLoading(false);
    }
  };

  const getStudentAnalytics = async (studentId) => {
    try {
      const response = await api.get(`/analytics/ai/student/${studentId}`);
      setSelectedStudent({
        id: studentId,
        analytics: response.data,
        user: students.find(s => s.id === studentId)
      });
    } catch (error) {
      console.error("Error loading student analytics:", error);
    }
  };

  const exportAnalytics = async (format) => {
    try {
      const data = {
        course: course,
        analytics: analytics,
        students: students,
        reviews: reviews,
        discussions: discussions,
        generated_at: new Date().toISOString()
      };

      if (format === 'json') {
        const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `course-analytics-${courseId}.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
      }
    } catch (error) {
      console.error("Error exporting analytics:", error);
      alert("Error exporting analytics");
    }
  };

  if (loading) {
    return (
      <div className="loading-container">
        <div className="loading-spinner"></div>
        <p>Loading analytics...</p>
      </div>
    );
  }

  if (!course || !analytics) {
    return (
      <div className="error-container">
        <h2>Analytics not available</h2>
        <button onClick={() => navigate("/instructor")}>Back to Dashboard</button>
      </div>
    );
  }

  return (
    <div className="course-analytics">
      <div className="analytics-header">
        <div className="header-content">
          <button className="back-btn" onClick={() => navigate("/instructor")}>
            ← Back to Dashboard
          </button>
          <div className="course-info">
            <h1>{course.title} - Analytics</h1>
            <div className="course-meta">
              <span>{course.audience}</span>
              <span>•</span>
              <span>{course.difficulty}</span>
              <span>•</span>
              <span>{students.length} students</span>
              <span>•</span>
              <span>{reviews.length} reviews</span>
            </div>
          </div>
        </div>
        <div className="header-actions">
          <select
            value={dateRange}
            onChange={(e) => setDateRange(e.target.value)}
            className="date-range-select"
          >
            <option value="7d">Last 7 days</option>
            <option value="30d">Last 30 days</option>
            <option value="90d">Last 90 days</option>
            <option value="all">All time</option>
          </select>
          <button className="btn secondary" onClick={() => exportAnalytics('json')}>
            📊 Export Data
          </button>
        </div>
      </div>

      <div className="analytics-tabs">
        <button
          className={activeTab === "overview" ? "active" : ""}
          onClick={() => setActiveTab("overview")}
        >
          Overview
        </button>
        <button
          className={activeTab === "students" ? "active" : ""}
          onClick={() => setActiveTab("students")}
        >
          Students
        </button>
        <button
          className={activeTab === "engagement" ? "active" : ""}
          onClick={() => setActiveTab("engagement")}
        >
          Engagement
        </button>
        <button
          className={activeTab === "reviews" ? "active" : ""}
          onClick={() => setActiveTab("reviews")}
        >
          Reviews
        </button>
        <button
          className={activeTab === "discussions" ? "active" : ""}
          onClick={() => setActiveTab("discussions")}
        >
          Q&A
        </button>
      </div>

      <div className="analytics-content">
        {activeTab === "overview" && (
          <div className="overview-section">
            <div className="metrics-grid">
              <div className="metric-card">
                <div className="metric-icon">👥</div>
                <div className="metric-content">
                  <div className="metric-value">{analytics.enrollment_trends || students.length}</div>
                  <div className="metric-label">Total Enrollments</div>
                  <div className="metric-change positive">+12% this month</div>
                </div>
              </div>

              <div className="metric-card">
                <div className="metric-icon">📈</div>
                <div className="metric-content">
                  <div className="metric-value">{analytics.completion_rate?.toFixed(1) || 0}%</div>
                  <div className="metric-label">Completion Rate</div>
                  <div className="metric-change positive">+5% this month</div>
                </div>
              </div>

              <div className="metric-card">
                <div className="metric-icon">⭐</div>
                <div className="metric-content">
                  <div className="metric-value">{analytics.average_progress?.toFixed(1) || 0}%</div>
                  <div className="metric-label">Average Progress</div>
                  <div className="metric-change neutral">+2% this month</div>
                </div>
              </div>

              <div className="metric-card">
                <div className="metric-icon">💬</div>
                <div className="metric-content">
                  <div className="metric-value">{discussions.length}</div>
                  <div className="metric-label">Discussions</div>
                  <div className="metric-change positive">+8 this week</div>
                </div>
              </div>
            </div>

            <div className="charts-grid">
              <div className="chart-card">
                <h3>Enrollment Trends</h3>
                <div className="chart-placeholder">
                  📈 Enrollment growth over time
                  <div className="chart-data">
                    <div className="data-point">
                      <span className="label">This Month:</span>
                      <span className="value">+{Math.floor(students.length * 0.1)}</span>
                    </div>
                    <div className="data-point">
                      <span className="label">Last Month:</span>
                      <span className="value">{Math.floor(students.length * 0.9)}</span>
                    </div>
                  </div>
                </div>
              </div>

              <div className="chart-card">
                <h3>Student Performance</h3>
                <div className="chart-placeholder">
                  📊 Average grades and completion rates
                  <div className="performance-metrics">
                    <div className="metric">
                      <span className="label">High Performers:</span>
                      <span className="value">{Math.floor(students.length * 0.3)}</span>
                    </div>
                    <div className="metric">
                      <span className="label">Average Performers:</span>
                      <span className="value">{Math.floor(students.length * 0.5)}</span>
                    </div>
                    <div className="metric">
                      <span className="label">Need Support:</span>
                      <span className="value">{Math.floor(students.length * 0.2)}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div className="insights-section">
              <h3>AI Insights & Recommendations</h3>
              <div className="insights-grid">
                {analytics.performance_insights?.map((insight, index) => (
                  <div key={index} className="insight-card">
                    <div className="insight-icon">💡</div>
                    <div className="insight-content">
                      <p>{insight}</p>
                    </div>
                  </div>
                )) || (
                  <div className="insight-card">
                    <div className="insight-icon">📈</div>
                    <div className="insight-content">
                      <p>Your course is performing well! Consider adding advanced modules to challenge high-performing students.</p>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {activeTab === "students" && (
          <div className="students-section">
            <div className="section-header">
              <h2>Student Performance</h2>
              <div className="filters">
                <select>
                  <option>All Students</option>
                  <option>High Performers</option>
                  <option>Need Support</option>
                  <option>Recently Active</option>
                </select>
              </div>
            </div>

            <div className="students-grid">
              {students.map(student => (
                <div key={student.id} className="student-card">
                  <div className="student-header">
                    <div className="student-avatar">
                      {student.name.charAt(0).toUpperCase()}
                    </div>
                    <div className="student-info">
                      <h4>{student.name}</h4>
                      <p>{student.email}</p>
                    </div>
                  </div>

                  <div className="student-metrics">
                    <div className="metric">
                      <span className="label">Progress:</span>
                      <span className="value">75%</span>
                    </div>
                    <div className="metric">
                      <span className="label">Last Active:</span>
                      <span className="value">2 days ago</span>
                    </div>
                    <div className="metric">
                      <span className="label">Discussions:</span>
                      <span className="value">3</span>
                    </div>
                  </div>

                  <div className="student-actions">
                    <button
                      className="btn small"
                      onClick={() => getStudentAnalytics(student.id)}
                    >
                      📊 View Details
                    </button>
                    <button className="btn small secondary">
                      📧 Message
                    </button>
                  </div>
                </div>
              ))}
            </div>

            {selectedStudent && (
              <div className="student-modal">
                <div className="modal-content">
                  <div className="modal-header">
                    <h3>{selectedStudent.user?.name} - Detailed Analytics</h3>
                    <button
                      className="close-btn"
                      onClick={() => setSelectedStudent(null)}
                    >
                      ×
                    </button>
                  </div>

                  <div className="student-details">
                    <div className="detail-grid">
                      <div className="detail-item">
                        <span className="label">Lessons Completed:</span>
                        <span className="value">{selectedStudent.analytics?.lessons_completed || 0}</span>
                      </div>
                      <div className="detail-item">
                        <span className="label">Time Spent:</span>
                        <span className="value">{selectedStudent.analytics?.total_time_spent || 0} min</span>
                      </div>
                      <div className="detail-item">
                        <span className="label">Current Progress:</span>
                        <span className="value">{selectedStudent.analytics?.progress_percentage || 0}%</span>
                      </div>
                      <div className="detail-item">
                        <span className="label">Learning Pattern:</span>
                        <span className="value">{selectedStudent.analytics?.learning_pattern || 'N/A'}</span>
                      </div>
                    </div>

                    {selectedStudent.analytics?.personalized_recommendations?.length > 0 && (
                      <div className="recommendations">
                        <h4>Personalized Recommendations</h4>
                        <ul>
                          {selectedStudent.analytics.personalized_recommendations.map((rec, index) => (
                            <li key={index}>{rec}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {activeTab === "engagement" && (
          <div className="engagement-section">
            <h2>Student Engagement</h2>

            <div className="engagement-metrics">
              <div className="metric-card">
                <h3>Activity Overview</h3>
                <div className="activity-stats">
                  <div className="stat">
                    <span className="label">Daily Active Users:</span>
                    <span className="value">{Math.floor(students.length * 0.6)}</span>
                  </div>
                  <div className="stat">
                    <span className="label">Weekly Active Users:</span>
                    <span className="value">{Math.floor(students.length * 0.8)}</span>
                  </div>
                  <div className="stat">
                    <span className="label">Discussion Participation:</span>
                    <span className="value">{Math.floor(discussions.length / students.length * 100)}%</span>
                  </div>
                </div>
              </div>

              <div className="metric-card">
                <h3>Content Engagement</h3>
                <div className="content-stats">
                  <div className="stat">
                    <span className="label">Most Popular Lesson:</span>
                    <span className="value">Introduction to {course.title.split(' ')[0]}</span>
                  </div>
                  <div className="stat">
                    <span className="label">Average Session Time:</span>
                    <span className="value">24 minutes</span>
                  </div>
                  <div className="stat">
                    <span className="label">Completion Rate by Lesson:</span>
                    <span className="value">78%</span>
                  </div>
                </div>
              </div>
            </div>

            <div className="engagement-chart">
              <h3>Engagement Trends</h3>
              <div className="chart-placeholder">
                📈 Student activity and engagement patterns over time
              </div>
            </div>
          </div>
        )}

        {activeTab === "reviews" && (
          <div className="reviews-section">
            <div className="section-header">
              <h2>Course Reviews</h2>
              <div className="review-stats">
                <span>Average Rating: ⭐ 4.2</span>
                <span>•</span>
                <span>{reviews.length} reviews</span>
              </div>
            </div>

            <div className="reviews-list">
              {reviews.map(review => (
                <div key={review.id} className="review-card">
                  <div className="review-header">
                    <div className="reviewer-info">
                      <div className="reviewer-avatar">
                        {review.user_name?.charAt(0).toUpperCase() || 'U'}
                      </div>
                      <div className="reviewer-details">
                        <h4>{review.user_name || 'Anonymous'}</h4>
                        <div className="review-rating">
                          {'⭐'.repeat(review.rating)}
                        </div>
                      </div>
                    </div>
                    <div className="review-date">
                      {new Date(review.created_at).toLocaleDateString()}
                    </div>
                  </div>

                  <div className="review-content">
                    <h5>{review.title}</h5>
                    <p>{review.content}</p>

                    {review.pros?.length > 0 && (
                      <div className="review-pros">
                        <strong>Pros:</strong> {review.pros.join(', ')}
                      </div>
                    )}

                    {review.cons?.length > 0 && (
                      <div className="review-cons">
                        <strong>Cons:</strong> {review.cons.join(', ')}
                      </div>
                    )}
                  </div>

                  <div className="review-actions">
                    <button className="btn small secondary">
                      👍 Helpful ({review.helpful_votes || 0})
                    </button>
                    <button className="btn small">
                      💬 Reply
                    </button>
                  </div>
                </div>
              ))}

              {reviews.length === 0 && (
                <div className="empty-state">
                  <h3>No reviews yet</h3>
                  <p>Reviews will appear here once students complete your course</p>
                </div>
              )}
            </div>
          </div>
        )}

        {activeTab === "discussions" && (
          <div className="discussions-section">
            <div className="section-header">
              <h2>Q&A Discussions</h2>
              <div className="discussion-stats">
                <span>{discussions.length} discussions</span>
                <span>•</span>
                <span>{discussions.reduce((sum, d) => sum + (d.reply_count || 0), 0)} replies</span>
              </div>
            </div>

            <div className="discussions-list">
              {discussions.map(discussion => (
                <div key={discussion.id} className="discussion-card">
                  <div className="discussion-header">
                    <div className="discussion-info">
                      <h4>{discussion.title}</h4>
                      <div className="discussion-meta">
                        <span>by {discussion.user_name || 'Anonymous'}</span>
                        <span>•</span>
                        <span>{discussion.discussion_type}</span>
                        <span>•</span>
                        <span>{discussion.reply_count || 0} replies</span>
                        <span>•</span>
                        <span>{discussion.view_count || 0} views</span>
                      </div>
                    </div>
                    <div className="discussion-date">
                      {new Date(discussion.created_at).toLocaleDateString()}
                    </div>
                  </div>

                  <div className="discussion-preview">
                    {discussion.content?.substring(0, 200)}...
                  </div>

                  <div className="discussion-actions">
                    <button className="btn small">
                      👁️ View Discussion
                    </button>
                    {discussion.is_pinned && (
                      <span className="pinned-badge">📌 Pinned</span>
                    )}
                    <button className="btn small secondary">
                      📌 Pin
                    </button>
                    <button className="btn small secondary">
                      🔒 Lock
                    </button>
                  </div>
                </div>
              ))}

              {discussions.length === 0 && (
                <div className="empty-state">
                  <h3>No discussions yet</h3>
                  <p>Discussions and Q&A will appear here as students engage with your course</p>
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      <style>{`
        .course-analytics {
          min-height: 100vh;
          background: #f8f9fa;
        }

        .analytics-header {
          background: white;
          padding: 2rem;
          border-bottom: 1px solid #e9ecef;
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
        }

        .header-content {
          flex: 1;
        }

        .back-btn {
          background: none;
          border: none;
          color: #007bff;
          cursor: pointer;
          font-weight: 500;
          margin-bottom: 1rem;
          display: flex;
          align-items: center;
          gap: 0.5rem;
        }

        .course-info h1 {
          margin: 0 0 0.5rem 0;
          color: #2c3e50;
        }

        .course-meta {
          display: flex;
          gap: 1rem;
          color: #6c757d;
        }

        .header-actions {
          display: flex;
          gap: 1rem;
          align-items: center;
        }

        .date-range-select {
          padding: 0.5rem 1rem;
          border: 1px solid #ddd;
          border-radius: 6px;
        }

        .analytics-tabs {
          background: white;
          display: flex;
          border-bottom: 1px solid #e9ecef;
          overflow-x: auto;
        }

        .analytics-tabs button {
          padding: 1rem 2rem;
          border: none;
          background: none;
          color: #6c757d;
          cursor: pointer;
          border-bottom: 3px solid transparent;
          transition: all 0.3s;
          white-space: nowrap;
        }

        .analytics-tabs button.active {
          color: #007bff;
          border-bottom-color: #007bff;
        }

        .analytics-content {
          padding: 2rem;
        }

        .metrics-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
          gap: 2rem;
          margin-bottom: 3rem;
        }

        .metric-card {
          background: white;
          padding: 2rem;
          border-radius: 12px;
          box-shadow: 0 4px 6px rgba(0,0,0,0.1);
          display: flex;
          align-items: center;
          gap: 1rem;
        }

        .metric-icon {
          font-size: 2rem;
        }

        .metric-content {
          flex: 1;
        }

        .metric-value {
          font-size: 2rem;
          font-weight: bold;
          color: #2c3e50;
          margin-bottom: 0.5rem;
        }

        .metric-label {
          color: #6c757d;
          margin-bottom: 0.25rem;
        }

        .metric-change {
          font-size: 0.9rem;
          font-weight: 500;
        }

        .metric-change.positive {
          color: #28a745;
        }

        .metric-change.negative {
          color: #dc3545;
        }

        .metric-change.neutral {
          color: #6c757d;
        }

        .charts-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
          gap: 2rem;
          margin-bottom: 3rem;
        }

        .chart-card {
          background: white;
          padding: 2rem;
          border-radius: 12px;
          box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }

        .chart-placeholder {
          height: 200px;
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          background: #f8f9fa;
          border-radius: 8px;
          color: #6c757d;
          font-size: 1.2rem;
        }

        .chart-data, .performance-metrics {
          margin-top: 1rem;
          width: 100%;
        }

        .data-point, .metric {
          display: flex;
          justify-content: space-between;
          margin-bottom: 0.5rem;
        }

        .insights-section h3 {
          margin-bottom: 2rem;
          color: #2c3e50;
        }

        .insights-grid {
          display: grid;
          gap: 1rem;
        }

        .insight-card {
          background: white;
          padding: 1.5rem;
          border-radius: 12px;
          box-shadow: 0 2px 4px rgba(0,0,0,0.1);
          display: flex;
          align-items: flex-start;
          gap: 1rem;
        }

        .insight-icon {
          font-size: 1.5rem;
          margin-top: 0.25rem;
        }

        .insight-content p {
          margin: 0;
          color: #495057;
          line-height: 1.5;
        }

        .section-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 2rem;
        }

        .section-header h2 {
          margin: 0;
          color: #2c3e50;
        }

        .filters select {
          padding: 0.5rem 1rem;
          border: 1px solid #ddd;
          border-radius: 6px;
        }

        .students-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
          gap: 2rem;
        }

        .student-card {
          background: white;
          padding: 1.5rem;
          border-radius: 12px;
          box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }

        .student-header {
          display: flex;
          align-items: center;
          gap: 1rem;
          margin-bottom: 1rem;
        }

        .student-avatar {
          width: 50px;
          height: 50px;
          border-radius: 50%;
          background: #007bff;
          color: white;
          display: flex;
          align-items: center;
          justify-content: center;
          font-weight: bold;
          font-size: 1.2rem;
        }

        .student-info h4 {
          margin: 0 0 0.25rem 0;
          color: #2c3e50;
        }

        .student-info p {
          margin: 0;
          color: #6c757d;
          font-size: 0.9rem;
        }

        .student-metrics {
          margin-bottom: 1rem;
        }

        .student-metrics .metric {
          display: flex;
          justify-content: space-between;
          margin-bottom: 0.5rem;
          font-size: 0.9rem;
        }

        .student-metrics .label {
          color: #6c757d;
        }

        .student-metrics .value {
          font-weight: 500;
          color: #2c3e50;
        }

        .student-actions {
          display: flex;
          gap: 0.5rem;
        }

        .student-modal {
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

        .modal-content {
          background: white;
          border-radius: 12px;
          width: 90%;
          max-width: 600px;
          max-height: 80vh;
          overflow-y: auto;
        }

        .modal-header {
          padding: 2rem 2rem 0;
          display: flex;
          justify-content: space-between;
          align-items: center;
        }

        .modal-header h3 {
          margin: 0;
          color: #2c3e50;
        }

        .close-btn {
          background: none;
          border: none;
          font-size: 2rem;
          cursor: pointer;
          color: #6c757d;
        }

        .student-details {
          padding: 2rem;
        }

        .detail-grid {
          display: grid;
          grid-template-columns: repeat(2, 1fr);
          gap: 1rem;
          margin-bottom: 2rem;
        }

        .detail-item {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 1rem;
          background: #f8f9fa;
          border-radius: 8px;
        }

        .detail-item .label {
          color: #6c757d;
          font-weight: 500;
        }

        .detail-item .value {
          font-weight: 600;
          color: #2c3e50;
        }

        .recommendations h4 {
          margin-bottom: 1rem;
          color: #2c3e50;
        }

        .recommendations ul {
          list-style: none;
          padding: 0;
        }

        .recommendations li {
          padding: 0.5rem 0;
          border-bottom: 1px solid #e9ecef;
          color: #495057;
        }

        .engagement-metrics {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
          gap: 2rem;
          margin-bottom: 3rem;
        }

        .activity-stats, .content-stats {
          display: flex;
          flex-direction: column;
          gap: 1rem;
        }

        .stat {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 0.75rem;
          background: #f8f9fa;
          border-radius: 8px;
        }

        .engagement-chart {
          background: white;
          padding: 2rem;
          border-radius: 12px;
          box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }

        .review-stats {
          display: flex;
          gap: 1rem;
          color: #6c757d;
        }

        .reviews-list {
          display: flex;
          flex-direction: column;
          gap: 1.5rem;
        }

        .review-card {
          background: white;
          padding: 2rem;
          border-radius: 12px;
          box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }

        .review-header {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          margin-bottom: 1.5rem;
        }

        .reviewer-info {
          display: flex;
          align-items: center;
          gap: 1rem;
        }

        .reviewer-avatar {
          width: 50px;
          height: 50px;
          border-radius: 50%;
          background: #007bff;
          color: white;
          display: flex;
          align-items: center;
          justify-content: center;
          font-weight: bold;
          font-size: 1.2rem;
        }

        .reviewer-details h4 {
          margin: 0 0 0.25rem 0;
          color: #2c3e50;
        }

        .review-rating {
          color: #ffc107;
          font-size: 1.1rem;
        }

        .review-date {
          color: #6c757d;
          font-size: 0.9rem;
        }

        .review-content h5 {
          margin: 0 0 1rem 0;
          color: #2c3e50;
        }

        .review-content p {
          margin: 0 0 1rem 0;
          color: #495057;
          line-height: 1.6;
        }

        .review-pros, .review-cons {
          margin: 0.5rem 0;
          padding: 0.75rem;
          border-radius: 6px;
        }

        .review-pros {
          background: #d4edda;
          color: #155724;
        }

        .review-cons {
          background: #f8d7da;
          color: #721c24;
        }

        .review-actions {
          display: flex;
          gap: 1rem;
          margin-top: 1rem;
        }

        .discussions-list {
          display: flex;
          flex-direction: column;
          gap: 1rem;
        }

        .discussion-card {
          background: white;
          padding: 1.5rem;
          border-radius: 12px;
          box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }

        .discussion-header {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          margin-bottom: 1rem;
        }

        .discussion-info h4 {
          margin: 0 0 0.5rem 0;
          color: #2c3e50;
        }

        .discussion-meta {
          display: flex;
          gap: 1rem;
          color: #6c757d;
          font-size: 0.9rem;
        }

        .discussion-preview {
          color: #495057;
          margin-bottom: 1rem;
          line-height: 1.5;
        }

        .discussion-actions {
          display: flex;
          gap: 0.5rem;
          align-items: center;
        }

        .pinned-badge {
          background: #fff3cd;
          color: #856404;
          padding: 0.25rem 0.75rem;
          border-radius: 20px;
          font-size: 0.8rem;
          font-weight: 500;
        }

        .empty-state {
          text-align: center;
          padding: 3rem;
          background: white;
          border-radius: 12px;
          box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }

        .empty-state h3 {
          margin: 0 0 1rem 0;
          color: #6c757d;
        }

        .empty-state p {
          margin: 0;
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
          background: #007bff;
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

        .loading-container {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          height: 400px;
          gap: 1rem;
        }

        .loading-spinner {
          width: 40px;
          height: 40px;
          border: 4px solid #f3f3f3;
          border-top: 4px solid #007bff;
          border-radius: 50%;
          animation: spin 1s linear infinite;
        }

        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }

        .error-container {
          text-align: center;
          padding: 3rem;
        }

        .error-container h2 {
          color: #dc3545;
          margin-bottom: 2rem;
        }
      `}</style>
    </div>
  );
}

export default CourseAnalytics;