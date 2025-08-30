import React, { useEffect, useState } from "react";
import api from "../services/api";
import useSessionId from "../hooks/useSessionId";
import EnhancedCourseViewer from "../components/EnhancedCourseViewer";
import EnhancedChat from "../components/EnhancedChat";

function CourseListItem({ course, me, refresh }) {
  const [viewMode, setViewMode] = useState("overview"); // overview, content, chat, students
  const sessionId = useSessionId(course.id);
  const [assignments, setAssignments] = useState([]);
  const [enrolledStudents, setEnrolledStudents] = useState([]);
  const [selectedStudent, setSelectedStudent] = useState(null);
  const [studentProgress, setStudentProgress] = useState(null);
  const [aiAnalytics, setAiAnalytics] = useState(null);

  useEffect(()=>{ api.get(`/courses/${course.id}/assignments`).then(r=>setAssignments(r.data)); },[course.id]);

  const send = async () => {
    if (!chatInput.trim()) return;
    const msg = { id: crypto.randomUUID(), role: "user", message: chatInput, created_at: new Date().toISOString() };
    setChat((c) => [...c, msg]);
    setChatInput("");
    setSending(true);
    try {
      const res = await api.post(`/ai/tutor`, { course_id: course.id, session_id: sessionId, message: msg.message });
      const reply = { id: crypto.randomUUID(), role: "assistant", message: res.data.reply, created_at: new Date().toISOString() };
      setChat((c) => [...c, reply]);
    } catch (err) {
      // Fallback to regular chat
      try {
        const res = await api.post(`/ai/chat`, { course_id: course.id, session_id: sessionId, message: msg.message });
        const reply = { id: crypto.randomUUID(), role: "assistant", message: res.data.reply, created_at: new Date().toISOString() };
        setChat((c) => [...c, reply]);
      } catch (fallbackErr) {
        const reply = { id: crypto.randomUUID(), role: "assistant", message: "Sorry, I'm having trouble responding right now.", created_at: new Date().toISOString() };
        setChat((c) => [...c, reply]);
      }
    } finally { setSending(false); }
  };

  const addLesson = async () => {
    const title = prompt("Lesson title"); if (!title) return;
    const content = prompt("Lesson content (optional)") || "";
    await api.post(`/courses/${course.id}/lessons`, { title, content });
    alert("Lesson added. Refresh course list to see updates.");
  };

  const createAssignment = async () => {
    const title = prompt("Assignment title"); if (!title) return;
    const description = prompt("Description") || "";
    await api.post(`/courses/${course.id}/assignments`, { title, description, rubric: ["Clarity", "Completeness"] });
    const r = await api.get(`/courses/${course.id}/assignments`); setAssignments(r.data);
  };

  const editCourse = async () => {
    const newTitle = prompt("New title", course.title);
    if (newTitle) {
      await api.put(`/courses/${course.id}`, { title: newTitle });
      alert("Course updated.");
    }
  };


  const deleteCourse = async () => {
    if (confirm("Delete course and all related data?")) {
      await api.delete(`/courses/${course.id}`);
      refresh(); // Refresh course list
    }
  };

  const viewStudentProgress = async (sid) => {
    const r = await api.get(`/courses/${course.id}/students/${sid}/progress`);
    setSelectedStudent(sid);
    setStudentProgress(r.data);
  };

  const sendNotification = async (sid) => {
    const title = prompt("Notification title");
    const message = prompt("Notification message");
    if (title && message) {
      await api.post(`/notifications/send/${sid}`, { title, message, type: "course" });
      alert("Notification sent");
    }
  };

  const removeStudent = async (sid) => {
    if (confirm("Remove student from course?")) {
      await api.delete(`/courses/${course.id}/students/${sid}`);
      setEnrolledStudents(s => s.filter(st => st.id !== sid));
      alert("Student removed");
    }
  };

  const generateQuiz = async (lessonId) => {
    await api.post(`/courses/lessons/${lessonId}/quiz/generate`);
    alert("Quiz generated. Refresh course to see.");
  };

  const viewStudents = async () => {
    const r = await api.get(`/courses/${course.id}/students`);
    setEnrolledStudents(r.data);
  };

  const getAiAnalytics = async () => {
    const r = await api.get(`/analytics/ai/course/${course.id}`);
    setAiAnalytics(r.data);
  };

  const aiGrade = async (aid) => {
    await api.post(`/assignments/${aid}/grade/ai`);
    alert("AI grading completed.");
  };

  return (
    <div className="enhanced-course-list-item">
      <div className="course-header" onClick={() => setViewMode(viewMode === "overview" ? "content" : "overview")}>
        <div className="course-info">
          <div className="course-title">{course.title}</div>
          <div className="course-meta">
            {course.audience} • {course.difficulty} • {course.lessons?.length || 0} lessons • 👥 {course.enrolled_user_ids?.length || 0} students
          </div>
        </div>
        <div className="course-status">
          <span className={`status ${course.published ? 'published' : 'draft'}`}>
            {course.published ? 'Published' : 'Draft'}
          </span>
        </div>
      </div>

      {viewMode === "overview" && (
        <div className="course-actions">
          <button className="btn small" onClick={() => setViewMode("content")}>
            📖 View Content
          </button>
          <button className="btn small" onClick={() => setViewMode("chat")}>
            💬 AI Chat
          </button>
          <button className="btn small" onClick={() => setViewMode("students")}>
            👥 Students
          </button>
          <button className="btn small secondary" onClick={editCourse}>
            ✏️ Edit
          </button>
          <button className="btn small error" onClick={deleteCourse}>
            🗑️ Delete
          </button>
        </div>
      )}

      {viewMode === "content" && (
        <div className="course-content-view">
          <div className="content-header">
            <button className="back-btn" onClick={() => setViewMode("overview")}>
              ← Back to Overview
            </button>
            <div className="content-actions">
              <button className="btn small" onClick={addLesson}>+ Add Lesson</button>
              <button className="btn small" onClick={createAssignment}>+ Create Assignment</button>
            </div>
          </div>
          <EnhancedCourseViewer
            course={course}
            onProgressUpdate={(lessonId, completed) => {
              // Handle instructor progress updates if needed
              console.log('Instructor progress update:', lessonId, completed);
            }}
            onQuizSubmit={(quizId, isCorrect) => {
              // Handle quiz submissions
              console.log('Quiz submitted:', quizId, isCorrect);
            }}
          />
        </div>
      )}

      {viewMode === "chat" && (
        <div className="course-chat-view">
          <div className="chat-header">
            <button className="back-btn" onClick={() => setViewMode("overview")}>
              ← Back to Overview
            </button>
            <h3>AI Course Assistant</h3>
          </div>
          <EnhancedChat
            courseId={course.id}
            sessionId={sessionId}
            onMessageSent={(message) => {
              // Handle message sent
              console.log('Message sent:', message);
            }}
          />
        </div>
      )}

      {viewMode === "students" && (
        <div className="course-students-view">
          <div className="students-header">
            <button className="back-btn" onClick={() => setViewMode("overview")}>
              ← Back to Overview
            </button>
            <h3>Enrolled Students</h3>
            <button className="btn small" onClick={viewStudents}>Refresh</button>
          </div>

          {enrolledStudents.length > 0 ? (
            <div className="students-list">
              {enrolledStudents.map(student => (
                <div key={student.id} className="student-card">
                  <div className="student-info">
                    <div className="student-name">{student.name}</div>
                    <div className="student-email">{student.email}</div>
                  </div>
                  <div className="student-actions">
                    <button className="btn small" onClick={() => viewStudentProgress(student.id)}>
                      📊 Progress
                    </button>
                    <button className="btn small" onClick={() => sendNotification(student.id)}>
                      📢 Notify
                    </button>
                    <button className="btn small error" onClick={() => removeStudent(student.id)}>
                      ❌ Remove
                    </button>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="empty-state">
              <p>No students enrolled yet</p>
              <button className="btn" onClick={viewStudents}>Load Students</button>
            </div>
          )}

          {selectedStudent && studentProgress && (
            <div className="student-progress-modal">
              <div className="modal-content">
                <h4>Student Progress</h4>
                <div className="progress-stats">
                  <div className="stat">
                    <span className="label">Overall Progress:</span>
                    <span className="value">{studentProgress.overall_progress?.toFixed(1)}%</span>
                  </div>
                  <div className="stat">
                    <span className="label">Completed:</span>
                    <span className="value">{studentProgress.completed ? "Yes" : "No"}</span>
                  </div>
                </div>
                <div className="lesson-progress">
                  <h5>Lesson Progress:</h5>
                  <div className="progress-list">
                    {studentProgress.lessons_progress?.map(lp => (
                      <div key={lp.lesson_id} className="progress-item">
                        <span className="lesson-id">{lp.lesson_id}</span>
                        <span className={`status ${lp.completed ? 'completed' : 'pending'}`}>
                          {lp.completed ? '✅ Completed' : '⏳ Pending'}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      <style jsx>{`
        .enhanced-course-list-item {
          background: rgba(255, 255, 255, 0.9);
          backdrop-filter: blur(20px);
          border-radius: var(--radius-xl);
          box-shadow: var(--shadow-lg);
          margin-bottom: var(--space-4);
          overflow: hidden;
          transition: all var(--transition-normal);
        }

        .course-header {
          padding: var(--space-4) var(--space-6);
          display: flex;
          justify-content: space-between;
          align-items: center;
          cursor: pointer;
          transition: background-color var(--transition-fast);
        }

        .course-header:hover {
          background: rgba(0, 0, 0, 0.02);
        }

        .course-info {
          flex: 1;
        }

        .course-title {
          font-size: 1.25rem;
          font-weight: 700;
          color: var(--gray-900);
          margin-bottom: var(--space-1);
        }

        .course-meta {
          font-size: 0.875rem;
          color: var(--gray-600);
        }

        .course-status .status {
          padding: var(--space-1) var(--space-3);
          border-radius: var(--radius-full);
          font-size: 0.75rem;
          font-weight: 600;
          text-transform: uppercase;
        }

        .status.published {
          background: var(--success-100);
          color: var(--success-700);
        }

        .status.draft {
          background: var(--warning-100);
          color: var(--warning-700);
        }

        .course-actions {
          padding: 0 var(--space-6) var(--space-4);
          display: flex;
          gap: var(--space-2);
          flex-wrap: wrap;
        }

        .course-content-view,
        .course-chat-view,
        .course-students-view {
          border-top: 1px solid var(--gray-200);
        }

        .content-header,
        .chat-header,
        .students-header {
          padding: var(--space-4) var(--space-6);
          display: flex;
          justify-content: space-between;
          align-items: center;
          background: var(--gray-50);
          border-bottom: 1px solid var(--gray-200);
        }

        .back-btn {
          background: none;
          border: none;
          color: var(--primary-600);
          cursor: pointer;
          font-weight: 500;
          display: flex;
          align-items: center;
          gap: var(--space-2);
          transition: color var(--transition-fast);
        }

        .back-btn:hover {
          color: var(--primary-700);
        }

        .content-actions {
          display: flex;
          gap: var(--space-2);
        }

        .students-list {
          padding: var(--space-4) var(--space-6);
          display: grid;
          gap: var(--space-3);
        }

        .student-card {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: var(--space-4);
          background: white;
          border-radius: var(--radius-lg);
          box-shadow: var(--shadow-sm);
        }

        .student-info .student-name {
          font-weight: 600;
          color: var(--gray-900);
          margin-bottom: var(--space-1);
        }

        .student-info .student-email {
          font-size: 0.875rem;
          color: var(--gray-600);
        }

        .student-actions {
          display: flex;
          gap: var(--space-2);
        }

        .empty-state {
          padding: var(--space-8);
          text-align: center;
          color: var(--gray-500);
        }

        .student-progress-modal {
          position: fixed;
          top: 0;
          left: 0;
          right: 0;
          bottom: 0;
          background: rgba(0, 0, 0, 0.5);
          display: flex;
          align-items: center;
          justify-content: center;
          z-index: 1000;
        }

        .modal-content {
          background: white;
          padding: var(--space-6);
          border-radius: var(--radius-xl);
          max-width: 500px;
          width: 90%;
          max-height: 80vh;
          overflow-y: auto;
        }

        .progress-stats {
          display: grid;
          gap: var(--space-3);
          margin-bottom: var(--space-6);
        }

        .stat {
          display: flex;
          justify-content: space-between;
          align-items: center;
        }

        .stat .label {
          font-weight: 500;
          color: var(--gray-700);
        }

        .stat .value {
          font-weight: 700;
          color: var(--gray-900);
        }

        .lesson-progress h5 {
          margin-bottom: var(--space-3);
          color: var(--gray-900);
        }

        .progress-list {
          display: grid;
          gap: var(--space-2);
        }

        .progress-item {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: var(--space-2) var(--space-3);
          background: var(--gray-50);
          border-radius: var(--radius-md);
        }

        .progress-item .lesson-id {
          font-weight: 500;
          color: var(--gray-700);
        }

        .progress-item .status.completed {
          color: var(--success-600);
          font-weight: 600;
        }

        .progress-item .status.pending {
          color: var(--warning-600);
          font-weight: 600;
        }

        /* Responsive Design */
        @media (max-width: 768px) {
          .course-header {
            padding: var(--space-3) var(--space-4);
            flex-direction: column;
            align-items: flex-start;
            gap: var(--space-2);
          }

          .course-actions {
            padding: 0 var(--space-4) var(--space-3);
            justify-content: center;
          }

          .content-header,
          .chat-header,
          .students-header {
            padding: var(--space-3) var(--space-4);
            flex-direction: column;
            gap: var(--space-3);
            text-align: center;
          }

          .student-card {
            flex-direction: column;
            align-items: flex-start;
            gap: var(--space-3);
          }

          .student-actions {
            width: 100%;
            justify-content: center;
          }
        }

        @media (max-width: 480px) {
          .course-actions {
            flex-direction: column;
          }

          .course-actions .btn {
            width: 100%;
          }

          .content-actions {
            flex-direction: column;
            width: 100%;
          }

          .content-actions .btn {
            width: 100%;
          }

          .student-actions {
            flex-direction: column;
            width: 100%;
          }

          .student-actions .btn {
            width: 100%;
          }
        }
      `}</style>
    </div>
  );
}

function InstructorDashboard({ me }) {
  const [activeTab, setActiveTab] = useState("courses");
  const [title, setTitle] = useState("");
  const [audience, setAudience] = useState("Beginners");
  const [difficulty, setDifficulty] = useState("beginner");
  const [courses, setCourses] = useState([]);
  const [topic, setTopic] = useState("");
  const [lessonsCount, setLessonsCount] = useState(5);
  const [error, setError] = useState("");
  const [analytics, setAnalytics] = useState(null);
  const [selectedStudent, setSelectedStudent] = useState(null);
  const [studentProgress, setStudentProgress] = useState(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [courseForm, setCourseForm] = useState({
    title: "",
    audience: "Beginners",
    difficulty: "beginner",
    description: "",
    tags: []
  });

  const refresh = () => api.get(`/courses`).then(r => setCourses(r.data));
  useEffect(() => { refresh(); }, []);
  useEffect(() => { api.get(`/analytics/instructor`).then(r => setAnalytics(r.data)); }, []);

  const createCourse = async (e) => {
    e.preventDefault(); setError("");
    try {
      await api.post(`/courses`, courseForm);
      setCourseForm({ title: "", audience: "Beginners", difficulty: "beginner", description: "", tags: [] });
      setShowCreateModal(false);
      refresh();
    } catch (err) { setError(err?.response?.data?.detail || err.message); }
  };

  const generateCourse = async (e) => {
    e.preventDefault(); setError("");
    try {
      await api.post(`/courses/ai/generate_course`, {
        topic,
        audience,
        difficulty,
        lessons_count: Number(lessonsCount)
      });
      setTopic(""); refresh();
    } catch (err) { setError(err?.response?.data?.detail || err.message); }
  };

  const publishCourse = async (courseId) => {
    try {
      await api.put(`/courses/${courseId}`, { published: true });
      refresh();
      alert("Course published successfully!");
    } catch (error) {
      alert("Error publishing course");
    }
  };

  return (
    <div className="instructor-dashboard">
      <div className="instructor-header">
        <div className="header-content">
          <h1>Instructor Dashboard</h1>
          <p>Welcome back, {me?.name}!</p>
        </div>
        <div className="header-actions">
          <button className="btn primary" onClick={() => setShowCreateModal(true)}>
            + Create Course
          </button>
        </div>
      </div>

      <div className="instructor-tabs">
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
          My Courses
        </button>
        <button
          className={activeTab === "analytics" ? "active" : ""}
          onClick={() => setActiveTab("analytics")}
        >
          Analytics
        </button>
        <button
          className={activeTab === "tools" ? "active" : ""}
          onClick={() => setActiveTab("tools")}
        >
          Tools
        </button>
      </div>

      <div className="instructor-content">
        {activeTab === "overview" && (
          <div className="overview-section">
            <div className="stats-grid">
              <div className="stat-card">
                <h3>Total Courses</h3>
                <div className="stat-number">{courses.length}</div>
                <div className="stat-detail">
                  {courses.filter(c => c.published).length} Published<br/>
                  {courses.filter(c => !c.published).length} Drafts
                </div>
              </div>
              <div className="stat-card">
                <h3>Total Students</h3>
                <div className="stat-number">
                  {courses.reduce((sum, c) => sum + (c.enrolled_user_ids?.length || 0), 0)}
                </div>
                <div className="stat-detail">Across all courses</div>
              </div>
              <div className="stat-card">
                <h3>Completion Rate</h3>
                <div className="stat-number">
                  {courses.length > 0 ?
                    Math.round(courses.reduce((sum, c) => sum + (c.enrolled_user_ids?.length || 0), 0) / courses.length) : 0}%
                </div>
                <div className="stat-detail">Average per course</div>
              </div>
              <div className="stat-card">
                <h3>AI Interactions</h3>
                <div className="stat-number">∞</div>
                <div className="stat-detail">Unlimited AI support</div>
              </div>
            </div>

            <div className="quick-actions">
              <h3>Quick Actions</h3>
              <div className="actions-grid">
                <button className="action-card" onClick={() => setShowCreateModal(true)}>
                  <div className="action-icon">📚</div>
                  <div className="action-title">Create Course</div>
                  <div className="action-desc">Build a new course from scratch</div>
                </button>
                <button className="action-card" onClick={() => setActiveTab("tools")}>
                  <div className="action-icon">🤖</div>
                  <div className="action-title">AI Generator</div>
                  <div className="action-desc">Generate courses with AI</div>
                </button>
                <button className="action-card" onClick={() => setActiveTab("analytics")}>
                  <div className="action-icon">📊</div>
                  <div className="action-title">View Analytics</div>
                  <div className="action-desc">Track student progress</div>
                </button>
                <button className="action-card" onClick={() => {/* Announcements */}}>
                  <div className="action-icon">📢</div>
                  <div className="action-title">Announcements</div>
                  <div className="action-desc">Send course updates</div>
                </button>
              </div>
            </div>
          </div>
        )}

        {activeTab === "courses" && (
          <div className="courses-section">
            <div className="section-header">
              <h2>My Courses</h2>
              <div className="course-filters">
                <select>
                  <option>All Courses</option>
                  <option>Published</option>
                  <option>Drafts</option>
                </select>
              </div>
            </div>

            <div className="courses-grid">
              {courses.map(course => (
                <div key={course.id} className="course-card">
                  <div className="course-header">
                    <h3>{course.title}</h3>
                    <span className={`status ${course.published ? 'published' : 'draft'}`}>
                      {course.published ? 'Published' : 'Draft'}
                    </span>
                  </div>

                  <div className="course-meta">
                    <span>👥 {course.enrolled_user_ids?.length || 0} students</span>
                    <span>📚 {course.lessons?.length || 0} lessons</span>
                    <span>🎯 {course.difficulty}</span>
                  </div>

                  <div className="course-description">
                    {course.description || "No description provided"}
                  </div>

                  <div className="course-actions">
                    <button className="btn small" onClick={() => {/* Edit course */}}>
                      Edit
                    </button>
                    {!course.published && (
                      <button className="btn primary small" onClick={() => publishCourse(course.id)}>
                        Publish
                      </button>
                    )}
                    <button className="btn secondary small" onClick={() => {/* View analytics */}}>
                      Analytics
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {activeTab === "analytics" && (
          <div className="analytics-section">
            <h2>Course Analytics</h2>
            {analytics && (
              <div className="analytics-grid">
                <div className="analytics-card">
                  <h3>Course Performance</h3>
                  <div className="metric">
                    <span className="metric-label">Total Courses:</span>
                    <span className="metric-value">{analytics.courses}</span>
                  </div>
                  <div className="metric">
                    <span className="metric-label">Total Students:</span>
                    <span className="metric-value">{analytics.students}</span>
                  </div>
                </div>

                <div className="analytics-card">
                  <h3>Student Engagement</h3>
                  <div className="engagement-chart">
                    📈 Student activity trends
                  </div>
                </div>

                <div className="analytics-card">
                  <h3>AI Usage</h3>
                  <div className="ai-stats">
                    <div>🤖 AI Tutoring Sessions: Active</div>
                    <div>📝 AI Grading: Available</div>
                    <div>📊 AI Analytics: Enabled</div>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {activeTab === "tools" && (
          <div className="tools-section">
            <h2>AI Teaching Tools</h2>

            <div className="tools-grid">
              <div className="tool-card">
                <h3>Course Generator</h3>
                <p>Generate complete courses using AI</p>
                <form onSubmit={generateCourse} className="tool-form">
                  <div className="form-group">
                    <label>Topic</label>
                    <input
                      type="text"
                      value={topic}
                      onChange={(e) => setTopic(e.target.value)}
                      placeholder="e.g., Introduction to Machine Learning"
                      required
                    />
                  </div>
                  <div className="form-row">
                    <div className="form-group">
                      <label>Audience</label>
                      <input
                        type="text"
                        value={audience}
                        onChange={(e) => setAudience(e.target.value)}
                        placeholder="e.g., Beginners"
                      />
                    </div>
                    <div className="form-group">
                      <label>Lessons</label>
                      <input
                        type="number"
                        min={1}
                        max={20}
                        value={lessonsCount}
                        onChange={(e) => setLessonsCount(e.target.value)}
                      />
                    </div>
                  </div>
                  <button type="submit" className="btn primary">
                    Generate Course
                  </button>
                </form>
              </div>

              <div className="tool-card">
                <h3>Content Analyzer</h3>
                <p>Analyze course content for improvements</p>
                <button className="btn secondary" onClick={() => alert("Content analysis feature coming soon!")}>
                  Analyze Content
                </button>
              </div>

              <div className="tool-card">
                <h3>Quiz Generator</h3>
                <p>Generate quizzes for any lesson</p>
                <button className="btn secondary" onClick={() => alert("Quiz generation available in course editor!")}>
                  Generate Quiz
                </button>
              </div>

              <div className="tool-card">
                <h3>Student Insights</h3>
                <p>Get AI-powered student performance insights</p>
                <button className="btn secondary" onClick={() => setActiveTab("analytics")}>
                  View Insights
                </button>
              </div>
            </div>
          </div>
        )}
      </div>

      {showCreateModal && (
        <div className="modal-overlay">
          <div className="modal">
            <h3>Create New Course</h3>
            <form onSubmit={createCourse}>
              <div className="form-group">
                <label>Course Title</label>
                <input
                  type="text"
                  value={courseForm.title}
                  onChange={(e) => setCourseForm({...courseForm, title: e.target.value})}
                  required
                />
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label>Audience</label>
                  <select
                    value={courseForm.audience}
                    onChange={(e) => setCourseForm({...courseForm, audience: e.target.value})}
                  >
                    <option value="Beginners">Beginners</option>
                    <option value="Intermediate">Intermediate</option>
                    <option value="Advanced">Advanced</option>
                    <option value="All Levels">All Levels</option>
                  </select>
                </div>

                <div className="form-group">
                  <label>Difficulty</label>
                  <select
                    value={courseForm.difficulty}
                    onChange={(e) => setCourseForm({...courseForm, difficulty: e.target.value})}
                  >
                    <option value="beginner">Beginner</option>
                    <option value="intermediate">Intermediate</option>
                    <option value="advanced">Advanced</option>
                  </select>
                </div>
              </div>

              <div className="form-group">
                <label>Description</label>
                <textarea
                  value={courseForm.description}
                  onChange={(e) => setCourseForm({...courseForm, description: e.target.value})}
                  rows={4}
                  placeholder="Describe what students will learn..."
                />
              </div>

              <div className="modal-actions">
                <button type="button" className="btn secondary" onClick={() => setShowCreateModal(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn primary">
                  Create Course
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      <style jsx>{`
        .instructor-dashboard {
          min-height: 100vh;
          background: #f8f9fa;
        }

        .instructor-header {
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          color: white;
          padding: 2rem;
          display: flex;
          justify-content: space-between;
          align-items: center;
        }

        .header-content h1 {
          margin: 0 0 0.5rem 0;
          font-size: 2rem;
        }

        .header-content p {
          margin: 0;
          opacity: 0.9;
        }

        .instructor-tabs {
          background: white;
          display: flex;
          border-bottom: 1px solid #e9ecef;
        }

        .instructor-tabs button {
          padding: 1rem 2rem;
          border: none;
          background: none;
          color: #6c757d;
          cursor: pointer;
          border-bottom: 3px solid transparent;
          transition: all 0.3s;
        }

        .instructor-tabs button.active {
          color: #007bff;
          border-bottom-color: #007bff;
        }

        .instructor-content {
          padding: 2rem;
        }

        .stats-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
          gap: 2rem;
          margin-bottom: 3rem;
        }

        .stat-card {
          background: white;
          padding: 2rem;
          border-radius: 12px;
          box-shadow: 0 4px 6px rgba(0,0,0,0.1);
          text-align: center;
        }

        .stat-card h3 {
          margin: 0 0 1rem 0;
          color: #6c757d;
          font-size: 1rem;
        }

        .stat-number {
          font-size: 3rem;
          font-weight: bold;
          color: #2c3e50;
          margin-bottom: 0.5rem;
        }

        .stat-detail {
          color: #6c757d;
          font-size: 0.9rem;
        }

        .quick-actions h3 {
          margin-bottom: 1.5rem;
          color: #2c3e50;
        }

        .actions-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
          gap: 1.5rem;
        }

        .action-card {
          background: white;
          padding: 2rem;
          border-radius: 12px;
          box-shadow: 0 4px 6px rgba(0,0,0,0.1);
          border: none;
          text-align: center;
          cursor: pointer;
          transition: transform 0.3s;
        }

        .action-card:hover {
          transform: translateY(-5px);
        }

        .action-icon {
          font-size: 2rem;
          margin-bottom: 1rem;
        }

        .action-title {
          font-size: 1.2rem;
          font-weight: 600;
          color: #2c3e50;
          margin-bottom: 0.5rem;
        }

        .action-desc {
          color: #6c757d;
          font-size: 0.9rem;
        }

        .section-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 2rem;
        }

        .course-filters select {
          padding: 0.5rem 1rem;
          border: 1px solid #ddd;
          border-radius: 6px;
        }

        .courses-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
          gap: 2rem;
        }

        .course-card {
          background: white;
          border-radius: 12px;
          box-shadow: 0 4px 6px rgba(0,0,0,0.1);
          overflow: hidden;
        }

        .course-header {
          padding: 1.5rem;
          border-bottom: 1px solid #eee;
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
        }

        .course-header h3 {
          margin: 0;
          color: #2c3e50;
        }

        .status {
          padding: 0.25rem 0.75rem;
          border-radius: 20px;
          font-size: 0.8rem;
          font-weight: 500;
        }

        .status.published {
          background: #d4edda;
          color: #155724;
        }

        .status.draft {
          background: #fff3cd;
          color: #856404;
        }

        .course-meta {
          padding: 1rem 1.5rem;
          display: flex;
          gap: 1rem;
          color: #6c757d;
          font-size: 0.9rem;
        }

        .course-description {
          padding: 0 1.5rem;
          color: #6c757d;
          margin-bottom: 1rem;
        }

        .course-actions {
          padding: 1rem 1.5rem;
          border-top: 1px solid #eee;
          display: flex;
          gap: 0.5rem;
        }

        .analytics-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
          gap: 2rem;
        }

        .analytics-card {
          background: white;
          padding: 2rem;
          border-radius: 12px;
          box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }

        .metric {
          display: flex;
          justify-content: space-between;
          margin-bottom: 1rem;
        }

        .metric-label {
          color: #6c757d;
        }

        .metric-value {
          font-weight: 600;
          color: #2c3e50;
        }

        .tools-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
          gap: 2rem;
        }

        .tool-card {
          background: white;
          padding: 2rem;
          border-radius: 12px;
          box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }

        .tool-form {
          margin-top: 1rem;
        }

        .form-row {
          display: flex;
          gap: 1rem;
        }

        .form-group {
          margin-bottom: 1rem;
          flex: 1;
        }

        .form-group label {
          display: block;
          margin-bottom: 0.5rem;
          font-weight: 500;
          color: #2c3e50;
        }

        .form-group input,
        .form-group select,
        .form-group textarea {
          width: 100%;
          padding: 0.75rem;
          border: 1px solid #ddd;
          border-radius: 6px;
          font-size: 1rem;
        }

        .modal-overlay {
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

        .modal {
          background: white;
          padding: 2rem;
          border-radius: 12px;
          width: 600px;
          max-width: 90vw;
          max-height: 90vh;
          overflow-y: auto;
        }

        .modal h3 {
          margin: 0 0 2rem 0;
          color: #2c3e50;
        }

        .modal-actions {
          display: flex;
          gap: 1rem;
          justify-content: flex-end;
          margin-top: 2rem;
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
          background: #007bff;
          color: white;
        }

        .btn.secondary {
          background: #6c757d;
          color: white;
        }

        .btn.small {
          padding: 0.5rem 1rem;
          font-size: 0.9rem;
        }
      `}</style>
    </div>
  );
}

export default InstructorDashboard;