import React, { useEffect, useState } from "react";
import api from "../services/api";
import { useApi } from "../hooks/useApi";
import useSessionId from "../hooks/useSessionId";
import EnhancedCourseViewer from "../components/EnhancedCourseViewer";
import EnhancedChat from "../components/EnhancedChat";
import CourseContentViewer from "../components/CourseContentViewer";
import ProfileManager from "../components/ProfileManager";

function StudentAssignments({ courseId, onSubmit }) {
  const [items, setItems] = useState([]);
  useEffect(()=>{ api.get(`/courses/${courseId}/assignments`).then(r=>setItems(r.data)); }, [courseId]);
  return (
    <div>
      {items.map(a => (
        <div className="quiz" key={a.id}>
          <div className="quiz-q">{a.title}</div>
          <div className="item-sub">Due: {a.due_at || 'N/A'}</div>
          <button className="btn mt" onClick={()=>onSubmit(a)}>Submit</button>
        </div>
      ))}
    </div>
  );
}

function Discussions({ courseId }) {
  const [threads, setThreads] = useState([]);
  const [selectedThread, setSelectedThread] = useState(null);
  const [posts, setPosts] = useState([]);
  const [newThreadTitle, setNewThreadTitle] = useState("");
  const [newThreadBody, setNewThreadBody] = useState("");
  const [newPostBody, setNewPostBody] = useState("");

  useEffect(() => { api.get(`/courses/${courseId}/threads`).then(r => setThreads(r.data)); }, [courseId]);

  const createThread = async () => {
    await api.post(`/courses/${courseId}/threads`, { title: newThreadTitle, body: newThreadBody });
    setNewThreadTitle(""); setNewThreadBody("");
    const r = await api.get(`/courses/${courseId}/threads`); setThreads(r.data);
  };

  const selectThread = async (t) => {
    setSelectedThread(t);
    const r = await api.get(`/threads/${t.id}/posts`);
    setPosts(r.data);
  };

  const addPost = async () => {
    await api.post(`/threads/${selectedThread.id}/posts`, { body: newPostBody });
    setNewPostBody("");
    const r = await api.get(`/threads/${selectedThread.id}/posts`);
    setPosts(r.data);
  };

  return (
    <div>
      {!selectedThread ? (
        <div>
          <div className="row">
            <input placeholder="Thread title" value={newThreadTitle} onChange={(e)=>setNewThreadTitle(e.target.value)} />
            <textarea placeholder="Body" value={newThreadBody} onChange={(e)=>setNewThreadBody(e.target.value)} />
            <button className="btn" onClick={createThread}>Create Thread</button>
          </div>
          <div className="list">
            {threads.map(t => (
              <div key={t.id} className="list-item" onClick={() => selectThread(t)}>
                <div>
                  <div className="item-title">{t.title}</div>
                  <div className="item-sub">by {t.user_id} • {new Date(t.created_at).toLocaleDateString()}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      ) : (
        <div>
          <button className="back" onClick={() => setSelectedThread(null)}>← Back</button>
          <h4>{selectedThread.title}</h4>
          <div className="posts">
            {posts.map(p => (
              <div key={p.id} className="post">
                <div className="post-body">{p.body}</div>
                <div className="item-sub">by {p.user_id} • {new Date(p.created_at).toLocaleDateString()}</div>
              </div>
            ))}
          </div>
          <div className="row">
            <textarea placeholder="Add reply" value={newPostBody} onChange={(e)=>setNewPostBody(e.target.value)} />
            <button className="btn" onClick={addPost}>Reply</button>
          </div>
        </div>
      )}
    </div>
  );
}

function StudentDashboard({ me }) {
  const [activeTab, setActiveTab] = useState("dashboard");
  const [courses, setCourses] = useState([]);
  const [selected, setSelected] = useState(null);
  const [chat, setChat] = useState([]);
  const [chatInput, setChatInput] = useState("");
  const [sending, setSending] = useState(false);
  const [analytics, setAnalytics] = useState(null);
  const [progress, setProgress] = useState(null);
  const [recommendations, setRecommendations] = useState([]);
  const [notifications, setNotifications] = useState([]);
  const [mySubmissions, setMySubmissions] = useState([]);
  const [learningPath, setLearningPath] = useState(null);
  const [searchTerm, setSearchTerm] = useState("");
  const [filterDifficulty, setFilterDifficulty] = useState("all");
  const sessionId = useSessionId(selected?.id);

  const refresh = () => api.get(`/courses`).then(r => setCourses(r.data));
  useEffect(()=>{ refresh(); },[]);
  useEffect(()=>{ api.get(`/analytics/student`).then(r=>setAnalytics(r.data)).catch(()=>{/* ignore */}); },[]);
  useEffect(()=>{ api.get(`/courses/recommendations`).then(r=>setRecommendations(r.data)).catch(()=>{setRecommendations([])}); },[]);
  useEffect(()=>{ api.get(`/notifications`).then(r=>setNotifications(r.data)).catch(()=>{setNotifications([])}); },[]);
  useEffect(()=>{ api.get(`/my_submissions`).then(r=>setMySubmissions(r.data)).catch(()=>{setMySubmissions([])}); },[]);
  useEffect(()=>{ api.get(`/courses/learning_path`).then(r=>setLearningPath(r.data)).catch(()=>{setLearningPath(null)}); },[me]);

  const enroll = async (c) => { await api.post(`/courses/${c.id}/enroll`); refresh(); };
  const open = async (c) => {
    setSelected(c);
    // For the new comprehensive course viewer, we don't need to load chat and progress here
    // as the CourseContentViewer component will handle it
  };
  const send = async () => {
    if (!chatInput.trim() || !selected) return;
    const msg = { id: crypto.randomUUID(), role: "user", message: chatInput, created_at: new Date().toISOString() };
    setChat((c) => [...c, msg]); setChatInput(""); setSending(true);
    try {
      const res = await api.post(`/ai/tutor`, { course_id: selected.id, session_id: sessionId, message: msg.message });
      setChat((c) => [...c, { id: crypto.randomUUID(), role: "assistant", message: res.data.reply, created_at: new Date().toISOString() }]);
    } catch (err) {
      // Fallback to regular chat if tutor fails
      try {
        const res = await api.post(`/ai/chat`, { course_id: selected.id, session_id: sessionId, message: msg.message });
        setChat((c) => [...c, { id: crypto.randomUUID(), role: "assistant", message: res.data.reply, created_at: new Date().toISOString() }]);
      } catch (fallbackErr) {
        setChat((c) => [...c, { id: crypto.randomUUID(), role: "assistant", message: "Sorry, I'm having trouble responding right now.", created_at: new Date().toISOString() }]);
      }
    } finally { setSending(false); }
  };

  const submitAssignment = async (a) => {
    const text = prompt("Paste your answer"); if (!text) return;
    // For file upload, we can add a file input, but for simplicity, assume no file for now
    await api.post(`/assignments/${a.id}/submit`, { text_answer: text, file_ids: [] });
    alert("Submitted.");
  };

  const submitQuiz = async (q, courseId) => {
    const selected = document.querySelector(`input[name="q-${q.id}"]:checked`);
    if (!selected) return alert("Select an answer");
    const index = Array.from(document.querySelectorAll(`input[name="q-${q.id}"]`)).indexOf(selected);
    const res = await api.post(`/quizzes/${courseId}/submit`, { question_id: q.id, selected_index: index });
    alert(res.data.correct ? "Correct!" : `Wrong. ${res.data.explanation}`);
  };

  const markComplete = async (lessonId) => {
    const res = await api.post(`/courses/${selected.id}/progress`, { lesson_id: lessonId, completed: true });
    setProgress(res.data);
  };

  const generateCertificate = async () => {
    const res = await api.post(`/courses/${selected.id}/certificate`);
    alert("Certificate generated! " + JSON.stringify(res.data));
  };

  const markRead = async (nid) => {
    await api.post(`/notifications/${nid}/read`);
    setNotifications(n => n.map(nn => nn.id === nid ? {...nn, read: true} : nn));
  };

  const deleteSubmission = async (sid) => {
    if (confirm("Delete submission?")) {
      await api.delete(`/my_submissions/${sid}`);
      setMySubmissions(s => s.filter(sub => sub.id !== sid));
    }
  };

  const enrolledCourses = courses.filter(c => c.enrolled_user_ids?.includes(me?.id));
  const availableCourses = courses.filter(c => !c.enrolled_user_ids?.includes(me?.id) && c.published);

  const filteredCourses = availableCourses.filter(course =>
    course.title.toLowerCase().includes(searchTerm.toLowerCase()) &&
    (filterDifficulty === "all" || course.difficulty === filterDifficulty)
  );

  // If a course is selected, show the enhanced course viewer
  if (selected) {
    return (
      <div className="enhanced-course-layout">
        <div className="course-viewer-section">
          <EnhancedCourseViewer
            course={selected}
            onProgressUpdate={(lessonId, completed) => {
              // Handle progress updates
              console.log('Progress updated:', lessonId, completed);
            }}
            onQuizSubmit={(quizId, isCorrect) => {
              // Handle quiz submissions
              console.log('Quiz submitted:', quizId, isCorrect);
            }}
          />
        </div>
        <div className="chat-section">
          <EnhancedChat
            courseId={selected.id}
            sessionId={sessionId}
            onMessageSent={(message) => {
              // Handle message sent
              console.log('Message sent:', message);
            }}
          />
        </div>
      </div>
    );
  }

  return (
    <div className="student-dashboard">
      <div className="student-header">
        <div className="header-content">
          <h1>Learning Dashboard</h1>
          <p>Welcome back, {me?.name}! Ready to continue your learning journey?</p>
        </div>
        <div className="header-stats">
          <div className="stat-item">
            <span className="stat-number">{enrolledCourses.length}</span>
            <span className="stat-label">Enrolled Courses</span>
          </div>
          <div className="stat-item">
            <span className="stat-number">{analytics?.submissions || 0}</span>
            <span className="stat-label">Submissions</span>
          </div>
          <div className="stat-item">
            <span className="stat-number">∞</span>
            <span className="stat-label">AI Support</span>
          </div>
        </div>
      </div>

      <div className="student-tabs">
        <button
          className={activeTab === "dashboard" ? "active" : ""}
          onClick={() => setActiveTab("dashboard")}
        >
          Dashboard
        </button>
        <button
          className={activeTab === "courses" ? "active" : ""}
          onClick={() => setActiveTab("courses")}
        >
          My Courses
        </button>
        <button
          className={activeTab === "explore" ? "active" : ""}
          onClick={() => setActiveTab("explore")}
        >
          Explore
        </button>
        <button
          className={activeTab === "progress" ? "active" : ""}
          onClick={() => setActiveTab("progress")}
        >
          Progress
        </button>
        <button
          className={activeTab === "notifications" ? "active" : ""}
          onClick={() => setActiveTab("notifications")}
        >
          Notifications
        </button>
        <button
          className={activeTab === "profile" ? "active" : ""}
          onClick={() => setActiveTab("profile")}
        >
          Profile
        </button>
      </div>

      <div className="student-content">
        {activeTab === "dashboard" && (
          <div className="dashboard-section">
            <div className="welcome-section">
              <h2>Continue Learning</h2>
              <div className="enrolled-courses">
                {enrolledCourses.slice(0, 3).map(course => {
                  const courseProgress = analytics?.course_progress?.find(cp => cp.course_id === course.id);
                  const progressPercent = courseProgress?.overall_progress || 0;

                  return (
                    <div key={course.id} className="course-card enrolled" onClick={() => open(course)}>
                      <div className="course-image">📚</div>
                      <h3>{course.title}</h3>
                      <p>{course.lessons?.length || 0} lessons • {course.difficulty}</p>
                      <div className="progress-bar">
                        <div className="progress-fill" style={{width: `${progressPercent}%`}}></div>
                      </div>
                      <span className="continue-btn">Continue Learning</span>
                    </div>
                  );
                })}
                {enrolledCourses.length === 0 && (
                  <div className="empty-state">
                    <h3>No courses yet</h3>
                    <p>Start your learning journey by exploring available courses!</p>
                    <button className="btn primary" onClick={() => setActiveTab("explore")}>
                      Explore Courses
                    </button>
                  </div>
                )}
              </div>
            </div>

            <div className="quick-stats">
              <div className="stat-card">
                <h3>Learning Streak</h3>
                <div className="streak-number">🔥 {analytics?.learning_streak || 0} days</div>
                <p>Keep it up!</p>
              </div>
              <div className="stat-card">
                <h3>Certificates Earned</h3>
                <div className="cert-number">🎓 {analytics?.certificates_earned || 0}</div>
                <p>This month</p>
              </div>
              <div className="stat-card">
                <h3>AI Interactions</h3>
                <div className="ai-number">🤖 {analytics?.ai_interactions || 0}</div>
                <p>This week</p>
              </div>
            </div>

            {learningPath && (
              <div className="learning-path-section">
                <h3>Your AI Learning Path</h3>
                <div className="path-stats">
                  <div className="path-stat">
                    <span className="stat-value">{learningPath.current_performance?.completed_courses || 0}</span>
                    <span className="stat-label">Completed Courses</span>
                  </div>
                  <div className="path-stat">
                    <span className="stat-value">{learningPath.current_performance?.average_grade || 0}%</span>
                    <span className="stat-label">Average Grade</span>
                  </div>
                  <div className="path-stat">
                    <span className="stat-value">{learningPath.current_performance?.active_courses || 0}</span>
                    <span className="stat-label">Active Courses</span>
                  </div>
                </div>

                {learningPath.recommendations?.length > 0 && (
                  <div className="recommendations">
                    <h4>Recommended Next Steps</h4>
                    <div className="recommendation-list">
                      {learningPath.recommendations.slice(0, 3).map(rec => (
                        <div key={rec.course_id} className="recommendation-item">
                          <div className="rec-content">
                            <h5>{rec.title}</h5>
                            <p>{rec.difficulty} • Match: {rec.score}/10</p>
                            <small>Why: {rec.reasons.join(", ")}</small>
                          </div>
                          <button className="btn small" onClick={() => enroll({id: rec.course_id})}>
                            Enroll
                          </button>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {activeTab === "courses" && (
          <div className="courses-section">
            <div className="section-header">
              <h2>My Enrolled Courses</h2>
            </div>

            <div className="courses-grid">
              {enrolledCourses.map(course => {
                const courseProgress = analytics?.course_progress?.find(cp => cp.course_id === course.id);
                const progressPercent = courseProgress?.overall_progress || 0;

                return (
                  <div key={course.id} className="course-card enrolled" onClick={() => open(course)}>
                    <div className="course-image">📚</div>
                    <h3>{course.title}</h3>
                    <p>{course.audience} • {course.difficulty}</p>
                    <p>{course.lessons?.length || 0} lessons</p>
                    <div className="course-progress">
                      <div className="progress-bar">
                        <div className="progress-fill" style={{width: `${progressPercent}%`}}></div>
                      </div>
                      <span className="progress-text">{progressPercent}% Complete</span>
                    </div>
                    <button className="btn primary">Continue Learning</button>
                  </div>
                );
              })}

              {enrolledCourses.length === 0 && (
                <div className="empty-state">
                  <h3>No enrolled courses</h3>
                  <p>Browse available courses to start learning!</p>
                  <button className="btn primary" onClick={() => setActiveTab("explore")}>
                    Browse Courses
                  </button>
                </div>
              )}
            </div>
          </div>
        )}

        {activeTab === "explore" && (
          <div className="explore-section">
            <div className="section-header">
              <h2>Explore Courses</h2>
              <div className="filters">
                <input
                  type="text"
                  placeholder="Search courses..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="search-input"
                />
                <select
                  value={filterDifficulty}
                  onChange={(e) => setFilterDifficulty(e.target.value)}
                >
                  <option value="all">All Levels</option>
                  <option value="beginner">Beginner</option>
                  <option value="intermediate">Intermediate</option>
                  <option value="advanced">Advanced</option>
                </select>
              </div>
            </div>

            <div className="courses-grid">
              {filteredCourses.map(course => (
                <div key={course.id} className="course-card">
                  <div className="course-image">🎓</div>
                  <h3>{course.title}</h3>
                  <p>{course.audience} • {course.difficulty}</p>
                  <p>{course.lessons?.length || 0} lessons • 👥 {course.enrolled_user_ids?.length || 0} students</p>
                  <div className="course-actions">
                    <button className="btn light small" onClick={() => {/* Preview course */}}>
                      Preview
                    </button>
                    <button className="btn primary small" onClick={() => enroll(course)}>
                      Enroll Now
                    </button>
                  </div>
                </div>
              ))}

              {filteredCourses.length === 0 && (
                <div className="empty-state">
                  <h3>No courses found</h3>
                  <p>Try adjusting your search or filters</p>
                </div>
              )}
            </div>
          </div>
        )}

        {activeTab === "progress" && (
          <div className="progress-section">
            <h2>My Learning Progress</h2>

            <div className="progress-overview">
              <div className="overview-card">
                <h3>Overall Progress</h3>
                <div className="progress-circle">
                  <div className="circle-text">{analytics?.overall_progress || 0}%</div>
                </div>
                <p>Across all enrolled courses</p>
              </div>

              <div className="overview-card">
                <h3>Completed Lessons</h3>
                <div className="stat-large">{analytics?.completed_lessons || 0}</div>
                <p>Out of {analytics?.total_lessons || 0} total lessons</p>
              </div>

              <div className="overview-card">
                <h3>Average Grade</h3>
                <div className="stat-large">{analytics?.average_grade || 0}%</div>
                <p>On submitted assignments</p>
              </div>
            </div>

            <div className="detailed-progress">
              <h3>Course Progress</h3>
              {enrolledCourses.map(course => {
                // Get progress for this course
                const courseProgress = analytics?.course_progress?.find(cp => cp.course_id === course.id);
                const progressPercent = courseProgress?.overall_progress || 0;
                const completedLessons = courseProgress?.lessons_progress?.filter(lp => lp.completed).length || 0;
                const totalLessons = course.lessons?.length || 0;

                return (
                  <div key={course.id} className="course-progress-item">
                    <div className="course-info">
                      <h4>{course.title}</h4>
                      <p>{totalLessons} lessons</p>
                    </div>
                    <div className="progress-details">
                      <div className="progress-bar">
                        <div className="progress-fill" style={{width: `${progressPercent}%`}}></div>
                      </div>
                      <span>{completedLessons}/{totalLessons} lessons completed</span>
                    </div>
                    <button className="btn small" onClick={() => open(course)}>
                      Continue
                    </button>
                  </div>
                );
              })}
            </div>

            {mySubmissions.length > 0 && (
              <div className="submissions-section">
                <h3>Recent Submissions</h3>
                <div className="submissions-list">
                  {mySubmissions.slice(0, 5).map(submission => (
                    <div key={submission.id} className="submission-item">
                      <div className="submission-info">
                        <h4>{submission.assignment_title}</h4>
                        <p>{submission.course_title}</p>
                        <small>{new Date(submission.created_at).toLocaleDateString()}</small>
                      </div>
                      {submission.ai_grade && (
                        <div className="grade-badge">
                          {submission.ai_grade.score}/100
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {activeTab === "notifications" && (
          <div className="notifications-section">
            <h2>Notifications</h2>

            {notifications.length === 0 ? (
              <div className="empty-state">
                <h3>No notifications</h3>
                <p>You're all caught up!</p>
              </div>
            ) : (
              <div className="notifications-list">
                {notifications.map(notification => (
                  <div
                    key={notification.id}
                    className={`notification-item ${notification.read ? 'read' : 'unread'}`}
                  >
                    <div className="notification-content">
                      <h4>{notification.title}</h4>
                      <p>{notification.message}</p>
                      <small>{new Date(notification.created_at).toLocaleDateString()}</small>
                    </div>
                    {!notification.read && (
                      <button
                        className="btn small"
                        onClick={() => markRead(notification.id)}
                      >
                        Mark Read
                      </button>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {activeTab === "profile" && (
          <ProfileManager user={me} onProfileUpdate={() => {
            // Refresh user data if needed
            window.location.reload();
          }} />
        )}
      </div>

      <style dangerouslySetInnerHTML={{
        __html: `
        .student-dashboard {
          min-height: 100vh;
          background: #f8f9fa;
        }

        .student-header {
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          color: white;
          padding: 2rem;
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
        }

        .header-content h1 {
          margin: 0 0 0.5rem 0;
          font-size: 2.5rem;
        }

        .header-content p {
          margin: 0;
          opacity: 0.9;
          font-size: 1.1rem;
        }

        .header-stats {
          display: flex;
          gap: 2rem;
        }

        .stat-item {
          text-align: center;
        }

        .stat-number {
          display: block;
          font-size: 2rem;
          font-weight: bold;
        }

        .stat-label {
          color: rgba(255,255,255,0.8);
          font-size: 0.9rem;
        }

        .student-tabs {
          background: white;
          display: flex;
          border-bottom: 1px solid #e9ecef;
          overflow-x: auto;
        }

        .student-tabs button {
          padding: 1rem 2rem;
          border: none;
          background: none;
          color: #6c757d;
          cursor: pointer;
          border-bottom: 3px solid transparent;
          transition: all 0.3s;
          white-space: nowrap;
        }

        .student-tabs button.active {
          color: #667eea;
          border-bottom-color: #667eea;
        }

        .student-content {
          padding: 2rem;
        }

        .dashboard-section {
          max-width: 1200px;
          margin: 0 auto;
        }

        .welcome-section h2 {
          margin-bottom: 1.5rem;
          color: #2c3e50;
        }

        .enrolled-courses {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
          gap: 2rem;
          margin-bottom: 3rem;
        }

        .course-card {
          background: white;
          border-radius: 12px;
          padding: 2rem;
          box-shadow: 0 4px 6px rgba(0,0,0,0.1);
          cursor: pointer;
          transition: transform 0.3s, box-shadow 0.3s;
        }

        .course-card:hover {
          transform: translateY(-5px);
          box-shadow: 0 8px 15px rgba(0,0,0,0.2);
        }

        .course-image {
          font-size: 3rem;
          margin-bottom: 1rem;
        }

        .course-card h3 {
          margin: 0 0 0.5rem 0;
          color: #2c3e50;
        }

        .course-card p {
          margin: 0.5rem 0;
          color: #6c757d;
        }

        .progress-bar {
          width: 100%;
          height: 8px;
          background: #e9ecef;
          border-radius: 4px;
          margin: 1rem 0;
          overflow: hidden;
        }

        .progress-fill {
          height: 100%;
          background: linear-gradient(90deg, #667eea, #764ba2);
          border-radius: 4px;
          transition: width 0.3s;
        }

        .continue-btn {
          color: #667eea;
          font-weight: 500;
          font-size: 0.9rem;
        }

        .empty-state {
          text-align: center;
          padding: 3rem;
          background: white;
          border-radius: 12px;
          box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }

        .empty-state h3 {
          margin: 0 0 1rem 0;
          color: #6c757d;
        }

        .empty-state p {
          margin: 0 0 2rem 0;
          color: #6c757d;
        }

        .quick-stats {
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
        }

        .streak-number, .cert-number, .ai-number {
          font-size: 2.5rem;
          margin-bottom: 0.5rem;
        }

        .learning-path-section {
          background: white;
          padding: 2rem;
          border-radius: 12px;
          box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }

        .path-stats {
          display: flex;
          justify-content: space-around;
          margin-bottom: 2rem;
        }

        .path-stat {
          text-align: center;
        }

        .stat-value {
          display: block;
          font-size: 2rem;
          font-weight: bold;
          color: #667eea;
        }

        .stat-label {
          color: #6c757d;
          font-size: 0.9rem;
        }

        .recommendations h4 {
          margin-bottom: 1rem;
          color: #2c3e50;
        }

        .recommendation-list {
          display: grid;
          gap: 1rem;
        }

        .recommendation-item {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 1rem;
          background: #f8f9fa;
          border-radius: 8px;
        }

        .rec-content h5 {
          margin: 0 0 0.5rem 0;
          color: #2c3e50;
        }

        .rec-content p {
          margin: 0.25rem 0;
          color: #6c757d;
          font-size: 0.9rem;
        }

        .courses-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
          gap: 2rem;
        }

        .section-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 2rem;
        }

        .filters {
          display: flex;
          gap: 1rem;
        }

        .search-input {
          padding: 0.5rem 1rem;
          border: 1px solid #ddd;
          border-radius: 6px;
          width: 250px;
        }

        .filters select {
          padding: 0.5rem 1rem;
          border: 1px solid #ddd;
          border-radius: 6px;
        }

        .course-progress-item {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 1.5rem;
          background: white;
          border-radius: 8px;
          margin-bottom: 1rem;
          box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }

        .course-info h4 {
          margin: 0 0 0.5rem 0;
          color: #2c3e50;
        }

        .progress-details {
          flex: 1;
          margin: 0 2rem;
        }

        .progress-text {
          font-size: 0.9rem;
          color: #6c757d;
          margin-top: 0.5rem;
        }

        .notifications-list {
          display: grid;
          gap: 1rem;
        }

        .notification-item {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 1.5rem;
          background: white;
          border-radius: 8px;
          box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }

        .notification-item.unread {
          border-left: 4px solid #667eea;
        }

        .notification-content h4 {
          margin: 0 0 0.5rem 0;
          color: #2c3e50;
        }

        .notification-content p {
          margin: 0.25rem 0;
          color: #6c757d;
        }

        .course-modal-overlay {
          position: fixed;
          top: 0;
          left: 0;
          right: 0;
          bottom: 0;
          background: rgba(0,0,0,0.8);
          display: flex;
          align-items: center;
          justify-content: center;
          z-index: 1000;
        }

        .course-modal {
          background: white;
          width: 90vw;
          height: 90vh;
          border-radius: 12px;
          overflow: hidden;
          display: flex;
          flex-direction: column;
        }

        .course-header {
          padding: 2rem;
          border-bottom: 1px solid #eee;
          display: flex;
          align-items: center;
          gap: 2rem;
        }

        .back-btn {
          background: #f8f9fa;
          border: none;
          padding: 0.75rem 1.5rem;
          border-radius: 6px;
          cursor: pointer;
          color: #6c757d;
        }

        .course-header h2 {
          margin: 0;
          color: #2c3e50;
          flex: 1;
        }

        .course-progress-header {
          text-align: right;
        }

        .course-content {
          flex: 1;
          display: flex;
          overflow: hidden;
        }

        .course-main {
          flex: 1;
          padding: 2rem;
          overflow-y: auto;
        }

        .lessons-section {
          margin-bottom: 3rem;
        }

        .lesson-item {
          padding: 1.5rem;
          border: 1px solid #eee;
          border-radius: 8px;
          margin-bottom: 1rem;
        }

        .lesson-item.completed {
          background: #f8fff8;
          border-color: #28a745;
        }

        .lesson-header {
          display: flex;
          align-items: center;
          gap: 1rem;
          margin-bottom: 1rem;
        }

        .lesson-number {
          background: #667eea;
          color: white;
          width: 30px;
          height: 30px;
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          font-weight: bold;
        }

        .lesson-header h4 {
          margin: 0;
          flex: 1;
          color: #2c3e50;
        }

        .completed-badge {
          color: #28a745;
          font-size: 1.2rem;
        }

        .quiz-section, .assignments-section, .discussions-section {
          margin-bottom: 3rem;
        }

        .quiz-item {
          padding: 1.5rem;
          border: 1px solid #eee;
          border-radius: 8px;
          margin-bottom: 1rem;
        }

        .quiz-options {
          margin: 1rem 0;
        }

        .option {
          display: block;
          margin-bottom: 0.5rem;
          padding: 0.5rem;
          border: 1px solid #eee;
          border-radius: 6px;
          cursor: pointer;
        }

        .option:hover {
          background: #f8f9fa;
        }

        .course-sidebar {
          width: 350px;
          border-left: 1px solid #eee;
          padding: 2rem;
          background: #f8f9fa;
          overflow-y: auto;
        }

        .ai-tutor {
          margin-bottom: 2rem;
        }

        .ai-tutor h4 {
          margin: 0 0 1rem 0;
          color: #2c3e50;
        }

        .chat-messages {
          max-height: 300px;
          overflow-y: auto;
          margin-bottom: 1rem;
        }

        .chat-message {
          padding: 0.75rem;
          margin-bottom: 0.5rem;
          border-radius: 6px;
        }

        .chat-message.user {
          background: #667eea;
          color: white;
          margin-left: 2rem;
        }

        .chat-message.assistant {
          background: white;
          border: 1px solid #eee;
          margin-right: 2rem;
        }

        .chat-input-group {
          display: flex;
          gap: 0.5rem;
        }

        .chat-input-group input {
          flex: 1;
          padding: 0.75rem;
          border: 1px solid #ddd;
          border-radius: 6px;
        }

        .certificate-section {
          background: linear-gradient(135deg, #667eea, #764ba2);
          color: white;
          padding: 2rem;
          border-radius: 12px;
          text-align: center;
        }

        .certificate-issued {
          background: #d4edda;
          color: #155724;
          padding: 2rem;
          border-radius: 12px;
          text-align: center;
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

        .btn.secondary {
          background: #6c757d;
          color: white;
        }

        .btn.light {
          background: #f8f9fa;
          color: #6c757d;
          border: 1px solid #ddd;
        }

        .btn.small {
          padding: 0.5rem 1rem;
          font-size: 0.9rem;
        }

        .enhanced-course-layout {
          display: grid;
          grid-template-columns: 1fr 400px;
          gap: var(--space-6);
          height: calc(100vh - 80px);
          padding: var(--space-6);
          background: var(--gray-50);
        }

        .course-viewer-section {
          background: white;
          border-radius: var(--radius-xl);
          box-shadow: var(--shadow-lg);
          overflow: hidden;
        }

        .chat-section {
          background: white;
          border-radius: var(--radius-xl);
          box-shadow: var(--shadow-lg);
          overflow: hidden;
          height: fit-content;
          max-height: 100%;
        }

        /* Responsive adjustments */
        @media (max-width: 1200px) {
          .enhanced-course-layout {
            grid-template-columns: 1fr 350px;
            gap: var(--space-4);
          }
        }

        @media (max-width: 1024px) {
          .enhanced-course-layout {
            grid-template-columns: 1fr;
            grid-template-rows: 1fr auto;
            height: auto;
            gap: var(--space-4);
          }

          .chat-section {
            max-height: 500px;
          }
        }

        @media (max-width: 768px) {
          .enhanced-course-layout {
            padding: var(--space-4);
            height: auto;
          }

          .course-viewer-section,
          .chat-section {
            border-radius: var(--radius-lg);
          }
        }
      `}} />
    </div>
  );
}

export default StudentDashboard;