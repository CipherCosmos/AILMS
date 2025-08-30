import React, { useEffect, useState } from "react";
import api from "../services/api";

function ParentPortal({ me }) {
  const [students, setStudents] = useState([]);
  const [selectedStudent, setSelectedStudent] = useState(null);
  const [studentProgress, setStudentProgress] = useState(null);
  const [studentCourses, setStudentCourses] = useState([]);
  const [notifications, setNotifications] = useState([]);
  const [activeTab, setActiveTab] = useState("overview");

  useEffect(() => {
    loadStudents();
    loadNotifications();
  }, []);

  useEffect(() => {
    if (selectedStudent) {
      loadStudentProgress();
      loadStudentCourses();
    }
  }, [selectedStudent]);

  const loadStudents = async () => {
    try {
      // In a real implementation, this would fetch students linked to the parent
      // For now, we'll use mock data
      setStudents([
        {
          id: "student1",
          name: "Emma Johnson",
          grade: "10th Grade",
          avatar: "👩‍🎓",
          enrolledCourses: 4,
          averageGrade: 92,
          currentStreak: 5,
          totalPoints: 1250
        },
        {
          id: "student2",
          name: "Alex Johnson",
          grade: "8th Grade",
          avatar: "👨‍🎓",
          enrolledCourses: 3,
          averageGrade: 88,
          currentStreak: 3,
          totalPoints: 980
        }
      ]);
    } catch (error) {
      console.error("Error loading students:", error);
    }
  };

  const loadStudentProgress = async () => {
    try {
      // Mock data - would come from API
      setStudentProgress({
        overallProgress: 78,
        completedCourses: 2,
        activeCourses: 3,
        totalLessons: 45,
        completedLessons: 35,
        averageQuizScore: 87,
        studyTimeThisWeek: 12.5, // hours
        achievements: [
          { id: "1", name: "Week Warrior", date: "2024-01-20", icon: "⚔️" },
          { id: "2", name: "Quiz Master", date: "2024-01-18", icon: "🧠" }
        ]
      });
    } catch (error) {
      console.error("Error loading student progress:", error);
    }
  };

  const loadStudentCourses = async () => {
    try {
      // Mock data - would come from API
      setStudentCourses([
        {
          id: "course1",
          title: "Advanced Mathematics",
          progress: 85,
          grade: 94,
          lastActivity: "2024-01-25",
          nextDeadline: "2024-01-30",
          status: "active"
        },
        {
          id: "course2",
          title: "Physics Fundamentals",
          progress: 72,
          grade: 89,
          lastActivity: "2024-01-24",
          nextDeadline: "2024-02-02",
          status: "active"
        },
        {
          id: "course3",
          title: "English Literature",
          progress: 100,
          grade: 96,
          lastActivity: "2024-01-20",
          nextDeadline: null,
          status: "completed"
        }
      ]);
    } catch (error) {
      console.error("Error loading student courses:", error);
    }
  };

  const loadNotifications = async () => {
    try {
      // Mock data - would come from API
      setNotifications([
        {
          id: "1",
          type: "achievement",
          title: "New Achievement Unlocked!",
          message: "Emma earned the 'Week Warrior' badge for studying 7 days in a row",
          date: "2024-01-20",
          studentId: "student1",
          read: false
        },
        {
          id: "2",
          type: "deadline",
          title: "Assignment Due Soon",
          message: "Emma has an assignment due in Advanced Mathematics on Jan 30th",
          date: "2024-01-25",
          studentId: "student1",
          read: false
        },
        {
          id: "3",
          type: "grade",
          title: "New Grade Posted",
          message: "Alex received an 89% on Physics Fundamentals quiz",
          date: "2024-01-24",
          studentId: "student2",
          read: true
        }
      ]);
    } catch (error) {
      console.error("Error loading notifications:", error);
    }
  };

  const markNotificationRead = async (notificationId) => {
    try {
      await api.post(`/notifications/${notificationId}/read`);
      setNotifications(prev =>
        prev.map(n => n.id === notificationId ? {...n, read: true} : n)
      );
    } catch (error) {
      console.error("Error marking notification as read:", error);
    }
  };

  const sendMessageToStudent = async (studentId, message) => {
    try {
      // In a real implementation, this would send a message to the student
      alert(`Message sent to ${students.find(s => s.id === studentId)?.name}: ${message}`);
    } catch (error) {
      console.error("Error sending message:", error);
    }
  };

  return (
    <div className="parent-portal">
      <div className="portal-header">
        <h1>👨‍👩‍👧‍👦 Parent Portal</h1>
        <p>Monitor your children's learning progress and stay connected</p>
      </div>

      <div className="portal-content">
        {/* Students List */}
        <div className="students-section">
          <h2>Your Children</h2>
          <div className="students-grid">
            {students.map(student => (
              <div
                key={student.id}
                className={`student-card ${selectedStudent?.id === student.id ? 'selected' : ''}`}
                onClick={() => setSelectedStudent(student)}
              >
                <div className="student-avatar">{student.avatar}</div>
                <div className="student-info">
                  <h3>{student.name}</h3>
                  <p className="student-grade">{student.grade}</p>
                  <div className="student-stats">
                    <div className="stat">
                      <span className="stat-value">{student.enrolledCourses}</span>
                      <span className="stat-label">Courses</span>
                    </div>
                    <div className="stat">
                      <span className="stat-value">{student.averageGrade}%</span>
                      <span className="stat-label">Avg Grade</span>
                    </div>
                    <div className="stat">
                      <span className="stat-value">{student.currentStreak}</span>
                      <span className="stat-label">Day Streak</span>
                    </div>
                  </div>
                </div>
                <div className="student-actions">
                  <button
                    className="btn small"
                    onClick={(e) => {
                      e.stopPropagation();
                      const message = prompt("Enter message for your child:");
                      if (message) sendMessageToStudent(student.id, message);
                    }}
                  >
                    💬 Message
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Selected Student Details */}
        {selectedStudent && (
          <div className="student-details">
            <div className="details-header">
              <div className="student-summary">
                <div className="student-avatar-large">{selectedStudent.avatar}</div>
                <div className="student-summary-info">
                  <h2>{selectedStudent.name}</h2>
                  <p>{selectedStudent.grade}</p>
                  <div className="summary-stats">
                    <div className="summary-stat">
                      <span className="stat-value">{studentProgress?.overallProgress || 0}%</span>
                      <span className="stat-label">Overall Progress</span>
                    </div>
                    <div className="summary-stat">
                      <span className="stat-value">{studentProgress?.averageQuizScore || 0}%</span>
                      <span className="stat-label">Avg Quiz Score</span>
                    </div>
                    <div className="summary-stat">
                      <span className="stat-value">{studentProgress?.studyTimeThisWeek || 0}h</span>
                      <span className="stat-label">Study Time (Week)</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div className="details-tabs">
              <button
                className={activeTab === "overview" ? "active" : ""}
                onClick={() => setActiveTab("overview")}
              >
                Overview
              </button>
              <button
                className={activeTab === "courses" ? "active" : ""}
                onClick={() => setActiveTab("courses")}
              >
                Courses
              </button>
              <button
                className={activeTab === "achievements" ? "active" : ""}
                onClick={() => setActiveTab("achievements")}
              >
                Achievements
              </button>
            </div>

            <div className="details-content">
              {activeTab === "overview" && studentProgress && (
                <div className="overview-section">
                  <div className="progress-overview">
                    <div className="progress-card">
                      <h3>Learning Progress</h3>
                      <div className="progress-circle">
                        <div className="progress-text">{studentProgress.overallProgress}%</div>
                      </div>
                      <p>{studentProgress.completedLessons}/{studentProgress.totalLessons} lessons completed</p>
                    </div>

                    <div className="progress-card">
                      <h3>Academic Performance</h3>
                      <div className="grade-display">
                        <div className="grade-value">{selectedStudent.averageGrade}%</div>
                        <div className="grade-label">Average Grade</div>
                      </div>
                      <p>Based on quiz scores and assignments</p>
                    </div>

                    <div className="progress-card">
                      <h3>Study Habits</h3>
                      <div className="study-stats">
                        <div className="study-stat">
                          <span className="stat-icon">🔥</span>
                          <span className="stat-value">{selectedStudent.currentStreak}</span>
                          <span className="stat-label">Day Streak</span>
                        </div>
                        <div className="study-stat">
                          <span className="stat-icon">⏰</span>
                          <span className="stat-value">{studentProgress.studyTimeThisWeek}h</span>
                          <span className="stat-label">This Week</span>
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="recent-activity">
                    <h3>Recent Activity</h3>
                    <div className="activity-list">
                      <div className="activity-item">
                        <div className="activity-icon">📚</div>
                        <div className="activity-content">
                          <h4>Completed Mathematics Lesson 5</h4>
                          <p>2 hours ago • Score: 95%</p>
                        </div>
                      </div>
                      <div className="activity-item">
                        <div className="activity-icon">✅</div>
                        <div className="activity-content">
                          <h4>Submitted Physics Assignment</h4>
                          <p>1 day ago • Grade: 89%</p>
                        </div>
                      </div>
                      <div className="activity-item">
                        <div className="activity-icon">🏆</div>
                        <div className="activity-content">
                          <h4>Earned "Week Warrior" Badge</h4>
                          <p>3 days ago • +100 points</p>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {activeTab === "courses" && (
                <div className="courses-section">
                  <h3>Course Progress</h3>
                  <div className="courses-list">
                    {studentCourses.map(course => (
                      <div key={course.id} className="course-progress-item">
                        <div className="course-info">
                          <h4>{course.title}</h4>
                          <div className="course-meta">
                            <span className={`status ${course.status}`}>{course.status}</span>
                            <span>Grade: {course.grade}%</span>
                          </div>
                        </div>
                        <div className="course-progress">
                          <div className="progress-bar">
                            <div
                              className="progress-fill"
                              style={{width: `${course.progress}%`}}
                            ></div>
                          </div>
                          <span className="progress-text">{course.progress}% Complete</span>
                        </div>
                        <div className="course-dates">
                          <div>Last: {new Date(course.lastActivity).toLocaleDateString()}</div>
                          {course.nextDeadline && (
                            <div>Due: {new Date(course.nextDeadline).toLocaleDateString()}</div>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {activeTab === "achievements" && (
                <div className="achievements-section">
                  <h3>Recent Achievements</h3>
                  <div className="achievements-grid">
                    {studentProgress?.achievements?.map(achievement => (
                      <div key={achievement.id} className="achievement-card">
                        <div className="achievement-icon">{achievement.icon}</div>
                        <div className="achievement-content">
                          <h3>{achievement.name}</h3>
                          <p>Earned on {new Date(achievement.date).toLocaleDateString()}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Notifications Sidebar */}
        <div className="notifications-sidebar">
          <h3>Notifications</h3>
          <div className="notifications-list">
            {notifications.map(notification => (
              <div
                key={notification.id}
                className={`notification-item ${notification.read ? 'read' : 'unread'}`}
                onClick={() => !notification.read && markNotificationRead(notification.id)}
              >
                <div className="notification-icon">
                  {notification.type === 'achievement' ? '🏆' :
                   notification.type === 'deadline' ? '⏰' :
                   notification.type === 'grade' ? '📊' : '📢'}
                </div>
                <div className="notification-content">
                  <h4>{notification.title}</h4>
                  <p>{notification.message}</p>
                  <small>{new Date(notification.date).toLocaleDateString()}</small>
                </div>
                {!notification.read && <div className="unread-indicator"></div>}
              </div>
            ))}
          </div>
        </div>
      </div>

      <style jsx>{`
        .parent-portal {
          min-height: 100vh;
          background: #f8f9fa;
          padding: 2rem;
        }

        .portal-header {
          text-align: center;
          margin-bottom: 2rem;
        }

        .portal-header h1 {
          color: #2c3e50;
          margin-bottom: 0.5rem;
        }

        .portal-header p {
          color: #6c757d;
          font-size: 1.1rem;
        }

        .portal-content {
          max-width: 1400px;
          margin: 0 auto;
          display: grid;
          grid-template-columns: 1fr 400px;
          gap: 2rem;
        }

        .students-section {
          background: white;
          padding: 2rem;
          border-radius: 12px;
          box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }

        .students-section h2 {
          margin: 0 0 1.5rem 0;
          color: #2c3e50;
        }

        .students-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
          gap: 1rem;
        }

        .student-card {
          display: flex;
          align-items: center;
          padding: 1.5rem;
          border: 2px solid #e9ecef;
          border-radius: 12px;
          cursor: pointer;
          transition: all 0.3s;
        }

        .student-card:hover {
          border-color: #667eea;
          box-shadow: 0 4px 12px rgba(102, 126, 234, 0.2);
        }

        .student-card.selected {
          border-color: #667eea;
          background: #f0f2ff;
        }

        .student-avatar {
          font-size: 3rem;
          margin-right: 1rem;
        }

        .student-info {
          flex: 1;
        }

        .student-info h3 {
          margin: 0 0 0.25rem 0;
          color: #2c3e50;
        }

        .student-grade {
          color: #6c757d;
          margin-bottom: 0.75rem;
        }

        .student-stats {
          display: flex;
          gap: 1rem;
        }

        .stat {
          text-align: center;
        }

        .stat-value {
          display: block;
          font-size: 1.25rem;
          font-weight: bold;
          color: #667eea;
        }

        .stat-label {
          font-size: 0.8rem;
          color: #6c757d;
        }

        .student-actions {
          margin-left: 1rem;
        }

        .student-details {
          background: white;
          border-radius: 12px;
          box-shadow: 0 4px 6px rgba(0,0,0,0.1);
          overflow: hidden;
        }

        .details-header {
          padding: 2rem;
          background: linear-gradient(135deg, #667eea, #764ba2);
          color: white;
        }

        .student-summary {
          display: flex;
          align-items: center;
          gap: 2rem;
        }

        .student-avatar-large {
          font-size: 4rem;
        }

        .student-summary-info h2 {
          margin: 0 0 0.5rem 0;
          font-size: 2rem;
        }

        .summary-stats {
          display: flex;
          gap: 2rem;
        }

        .summary-stat {
          text-align: center;
        }

        .summary-stat .stat-value {
          display: block;
          font-size: 1.5rem;
          font-weight: bold;
        }

        .summary-stat .stat-label {
          color: rgba(255,255,255,0.8);
          font-size: 0.9rem;
        }

        .details-tabs {
          display: flex;
          background: #f8f9fa;
          border-bottom: 1px solid #e9ecef;
        }

        .details-tabs button {
          flex: 1;
          padding: 1rem;
          border: none;
          background: none;
          color: #6c757d;
          cursor: pointer;
          font-weight: 500;
          transition: all 0.3s;
        }

        .details-tabs button.active {
          color: #667eea;
          border-bottom: 3px solid #667eea;
          background: white;
        }

        .details-content {
          padding: 2rem;
        }

        .progress-overview {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
          gap: 2rem;
          margin-bottom: 3rem;
        }

        .progress-card {
          text-align: center;
          padding: 2rem;
          background: #f8f9fa;
          border-radius: 12px;
        }

        .progress-card h3 {
          margin: 0 0 1.5rem 0;
          color: #2c3e50;
        }

        .progress-circle {
          width: 120px;
          height: 120px;
          border-radius: 50%;
          background: conic-gradient(#667eea ${studentProgress?.overallProgress || 0}%, #e9ecef 0%);
          display: flex;
          align-items: center;
          justify-content: center;
          margin: 0 auto 1rem;
        }

        .progress-text {
          font-size: 1.5rem;
          font-weight: bold;
          color: #2c3e50;
        }

        .grade-display {
          margin: 1rem 0;
        }

        .grade-value {
          font-size: 2.5rem;
          font-weight: bold;
          color: #28a745;
        }

        .grade-label {
          color: #6c757d;
          font-size: 0.9rem;
        }

        .study-stats {
          display: flex;
          justify-content: space-around;
          margin: 1rem 0;
        }

        .study-stat {
          text-align: center;
        }

        .study-stat .stat-icon {
          display: block;
          font-size: 2rem;
          margin-bottom: 0.5rem;
        }

        .recent-activity h3 {
          margin: 0 0 1.5rem 0;
          color: #2c3e50;
        }

        .activity-list {
          display: grid;
          gap: 1rem;
        }

        .activity-item {
          display: flex;
          align-items: center;
          gap: 1rem;
          padding: 1rem;
          background: #f8f9fa;
          border-radius: 8px;
        }

        .activity-icon {
          font-size: 1.5rem;
        }

        .activity-content h4 {
          margin: 0 0 0.25rem 0;
          color: #2c3e50;
        }

        .activity-content p {
          margin: 0;
          color: #6c757d;
          font-size: 0.9rem;
        }

        .courses-list {
          display: grid;
          gap: 1rem;
        }

        .course-progress-item {
          display: grid;
          grid-template-columns: 1fr 150px 120px;
          gap: 1rem;
          padding: 1.5rem;
          background: #f8f9fa;
          border-radius: 8px;
          align-items: center;
        }

        .course-info h4 {
          margin: 0 0 0.5rem 0;
          color: #2c3e50;
        }

        .course-meta {
          display: flex;
          gap: 1rem;
          align-items: center;
        }

        .status {
          padding: 0.25rem 0.75rem;
          border-radius: 12px;
          font-size: 0.8rem;
          font-weight: 500;
        }

        .status.active {
          background: #d4edda;
          color: #155724;
        }

        .status.completed {
          background: #d1ecf1;
          color: #0c5460;
        }

        .course-progress {
          text-align: center;
        }

        .progress-bar {
          width: 100%;
          height: 8px;
          background: #e9ecef;
          border-radius: 4px;
          margin-bottom: 0.5rem;
          overflow: hidden;
        }

        .progress-fill {
          height: 100%;
          background: linear-gradient(90deg, #667eea, #764ba2);
          border-radius: 4px;
          transition: width 0.3s;
        }

        .progress-text {
          font-size: 0.8rem;
          color: #6c757d;
        }

        .course-dates {
          font-size: 0.8rem;
          color: #6c757d;
        }

        .achievements-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
          gap: 1rem;
        }

        .achievement-card {
          display: flex;
          align-items: center;
          gap: 1rem;
          padding: 1rem;
          background: #f8f9fa;
          border-radius: 8px;
        }

        .achievement-icon {
          font-size: 2rem;
        }

        .achievement-content h3 {
          margin: 0 0 0.25rem 0;
          color: #2c3e50;
        }

        .achievement-content p {
          margin: 0;
          color: #6c757d;
          font-size: 0.9rem;
        }

        .notifications-sidebar {
          background: white;
          padding: 2rem;
          border-radius: 12px;
          box-shadow: 0 4px 6px rgba(0,0,0,0.1);
          height: fit-content;
        }

        .notifications-sidebar h3 {
          margin: 0 0 1.5rem 0;
          color: #2c3e50;
        }

        .notifications-list {
          display: grid;
          gap: 1rem;
        }

        .notification-item {
          display: flex;
          align-items: flex-start;
          gap: 1rem;
          padding: 1rem;
          background: #f8f9fa;
          border-radius: 8px;
          cursor: pointer;
          transition: all 0.3s;
        }

        .notification-item:hover {
          background: #e9ecef;
        }

        .notification-item.unread {
          border-left: 4px solid #667eea;
        }

        .notification-icon {
          font-size: 1.5rem;
          margin-top: 0.25rem;
        }

        .notification-content h4 {
          margin: 0 0 0.5rem 0;
          color: #2c3e50;
          font-size: 0.9rem;
        }

        .notification-content p {
          margin: 0.25rem 0;
          color: #6c757d;
          font-size: 0.8rem;
          line-height: 1.4;
        }

        .unread-indicator {
          width: 8px;
          height: 8px;
          background: #667eea;
          border-radius: 50%;
          margin-top: 0.5rem;
        }

        .btn {
          padding: 0.5rem 1rem;
          border: none;
          border-radius: 6px;
          cursor: pointer;
          font-weight: 500;
          font-size: 0.9rem;
        }

        .btn.small {
          padding: 0.375rem 0.75rem;
          font-size: 0.8rem;
        }

        @media (max-width: 1024px) {
          .portal-content {
            grid-template-columns: 1fr;
          }

          .notifications-sidebar {
            order: -1;
          }
        }

        @media (max-width: 768px) {
          .students-grid {
            grid-template-columns: 1fr;
          }

          .student-card {
            flex-direction: column;
            text-align: center;
          }

          .student-stats {
            justify-content: center;
          }

          .progress-overview {
            grid-template-columns: 1fr;
          }

          .course-progress-item {
            grid-template-columns: 1fr;
            text-align: center;
          }
        }
      `}</style>
    </div>
  );
}

export default ParentPortal;