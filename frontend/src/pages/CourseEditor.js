import React, { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import api from "../services/api";
import MediaUpload from "../components/MediaUpload";

function CourseEditor({ me }) {
  const { courseId } = useParams();
  const navigate = useNavigate();
  const [course, setCourse] = useState(null);
  const [activeTab, setActiveTab] = useState("overview");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [selectedLesson, setSelectedLesson] = useState(null);
  const [showLessonModal, setShowLessonModal] = useState(false);
  const [lessonForm, setLessonForm] = useState({
    title: "",
    content: "",
    content_type: "text",
    estimated_time: 30,
    difficulty_level: "intermediate",
    learning_objectives: [],
    tags: []
  });

  useEffect(() => {
    loadCourse();
  }, [courseId]);

  const loadCourse = async () => {
    try {
      const response = await api.get(`/courses/${courseId}`);
      setCourse(response.data);
    } catch (error) {
      console.error("Error loading course:", error);
      alert("Error loading course");
    } finally {
      setLoading(false);
    }
  };

  const saveCourse = async (updates) => {
    setSaving(true);
    try {
      await api.put(`/courses/${courseId}`, updates);
      setCourse(prev => ({ ...prev, ...updates }));
      alert("Course updated successfully!");
    } catch (error) {
      console.error("Error saving course:", error);
      alert("Error saving course");
    } finally {
      setSaving(false);
    }
  };

  const createLesson = async () => {
    try {
      await api.post(`/courses/${courseId}/lessons`, lessonForm);
      setShowLessonModal(false);
      setLessonForm({
        title: "",
        content: "",
        content_type: "text",
        estimated_time: 30,
        difficulty_level: "intermediate",
        learning_objectives: [],
        tags: []
      });
      loadCourse();
      alert("Lesson created successfully!");
    } catch (error) {
      console.error("Error creating lesson:", error);
      alert("Error creating lesson");
    }
  };

  const updateLesson = async (lessonId, updates) => {
    try {
      await api.put(`/courses/${courseId}/lessons/${lessonId}`, updates);
      loadCourse();
      alert("Lesson updated successfully!");
    } catch (error) {
      console.error("Error updating lesson:", error);
      alert("Error updating lesson");
    }
  };

  const deleteLesson = async (lessonId) => {
    if (!confirm("Are you sure you want to delete this lesson?")) return;
    try {
      await api.delete(`/courses/${courseId}/lessons/${lessonId}`);
      loadCourse();
      alert("Lesson deleted successfully!");
    } catch (error) {
      console.error("Error deleting lesson:", error);
      alert("Error deleting lesson");
    }
  };

  const generateAIContent = async (contentType, prompt) => {
    try {
      const response = await api.post(`/courses/ai/generate_content`, {
        content_type: contentType,
        topic: prompt,
        target_audience: course.audience,
        difficulty_level: course.difficulty
      });
      return response.data.generated_content;
    } catch (error) {
      console.error("Error generating AI content:", error);
      alert("Error generating AI content");
      return null;
    }
  };

  if (loading) {
    return (
      <div className="loading-container">
        <div className="loading-spinner"></div>
        <p>Loading course editor...</p>
      </div>
    );
  }

  if (!course) {
    return (
      <div className="error-container">
        <h2>Course not found</h2>
        <button onClick={() => navigate("/instructor")}>Back to Dashboard</button>
      </div>
    );
  }

  return (
    <div className="course-editor">
      <div className="editor-header">
        <div className="header-content">
          <button className="back-btn" onClick={() => navigate("/instructor")}>
            ← Back to Dashboard
          </button>
          <div className="course-info">
            <h1>{course.title}</h1>
            <div className="course-meta">
              <span>{course.audience}</span>
              <span>•</span>
              <span>{course.difficulty}</span>
              <span>•</span>
              <span>{course.lessons?.length || 0} lessons</span>
              <span>•</span>
              <span>{course.enrolled_user_ids?.length || 0} students</span>
            </div>
          </div>
        </div>
        <div className="header-actions">
          <button
            className={`publish-btn ${course.published ? 'published' : 'draft'}`}
            onClick={() => saveCourse({ published: !course.published })}
            disabled={saving}
          >
            {course.published ? 'Unpublish' : 'Publish'} Course
          </button>
        </div>
      </div>

      <div className="editor-tabs">
        <button
          className={activeTab === "overview" ? "active" : ""}
          onClick={() => setActiveTab("overview")}
        >
          Overview
        </button>
        <button
          className={activeTab === "lessons" ? "active" : ""}
          onClick={() => setActiveTab("lessons")}
        >
          Lessons
        </button>
        <button
          className={activeTab === "content" ? "active" : ""}
          onClick={() => setActiveTab("content")}
        >
          Content
        </button>
        <button
          className={activeTab === "media" ? "active" : ""}
          onClick={() => setActiveTab("media")}
        >
          Media
        </button>
        <button
          className={activeTab === "settings" ? "active" : ""}
          onClick={() => setActiveTab("settings")}
        >
          Settings
        </button>
      </div>

      <div className="editor-content">
        {activeTab === "overview" && (
          <div className="overview-section">
            <div className="overview-grid">
              <div className="overview-card">
                <h3>Course Statistics</h3>
                <div className="stats-grid">
                  <div className="stat-item">
                    <span className="stat-value">{course.enrolled_user_ids?.length || 0}</span>
                    <span className="stat-label">Enrolled Students</span>
                  </div>
                  <div className="stat-item">
                    <span className="stat-value">{course.lessons?.length || 0}</span>
                    <span className="stat-label">Total Lessons</span>
                  </div>
                  <div className="stat-item">
                    <span className="stat-value">{course.published ? 'Published' : 'Draft'}</span>
                    <span className="stat-label">Status</span>
                  </div>
                </div>
              </div>

              <div className="overview-card">
                <h3>Quick Actions</h3>
                <div className="actions-list">
                  <button
                    className="action-btn"
                    onClick={() => setShowLessonModal(true)}
                  >
                    + Add New Lesson
                  </button>
                  <button
                    className="action-btn"
                    onClick={() => setActiveTab("content")}
                  >
                    📝 Edit Content
                  </button>
                  <button
                    className="action-btn"
                    onClick={() => navigate(`/instructor/course/${courseId}/analytics`)}
                  >
                    📊 View Analytics
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === "lessons" && (
          <div className="lessons-section">
            <div className="section-header">
              <h2>Course Lessons</h2>
              <button
                className="btn primary"
                onClick={() => setShowLessonModal(true)}
              >
                + Add Lesson
              </button>
            </div>

            <div className="lessons-list">
              {course.lessons?.map((lesson, index) => (
                <div key={lesson.id} className="lesson-item">
                  <div className="lesson-header">
                    <div className="lesson-info">
                      <h4>{lesson.title}</h4>
                      <div className="lesson-meta">
                        <span>Lesson {index + 1}</span>
                        <span>•</span>
                        <span>{lesson.estimated_time || 30} min</span>
                        <span>•</span>
                        <span>{lesson.difficulty_level || 'intermediate'}</span>
                      </div>
                    </div>
                    <div className="lesson-actions">
                      <button
                        className="btn small"
                        onClick={() => {
                          setSelectedLesson(lesson);
                          setLessonForm({
                            title: lesson.title,
                            content: lesson.content,
                            content_type: lesson.content_type || "text",
                            estimated_time: lesson.estimated_time || 30,
                            difficulty_level: lesson.difficulty_level || "intermediate",
                            learning_objectives: lesson.learning_objectives || [],
                            tags: lesson.tags || []
                          });
                          setShowLessonModal(true);
                        }}
                      >
                        Edit
                      </button>
                      <button
                        className="btn small danger"
                        onClick={() => deleteLesson(lesson.id)}
                      >
                        Delete
                      </button>
                    </div>
                  </div>
                  <div className="lesson-preview">
                    {lesson.content?.substring(0, 200)}...
                  </div>
                </div>
              ))}

              {(!course.lessons || course.lessons.length === 0) && (
                <div className="empty-state">
                  <h3>No lessons yet</h3>
                  <p>Start building your course by adding your first lesson</p>
                  <button
                    className="btn primary"
                    onClick={() => setShowLessonModal(true)}
                  >
                    Create First Lesson
                  </button>
                </div>
              )}
            </div>
          </div>
        )}

        {activeTab === "content" && (
          <div className="content-section">
            <div className="content-editor">
              <div className="editor-toolbar">
                <h3>Course Content Editor</h3>
                <div className="toolbar-actions">
                  <button
                    className="btn small"
                    onClick={async () => {
                      const aiContent = await generateAIContent("lesson", "Generate an introduction lesson for " + course.title);
                      if (aiContent) {
                        setLessonForm(prev => ({ ...prev, content: aiContent }));
                      }
                    }}
                  >
                    🤖 Generate with AI
                  </button>
                </div>
              </div>

              <div className="content-form">
                <div className="form-group">
                  <label>Course Description</label>
                  <textarea
                    value={course.description || ""}
                    onChange={(e) => setCourse(prev => ({ ...prev, description: e.target.value }))}
                    rows={6}
                    placeholder="Describe what students will learn in this course..."
                  />
                </div>

                <div className="form-actions">
                  <button
                    className="btn primary"
                    onClick={() => saveCourse({ description: course.description })}
                    disabled={saving}
                  >
                    {saving ? "Saving..." : "Save Description"}
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === "media" && (
          <div className="media-section">
            <div className="section-header">
              <h2>Course Media Library</h2>
              <p>Upload and manage media files for your course content</p>
            </div>

            <div className="media-upload-container">
              <MediaUpload
                courseId={courseId}
                onMediaUploaded={(mediaData) => {
                  console.log('Media uploaded:', mediaData);
                  // Here you could update the course state with media information
                  // For now, we'll just log it
                }}
              />
            </div>

            <div className="media-info">
              <div className="info-card">
                <h4>📸 Image Files</h4>
                <p>JPG, PNG, GIF, WebP - Max 10MB each</p>
                <p>Perfect for course thumbnails, diagrams, and illustrations</p>
              </div>

              <div className="info-card">
                <h4>🎥 Video Files</h4>
                <p>MP4, WebM, OGG - Max 50MB each</p>
                <p>Upload lecture videos, tutorials, and demonstrations</p>
              </div>

              <div className="info-card">
                <h4>🎵 Audio Files</h4>
                <p>MP3, WAV, OGG - Max 20MB each</p>
                <p>Add podcasts, audio lectures, and sound effects</p>
              </div>

              <div className="info-card">
                <h4>📄 Documents</h4>
                <p>PDF, DOC, DOCX - Max 15MB each</p>
                <p>Share handouts, worksheets, and reference materials</p>
              </div>
            </div>
          </div>
        )}

        {activeTab === "settings" && (
          <div className="settings-section">
            <div className="settings-grid">
              <div className="settings-card">
                <h3>Basic Information</h3>
                <div className="form-group">
                  <label>Course Title</label>
                  <input
                    type="text"
                    value={course.title}
                    onChange={(e) => setCourse(prev => ({ ...prev, title: e.target.value }))}
                  />
                </div>

                <div className="form-row">
                  <div className="form-group">
                    <label>Audience</label>
                    <select
                      value={course.audience}
                      onChange={(e) => setCourse(prev => ({ ...prev, audience: e.target.value }))}
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
                      value={course.difficulty}
                      onChange={(e) => setCourse(prev => ({ ...prev, difficulty: e.target.value }))}
                    >
                      <option value="beginner">Beginner</option>
                      <option value="intermediate">Intermediate</option>
                      <option value="advanced">Advanced</option>
                    </select>
                  </div>
                </div>

                <button
                  className="btn primary"
                  onClick={() => saveCourse({
                    title: course.title,
                    audience: course.audience,
                    difficulty: course.difficulty
                  })}
                  disabled={saving}
                >
                  {saving ? "Saving..." : "Save Changes"}
                </button>
              </div>

              <div className="settings-card">
                <h3>Course Tags</h3>
                <div className="tags-editor">
                  <input
                    type="text"
                    placeholder="Add tags (press Enter)"
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && e.target.value.trim()) {
                        const newTag = e.target.value.trim();
                        setCourse(prev => ({
                          ...prev,
                          tags: [...(prev.tags || []), newTag]
                        }));
                        e.target.value = '';
                      }
                    }}
                  />
                  <div className="tags-list">
                    {(course.tags || []).map((tag, index) => (
                      <span key={index} className="tag">
                        {tag}
                        <button
                          onClick={() => {
                            setCourse(prev => ({
                              ...prev,
                              tags: prev.tags.filter((_, i) => i !== index)
                            }));
                          }}
                        >
                          ×
                        </button>
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {showLessonModal && (
        <div className="modal-overlay">
          <div className="modal">
            <h3>{selectedLesson ? 'Edit Lesson' : 'Create New Lesson'}</h3>

            <div className="lesson-form">
              <div className="form-group">
                <label>Lesson Title</label>
                <input
                  type="text"
                  value={lessonForm.title}
                  onChange={(e) => setLessonForm(prev => ({ ...prev, title: e.target.value }))}
                  placeholder="Enter lesson title"
                />
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label>Content Type</label>
                  <select
                    value={lessonForm.content_type}
                    onChange={(e) => setLessonForm(prev => ({ ...prev, content_type: e.target.value }))}
                  >
                    <option value="text">Text</option>
                    <option value="video">Video</option>
                    <option value="interactive">Interactive</option>
                    <option value="quiz">Quiz</option>
                  </select>
                </div>

                <div className="form-group">
                  <label>Estimated Time (minutes)</label>
                  <input
                    type="number"
                    value={lessonForm.estimated_time}
                    onChange={(e) => setLessonForm(prev => ({ ...prev, estimated_time: parseInt(e.target.value) }))}
                    min="5"
                    max="180"
                  />
                </div>
              </div>

              <div className="form-group">
                <label>Difficulty Level</label>
                <select
                  value={lessonForm.difficulty_level}
                  onChange={(e) => setLessonForm(prev => ({ ...prev, difficulty_level: e.target.value }))}
                >
                  <option value="beginner">Beginner</option>
                  <option value="intermediate">Intermediate</option>
                  <option value="advanced">Advanced</option>
                </select>
              </div>

              <div className="form-group">
                <label>Lesson Content</label>
                <textarea
                  value={lessonForm.content}
                  onChange={(e) => setLessonForm(prev => ({ ...prev, content: e.target.value }))}
                  rows={10}
                  placeholder="Enter lesson content..."
                />
              </div>

              <div className="form-group">
                <label>Learning Objectives</label>
                <textarea
                  value={lessonForm.learning_objectives.join('\n')}
                  onChange={(e) => setLessonForm(prev => ({
                    ...prev,
                    learning_objectives: e.target.value.split('\n').filter(obj => obj.trim())
                  }))}
                  rows={4}
                  placeholder="Enter learning objectives (one per line)"
                />
              </div>
            </div>

            <div className="modal-actions">
              <button
                className="btn secondary"
                onClick={() => {
                  setShowLessonModal(false);
                  setSelectedLesson(null);
                  setLessonForm({
                    title: "",
                    content: "",
                    content_type: "text",
                    estimated_time: 30,
                    difficulty_level: "intermediate",
                    learning_objectives: [],
                    tags: []
                  });
                }}
              >
                Cancel
              </button>
              <button
                className="btn primary"
                onClick={() => {
                  if (selectedLesson) {
                    updateLesson(selectedLesson.id, lessonForm);
                  } else {
                    createLesson();
                  }
                }}
              >
                {selectedLesson ? 'Update Lesson' : 'Create Lesson'}
              </button>
            </div>
          </div>
        </div>
      )}

      <style>{`
        .course-editor {
          min-height: 100vh;
          background: #f8f9fa;
        }

        .editor-header {
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
        }

        .publish-btn {
          padding: 0.75rem 1.5rem;
          border: none;
          border-radius: 6px;
          cursor: pointer;
          font-weight: 500;
          transition: all 0.3s;
        }

        .publish-btn.published {
          background: #28a745;
          color: white;
        }

        .publish-btn.draft {
          background: #ffc107;
          color: #212529;
        }

        .editor-tabs {
          background: white;
          display: flex;
          border-bottom: 1px solid #e9ecef;
        }

        .editor-tabs button {
          padding: 1rem 2rem;
          border: none;
          background: none;
          color: #6c757d;
          cursor: pointer;
          border-bottom: 3px solid transparent;
          transition: all 0.3s;
        }

        .editor-tabs button.active {
          color: #007bff;
          border-bottom-color: #007bff;
        }

        .editor-content {
          padding: 2rem;
        }

        .overview-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
          gap: 2rem;
        }

        .overview-card {
          background: white;
          padding: 2rem;
          border-radius: 12px;
          box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }

        .stats-grid {
          display: grid;
          grid-template-columns: repeat(3, 1fr);
          gap: 1rem;
        }

        .stat-item {
          text-align: center;
        }

        .stat-value {
          display: block;
          font-size: 2rem;
          font-weight: bold;
          color: #007bff;
          margin-bottom: 0.5rem;
        }

        .stat-label {
          color: #6c757d;
          font-size: 0.9rem;
        }

        .actions-list {
          display: flex;
          flex-direction: column;
          gap: 1rem;
        }

        .action-btn {
          padding: 1rem;
          background: #f8f9fa;
          border: 1px solid #dee2e6;
          border-radius: 8px;
          cursor: pointer;
          text-align: left;
          transition: all 0.3s;
        }

        .action-btn:hover {
          background: #e9ecef;
          transform: translateY(-2px);
        }

        .lessons-list {
          display: flex;
          flex-direction: column;
          gap: 1rem;
        }

        .lesson-item {
          background: white;
          border-radius: 12px;
          padding: 1.5rem;
          box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }

        .lesson-header {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          margin-bottom: 1rem;
        }

        .lesson-info h4 {
          margin: 0 0 0.5rem 0;
          color: #2c3e50;
        }

        .lesson-meta {
          display: flex;
          gap: 1rem;
          color: #6c757d;
          font-size: 0.9rem;
        }

        .lesson-actions {
          display: flex;
          gap: 0.5rem;
        }

        .lesson-preview {
          color: #6c757d;
          line-height: 1.5;
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

        .content-editor {
          background: white;
          border-radius: 12px;
          padding: 2rem;
          box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }

        .editor-toolbar {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 2rem;
          padding-bottom: 1rem;
          border-bottom: 1px solid #e9ecef;
        }

        .toolbar-actions {
          display: flex;
          gap: 1rem;
        }

        .settings-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
          gap: 2rem;
        }

        .settings-card {
          background: white;
          padding: 2rem;
          border-radius: 12px;
          box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }

        .form-group {
          margin-bottom: 1.5rem;
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

        .form-row {
          display: flex;
          gap: 1rem;
        }

        .form-row .form-group {
          flex: 1;
        }

        .tags-editor {
          display: flex;
          flex-direction: column;
          gap: 1rem;
        }

        .tags-list {
          display: flex;
          flex-wrap: wrap;
          gap: 0.5rem;
        }

        .tag {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          padding: 0.25rem 0.75rem;
          background: #e9ecef;
          border-radius: 20px;
          font-size: 0.9rem;
        }

        .tag button {
          background: none;
          border: none;
          color: #6c757d;
          cursor: pointer;
          font-size: 1.2rem;
          line-height: 1;
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
          border-radius: 12px;
          width: 90%;
          max-width: 800px;
          max-height: 90vh;
          overflow-y: auto;
        }

        .modal h3 {
          margin: 0 0 2rem 0;
          padding: 2rem 2rem 0;
          color: #2c3e50;
        }

        .lesson-form {
          padding: 0 2rem;
        }

        .modal-actions {
          padding: 2rem;
          display: flex;
          gap: 1rem;
          justify-content: flex-end;
          border-top: 1px solid #e9ecef;
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

        .btn.danger {
          background: #dc3545;
          color: white;
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
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          height: 400px;
          gap: 1rem;
        }

        .error-container h2 {
          color: #dc3545;
        }

        .media-section {
          background: white;
          border-radius: 12px;
          padding: 2rem;
          box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }

        .media-section .section-header {
          text-align: center;
          margin-bottom: 2rem;
        }

        .media-section .section-header h2 {
          margin: 0 0 0.5rem 0;
          color: #2c3e50;
          font-size: 1.5rem;
        }

        .media-section .section-header p {
          color: #6c757d;
          margin: 0;
        }

        .media-upload-container {
          margin-bottom: 2rem;
        }

        .media-info {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
          gap: 1.5rem;
          margin-top: 2rem;
        }

        .info-card {
          background: #f8f9fa;
          padding: 1.5rem;
          border-radius: 8px;
          border-left: 4px solid #667eea;
          transition: transform 0.3s;
        }

        .info-card:hover {
          transform: translateY(-2px);
        }

        .info-card h4 {
          margin: 0 0 0.5rem 0;
          color: #2c3e50;
          font-size: 1.1rem;
        }

        .info-card p {
          margin: 0.25rem 0;
          color: #6c757d;
          font-size: 0.9rem;
          line-height: 1.4;
        }
      `}</style>
    </div>
  );
}

export default CourseEditor;