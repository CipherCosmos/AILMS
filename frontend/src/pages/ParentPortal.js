import React, { useEffect, useState } from "react";
import api from "../services/api";

function ParentPortal({ me }) {
  const [students, setStudents] = useState([]);
  const [selectedStudent, setSelectedStudent] = useState(null);
  const [studentProgress, setStudentProgress] = useState(null);
  const [studentCourses, setStudentCourses] = useState([]);
  const [notifications, setNotifications] = useState([]);
  const [activeTab, setActiveTab] = useState("overview");
  const [communicationHistory, setCommunicationHistory] = useState([]);
  const [learningGoals, setLearningGoals] = useState([]);
  const [academicAlerts, setAcademicAlerts] = useState([]);
  const [parentResources, setParentResources] = useState([]);
  const [studyPlans, setStudyPlans] = useState([]);
  const [supportTickets, setSupportTickets] = useState([]);

  useEffect(() => {
    loadStudents();
    loadNotifications();
    loadCommunicationHistory();
    loadLearningGoals();
    loadAcademicAlerts();
    loadParentResources();
    loadStudyPlans();
    loadSupportTickets();
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

  const loadCommunicationHistory = async () => {
    try {
      setCommunicationHistory([
        {
          id: "comm1",
          studentId: "student1",
          type: "message",
          content: "Great job on your math homework this week!",
          timestamp: "2024-01-25T10:30:00Z",
          direction: "parent_to_student"
        },
        {
          id: "comm2",
          studentId: "student1",
          type: "notification",
          content: "Emma completed Advanced Mathematics lesson 5",
          timestamp: "2024-01-24T15:45:00Z",
          direction: "system"
        }
      ]);
    } catch (error) {
      console.error("Error loading communication history:", error);
    }
  };

  const loadLearningGoals = async () => {
    try {
      setLearningGoals([
        {
          id: "goal1",
          studentId: "student1",
          title: "Improve Math Grade to A",
          description: "Focus on algebra and geometry concepts",
          targetDate: "2024-06-01",
          progress: 75,
          status: "on_track"
        },
        {
          id: "goal2",
          studentId: "student2",
          title: "Complete Science Fair Project",
          description: "Research and build a working model",
          targetDate: "2024-03-15",
          progress: 60,
          status: "on_track"
        }
      ]);
    } catch (error) {
      console.error("Error loading learning goals:", error);
    }
  };

  const loadAcademicAlerts = async () => {
    try {
      setAcademicAlerts([
        {
          id: "alert1",
          studentId: "student1",
          type: "warning",
          title: "Low Engagement in Physics",
          message: "Emma has not accessed Physics materials for 3 days",
          severity: "medium",
          timestamp: "2024-01-24T09:00:00Z"
        },
        {
          id: "alert2",
          studentId: "student2",
          type: "success",
          title: "Excellent Progress in English",
          message: "Alex improved his reading comprehension score by 15%",
          severity: "low",
          timestamp: "2024-01-23T14:30:00Z"
        }
      ]);
    } catch (error) {
      console.error("Error loading academic alerts:", error);
    }
  };

  const loadParentResources = async () => {
    try {
      setParentResources([
        {
          id: "res1",
          title: "Supporting Your Child's Online Learning",
          type: "guide",
          description: "Tips for parents to help their children succeed in online education",
          downloadUrl: "#",
          category: "parenting"
        },
        {
          id: "res2",
          title: "Understanding Academic Progress Reports",
          type: "video",
          description: "Learn how to interpret your child's progress reports",
          downloadUrl: "#",
          category: "academic"
        },
        {
          id: "res3",
          title: "Homework Help Strategies",
          type: "webinar",
          description: "Effective strategies for helping with homework",
          downloadUrl: "#",
          category: "support"
        }
      ]);
    } catch (error) {
      console.error("Error loading parent resources:", error);
    }
  };

  const loadStudyPlans = async () => {
    try {
      setStudyPlans([
        {
          id: "plan1",
          studentId: "student1",
          title: "Weekly Study Schedule",
          description: "Balanced study plan for Emma's courses",
          subjects: ["Math", "Physics", "English"],
          totalHours: 15,
          completedHours: 12,
          status: "active"
        },
        {
          id: "plan2",
          studentId: "student2",
          title: "Exam Preparation Plan",
          description: "Intensive preparation for mid-term exams",
          subjects: ["Math", "Science", "History"],
          totalHours: 20,
          completedHours: 8,
          status: "active"
        }
      ]);
    } catch (error) {
      console.error("Error loading study plans:", error);
    }
  };

  const loadSupportTickets = async () => {
    try {
      setSupportTickets([
        {
          id: "ticket1",
          studentId: "student1",
          title: "Technical Issue with Assignment Submission",
          description: "Emma is having trouble uploading her math assignment",
          status: "resolved",
          priority: "high",
          createdAt: "2024-01-20T08:30:00Z",
          resolvedAt: "2024-01-20T10:15:00Z"
        },
        {
          id: "ticket2",
          studentId: "student2",
          title: "Question About Course Content",
          description: "Alex needs clarification on physics chapter 3",
          status: "in_progress",
          priority: "medium",
          createdAt: "2024-01-24T16:00:00Z",
          resolvedAt: null
        }
      ]);
    } catch (error) {
      console.error("Error loading support tickets:", error);
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
              <button
                className={activeTab === "communication" ? "active" : ""}
                onClick={() => setActiveTab("communication")}
              >
                Communication
              </button>
              <button
                className={activeTab === "goals" ? "active" : ""}
                onClick={() => setActiveTab("goals")}
              >
                Learning Goals
              </button>
              <button
                className={activeTab === "alerts" ? "active" : ""}
                onClick={() => setActiveTab("alerts")}
              >
                Academic Alerts
              </button>
              <button
                className={activeTab === "resources" ? "active" : ""}
                onClick={() => setActiveTab("resources")}
              >
                Parent Resources
              </button>
              <button
                className={activeTab === "support" ? "active" : ""}
                onClick={() => setActiveTab("support")}
              >
                Support
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

              {activeTab === "communication" && (
                <div className="communication-section">
                  <h3>Communication History</h3>
                  <div className="communication-tools">
                    <button className="btn primary">Send Message</button>
                    <button className="btn secondary">Schedule Meeting</button>
                    <button className="btn secondary">Contact Teacher</button>
                  </div>

                  <div className="communication-timeline">
                    {communicationHistory.map(message => (
                      <div key={message.id} className={`message-item ${message.direction}`}>
                        <div className="message-header">
                          <span className="message-type">{message.type}</span>
                          <span className="message-time">
                            {new Date(message.timestamp).toLocaleString()}
                          </span>
                        </div>
                        <div className="message-content">
                          <p>{message.content}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {activeTab === "goals" && (
                <div className="goals-section">
                  <h3>Learning Goals & Progress</h3>
                  <div className="goals-tools">
                    <button className="btn primary">Set New Goal</button>
                    <button className="btn secondary">Review Progress</button>
                  </div>

                  <div className="goals-list">
                    {learningGoals.map(goal => (
                      <div key={goal.id} className="goal-card">
                        <div className="goal-header">
                          <h4>{goal.title}</h4>
                          <span className={`goal-status ${goal.status}`}>
                            {goal.status.replace('_', ' ')}
                          </span>
                        </div>
                        <p>{goal.description}</p>
                        <div className="goal-progress">
                          <div className="progress-bar">
                            <div
                              className="progress-fill"
                              style={{width: `${goal.progress}%`}}
                            ></div>
                          </div>
                          <span className="progress-text">{goal.progress}% Complete</span>
                        </div>
                        <div className="goal-dates">
                          <span>Target: {new Date(goal.targetDate).toLocaleDateString()}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {activeTab === "alerts" && (
                <div className="alerts-section">
                  <h3>Academic Alerts & Notifications</h3>
                  <div className="alerts-summary">
                    <div className="alert-stat">
                      <span className="stat-number">
                        {academicAlerts.filter(a => a.severity === 'high').length}
                      </span>
                      <span className="stat-label">High Priority</span>
                    </div>
                    <div className="alert-stat">
                      <span className="stat-number">
                        {academicAlerts.filter(a => a.severity === 'medium').length}
                      </span>
                      <span className="stat-label">Medium Priority</span>
                    </div>
                    <div className="alert-stat">
                      <span className="stat-number">
                        {academicAlerts.filter(a => a.severity === 'low').length}
                      </span>
                      <span className="stat-label">Low Priority</span>
                    </div>
                  </div>

                  <div className="alerts-list">
                    {academicAlerts.map(alert => (
                      <div key={alert.id} className={`alert-card ${alert.severity}`}>
                        <div className="alert-header">
                          <div className="alert-icon">
                            {alert.type === 'warning' ? '⚠️' :
                             alert.type === 'success' ? '✅' :
                             alert.type === 'info' ? 'ℹ️' : '📢'}
                          </div>
                          <div className="alert-content">
                            <h4>{alert.title}</h4>
                            <p>{alert.message}</p>
                            <small>{new Date(alert.timestamp).toLocaleString()}</small>
                          </div>
                        </div>
                        <div className="alert-actions">
                          <button className="btn small">Acknowledge</button>
                          <button className="btn small secondary">Contact Teacher</button>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {activeTab === "resources" && (
                <div className="resources-section">
                  <h3>Parent Resources & Support</h3>
                  <div className="resources-categories">
                    <button className="category-btn active">All</button>
                    <button className="category-btn">Parenting</button>
                    <button className="category-btn">Academic</button>
                    <button className="category-btn">Technical</button>
                    <button className="category-btn">Wellness</button>
                  </div>

                  <div className="resources-grid">
                    {parentResources.map(resource => (
                      <div key={resource.id} className="resource-card">
                        <div className="resource-icon">
                          {resource.type === 'guide' ? '📖' :
                           resource.type === 'video' ? '🎥' :
                           resource.type === 'webinar' ? '🎤' : '📄'}
                        </div>
                        <div className="resource-content">
                          <h4>{resource.title}</h4>
                          <p>{resource.description}</p>
                          <div className="resource-meta">
                            <span className="resource-type">{resource.type}</span>
                            <span className="resource-category">{resource.category}</span>
                          </div>
                        </div>
                        <div className="resource-actions">
                          <button className="btn small primary">Access</button>
                          <button className="btn small secondary">Download</button>
                        </div>
                      </div>
                    ))}
                  </div>

                  <div className="upcoming-webinars">
                    <h4>Upcoming Webinars</h4>
                    <div className="webinar-list">
                      <div className="webinar-item">
                        <div className="webinar-info">
                          <h5>Supporting Online Learning at Home</h5>
                          <p>Learn effective strategies for supporting your child's online education</p>
                          <small>Jan 30, 2024 • 7:00 PM EST</small>
                        </div>
                        <button className="btn small primary">Register</button>
                      </div>
                      <div className="webinar-item">
                        <div className="webinar-info">
                          <h5>Understanding Progress Reports</h5>
                          <p>Get insights into interpreting your child's academic progress</p>
                          <small>Feb 5, 2024 • 6:30 PM EST</small>
                        </div>
                        <button className="btn small primary">Register</button>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {activeTab === "support" && (
                <div className="support-section">
                  <h3>Support & Help Center</h3>
                  <div className="support-overview">
                    <div className="support-stat">
                      <span className="stat-number">
                        {supportTickets.filter(t => t.status === 'open').length}
                      </span>
                      <span className="stat-label">Open Tickets</span>
                    </div>
                    <div className="support-stat">
                      <span className="stat-number">
                        {supportTickets.filter(t => t.status === 'resolved').length}
                      </span>
                      <span className="stat-label">Resolved</span>
                    </div>
                    <div className="support-stat">
                      <span className="stat-number">2.3h</span>
                      <span className="stat-label">Avg Response</span>
                    </div>
                  </div>

                  <div className="quick-help">
                    <h4>Quick Help</h4>
                    <div className="help-grid">
                      <div className="help-card">
                        <h5>📚 Course Access Issues</h5>
                        <p>Having trouble accessing course materials?</p>
                        <button className="btn small">Get Help</button>
                      </div>
                      <div className="help-card">
                        <h5>💻 Technical Problems</h5>
                        <p>Issues with login, videos, or assignments?</p>
                        <button className="btn small">Report Issue</button>
                      </div>
                      <div className="help-card">
                        <h5>📊 Understanding Grades</h5>
                        <p>Need help interpreting progress reports?</p>
                        <button className="btn small">Learn More</button>
                      </div>
                      <div className="help-card">
                        <h5>👥 Contact Teacher</h5>
                        <p>Need to speak with your child's instructor?</p>
                        <button className="btn small">Contact Form</button>
                      </div>
                    </div>
                  </div>

                  <div className="support-tickets">
                    <div className="tickets-header">
                      <h4>Recent Support Tickets</h4>
                      <button className="btn primary">New Ticket</button>
                    </div>
                    <div className="tickets-list">
                      {supportTickets.map(ticket => (
                        <div key={ticket.id} className="ticket-item">
                          <div className="ticket-info">
                            <h5>{ticket.title}</h5>
                            <p>{ticket.description}</p>
                            <div className="ticket-meta">
                              <span className={`priority ${ticket.priority}`}>
                                {ticket.priority}
                              </span>
                              <span className={`status ${ticket.status}`}>
                                {ticket.status.replace('_', ' ')}
                              </span>
                              <small>
                                Created: {new Date(ticket.createdAt).toLocaleDateString()}
                              </small>
                            </div>
                          </div>
                          <div className="ticket-actions">
                            <button className="btn small">View Details</button>
                            {ticket.status !== 'resolved' && (
                              <button className="btn small secondary">Update</button>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
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

        .communication-section {
          max-width: 100%;
        }

        .communication-tools {
          display: flex;
          gap: 1rem;
          margin-bottom: 2rem;
          flex-wrap: wrap;
        }

        .communication-timeline {
          display: grid;
          gap: 1rem;
        }

        .message-item {
          display: flex;
          flex-direction: column;
          gap: 0.5rem;
          padding: 1rem;
          background: #f8f9fa;
          border-radius: 8px;
          border-left: 4px solid #667eea;
        }

        .message-item.parent_to_student {
          border-left-color: #28a745;
        }

        .message-item.system {
          border-left-color: #6c757d;
        }

        .message-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
        }

        .message-type {
          padding: 0.25rem 0.5rem;
          background: #667eea;
          color: white;
          border-radius: 12px;
          font-size: 0.8rem;
          font-weight: 500;
        }

        .message-time {
          color: #6c757d;
          font-size: 0.9rem;
        }

        .goals-section {
          max-width: 100%;
        }

        .goals-tools {
          display: flex;
          gap: 1rem;
          margin-bottom: 2rem;
          flex-wrap: wrap;
        }

        .goals-list {
          display: grid;
          gap: 1.5rem;
        }

        .goal-card {
          background: white;
          padding: 1.5rem;
          border-radius: 12px;
          box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }

        .goal-header {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          margin-bottom: 1rem;
        }

        .goal-header h4 {
          margin: 0;
          color: #2c3e50;
        }

        .goal-status {
          padding: 0.25rem 0.75rem;
          border-radius: 20px;
          font-size: 0.8rem;
          font-weight: 600;
          text-transform: capitalize;
        }

        .goal-status.on_track { background: #d4edda; color: #155724; }
        .goal-status.behind { background: #f8d7da; color: #721c24; }
        .goal-status.completed { background: #d1ecf1; color: #0c5460; }

        .goal-progress {
          margin: 1rem 0;
        }

        .goal-dates {
          font-size: 0.9rem;
          color: #6c757d;
        }

        .alerts-section {
          max-width: 100%;
        }

        .alerts-summary {
          display: flex;
          gap: 2rem;
          margin-bottom: 2rem;
          flex-wrap: wrap;
        }

        .alert-stat {
          text-align: center;
          padding: 1rem;
          background: white;
          border-radius: 8px;
          box-shadow: 0 2px 4px rgba(0,0,0,0.1);
          min-width: 120px;
        }

        .alert-stat .stat-number {
          display: block;
          font-size: 2rem;
          font-weight: bold;
          color: #667eea;
        }

        .alert-stat .stat-label {
          color: #6c757d;
          font-size: 0.9rem;
        }

        .alerts-list {
          display: grid;
          gap: 1rem;
        }

        .alert-card {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          padding: 1.5rem;
          border-radius: 12px;
          box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }

        .alert-card.high {
          background: #fff5f5;
          border-left: 4px solid #dc3545;
        }

        .alert-card.medium {
          background: #fffbf0;
          border-left: 4px solid #ffc107;
        }

        .alert-card.low {
          background: #f0f9ff;
          border-left: 4px solid #17a2b8;
        }

        .alert-header {
          display: flex;
          gap: 1rem;
          flex: 1;
        }

        .alert-icon {
          font-size: 1.5rem;
          margin-top: 0.25rem;
        }

        .alert-content h4 {
          margin: 0 0 0.5rem 0;
          color: #2c3e50;
        }

        .alert-content p {
          margin: 0.25rem 0;
          color: #6c757d;
          font-size: 0.9rem;
        }

        .alert-actions {
          display: flex;
          gap: 0.5rem;
          flex-direction: column;
        }

        .resources-section {
          max-width: 100%;
        }

        .resources-categories {
          display: flex;
          gap: 1rem;
          margin-bottom: 2rem;
          flex-wrap: wrap;
        }

        .category-btn {
          padding: 0.5rem 1rem;
          border: 1px solid #ddd;
          background: white;
          border-radius: 20px;
          cursor: pointer;
          font-size: 0.9rem;
          transition: all 0.3s;
        }

        .category-btn.active {
          background: #667eea;
          color: white;
          border-color: #667eea;
        }

        .resources-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
          gap: 1.5rem;
          margin-bottom: 3rem;
        }

        .resource-card {
          display: flex;
          gap: 1rem;
          padding: 1.5rem;
          background: white;
          border-radius: 12px;
          box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }

        .resource-icon {
          font-size: 2rem;
          margin-top: 0.25rem;
        }

        .resource-content {
          flex: 1;
        }

        .resource-content h4 {
          margin: 0 0 0.5rem 0;
          color: #2c3e50;
        }

        .resource-content p {
          margin: 0.25rem 0;
          color: #6c757d;
          font-size: 0.9rem;
        }

        .resource-meta {
          display: flex;
          gap: 1rem;
          margin-top: 1rem;
        }

        .resource-type,
        .resource-category {
          padding: 0.25rem 0.5rem;
          background: #e9ecef;
          color: #495057;
          border-radius: 12px;
          font-size: 0.8rem;
        }

        .resource-actions {
          display: flex;
          flex-direction: column;
          gap: 0.5rem;
        }

        .upcoming-webinars {
          background: white;
          padding: 2rem;
          border-radius: 12px;
          box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }

        .webinar-list {
          display: grid;
          gap: 1.5rem;
        }

        .webinar-item {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          padding: 1.5rem;
          background: #f8f9fa;
          border-radius: 8px;
        }

        .webinar-info h5 {
          margin: 0 0 0.5rem 0;
          color: #2c3e50;
        }

        .webinar-info p {
          margin: 0.25rem 0;
          color: #6c757d;
          font-size: 0.9rem;
        }

        .support-section {
          max-width: 100%;
        }

        .support-overview {
          display: flex;
          gap: 2rem;
          margin-bottom: 3rem;
          flex-wrap: wrap;
        }

        .support-stat {
          text-align: center;
          padding: 1rem;
          background: white;
          border-radius: 8px;
          box-shadow: 0 2px 4px rgba(0,0,0,0.1);
          min-width: 120px;
        }

        .support-stat .stat-number {
          display: block;
          font-size: 2rem;
          font-weight: bold;
          color: #667eea;
        }

        .support-stat .stat-label {
          color: #6c757d;
          font-size: 0.9rem;
        }

        .quick-help {
          background: white;
          padding: 2rem;
          border-radius: 12px;
          box-shadow: 0 2px 4px rgba(0,0,0,0.1);
          margin-bottom: 2rem;
        }

        .help-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
          gap: 1rem;
        }

        .help-card {
          padding: 1.5rem;
          background: #f8f9fa;
          border-radius: 8px;
          text-align: center;
        }

        .help-card h5 {
          margin: 0 0 0.5rem 0;
          color: #2c3e50;
        }

        .help-card p {
          margin: 0.25rem 0 1rem 0;
          color: #6c757d;
          font-size: 0.9rem;
        }

        .support-tickets {
          background: white;
          padding: 2rem;
          border-radius: 12px;
          box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }

        .tickets-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 2rem;
        }

        .tickets-list {
          display: grid;
          gap: 1rem;
        }

        .ticket-item {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          padding: 1.5rem;
          background: #f8f9fa;
          border-radius: 8px;
        }

        .ticket-info h5 {
          margin: 0 0 0.5rem 0;
          color: #2c3e50;
        }

        .ticket-info p {
          margin: 0.25rem 0;
          color: #6c757d;
          font-size: 0.9rem;
        }

        .ticket-meta {
          display: flex;
          gap: 1rem;
          align-items: center;
          margin-top: 1rem;
          flex-wrap: wrap;
        }

        .priority,
        .status {
          padding: 0.25rem 0.5rem;
          border-radius: 12px;
          font-size: 0.8rem;
          font-weight: 500;
        }

        .priority.high { background: #f8d7da; color: #721c24; }
        .priority.medium { background: #fff3cd; color: #856404; }
        .priority.low { background: #d1ecf1; color: #0c5460; }

        .status.open { background: #fff3cd; color: #856404; }
        .status.in_progress { background: #d1ecf1; color: #0c5460; }
        .status.resolved { background: #d4edda; color: #155724; }

        .ticket-actions {
          display: flex;
          gap: 0.5rem;
          flex-direction: column;
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