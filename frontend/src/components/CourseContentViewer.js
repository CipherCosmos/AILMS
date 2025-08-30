import React, { useState, useEffect } from "react";
import api from "../services/api";

function CourseContentViewer({ courseId, user }) {
  const [course, setCourse] = useState(null);
  const [progress, setProgress] = useState(null);
  const [currentLesson, setCurrentLesson] = useState(0);
  const [chat, setChat] = useState([]);
  const [chatInput, setChatInput] = useState("");
  const [sending, setSending] = useState(false);
  const [showQuiz, setShowQuiz] = useState(false);
  const [quizAnswers, setQuizAnswers] = useState({});
  const [certificate, setCertificate] = useState(null);

  useEffect(() => {
    loadCourse();
    loadProgress();
  }, [courseId]);

  const loadCourse = async () => {
    try {
      const response = await api.get(`/courses/${courseId}`);
      setCourse(response.data);
    } catch (error) {
      console.error("Error loading course:", error);
    }
  };

  const loadProgress = async () => {
    try {
      const response = await api.get(`/courses/${courseId}/progress`);
      setProgress(response.data);
    } catch (error) {
      console.error("Error loading progress:", error);
    }
  };

  const markLessonComplete = async (lessonId) => {
    try {
      await api.post(`/courses/${courseId}/progress`, {
        lesson_id: lessonId,
        completed: true
      });
      loadProgress();
    } catch (error) {
      console.error("Error updating progress:", error);
    }
  };

  const sendChatMessage = async () => {
    if (!chatInput.trim()) return;

    const userMessage = {
      id: Date.now(),
      role: "user",
      message: chatInput,
      created_at: new Date().toISOString()
    };

    setChat(prev => [...prev, userMessage]);
    setChatInput("");
    setSending(true);

    try {
      const response = await api.post(`/ai/chat`, {
        course_id: courseId,
        session_id: `session_${user.id}_${courseId}`,
        message: userMessage.message
      });

      const aiMessage = {
        id: Date.now() + 1,
        role: "assistant",
        message: response.data.reply,
        created_at: new Date().toISOString()
      };

      setChat(prev => [...prev, aiMessage]);
    } catch (error) {
      console.error("Error sending chat:", error);
    } finally {
      setSending(false);
    }
  };

  const submitQuiz = async () => {
    if (!course?.quiz?.length) return;

    const currentQuiz = course.quiz[0]; // For simplicity, take first quiz
    const selectedAnswer = quizAnswers[currentQuiz.id];

    if (selectedAnswer === undefined) {
      alert("Please select an answer");
      return;
    }

    try {
      const response = await api.post(`/quizzes/${courseId}/submit`, {
        question_id: currentQuiz.id,
        selected_index: selectedAnswer
      });

      alert(response.data.correct ?
        `Correct! ${response.data.explanation}` :
        `Incorrect. ${response.data.explanation}`
      );

      setShowQuiz(false);
      setQuizAnswers({});
    } catch (error) {
      console.error("Error submitting quiz:", error);
    }
  };

  const generateCertificate = async () => {
    try {
      const response = await api.post(`/courses/${courseId}/certificate`);
      setCertificate(response.data);
    } catch (error) {
      console.error("Error generating certificate:", error);
      alert("Error generating certificate. Make sure course is completed.");
    }
  };

  if (!course) {
    return <div className="loading">Loading course...</div>;
  }

  const currentLessonData = course.lessons?.[currentLesson];

  return (
    <div className="course-viewer">
      {/* Header */}
      <div className="course-header">
        <button
          className="back-btn"
          onClick={() => window.history.back()}
        >
          ← Back to Dashboard
        </button>
        <div className="course-info">
          <h1>{course.title}</h1>
          <div className="course-meta">
            <span>{course.audience}</span>
            <span>•</span>
            <span>{course.difficulty}</span>
            {progress && (
              <>
                <span>•</span>
                <span>Progress: {progress.overall_progress?.toFixed(1)}%</span>
              </>
            )}
          </div>
        </div>
      </div>

      <div className="course-content">
        {/* Sidebar - Lesson Navigation */}
        <div className="lesson-sidebar">
          <h3>Course Content</h3>
          <div className="lesson-list">
            {course.lessons?.map((lesson, index) => {
              const lessonProgress = progress?.lessons_progress?.find(
                lp => lp.lesson_id === lesson.id
              );
              return (
                <div
                  key={lesson.id}
                  className={`lesson-item ${lessonProgress?.completed ? 'completed' : ''} ${currentLesson === index ? 'active' : ''}`}
                  onClick={() => setCurrentLesson(index)}
                >
                  <div className="lesson-number">{index + 1}</div>
                  <div className="lesson-title">{lesson.title}</div>
                  {lessonProgress?.completed && <span className="checkmark">✓</span>}
                </div>
              );
            })}
          </div>

          {/* Quiz Section */}
          {course.quiz?.length > 0 && (
            <div className="quiz-section">
              <button
                className="btn primary"
                onClick={() => setShowQuiz(!showQuiz)}
              >
                {showQuiz ? 'Hide Quiz' : 'Take Quiz'}
              </button>
            </div>
          )}

          {/* Certificate Section */}
          {progress?.completed && !progress?.certificate_issued && (
            <div className="certificate-section">
              <button
                className="btn success"
                onClick={generateCertificate}
              >
                Generate Certificate
              </button>
            </div>
          )}

          {certificate && (
            <div className="certificate-display">
              <h4>🎓 Certificate Earned!</h4>
              <p>Course: {certificate.course_title}</p>
              <p>Completed: {new Date(certificate.completion_date).toLocaleDateString()}</p>
            </div>
          )}
        </div>

        {/* Main Content Area */}
        <div className="lesson-content">
          {currentLessonData && (
            <div className="lesson-display">
              <h2>{currentLessonData.title}</h2>
              <div className="lesson-text">
                {currentLessonData.content}
              </div>

              {!progress?.lessons_progress?.find(lp => lp.lesson_id === currentLessonData.id)?.completed && (
                <button
                  className="btn primary"
                  onClick={() => markLessonComplete(currentLessonData.id)}
                >
                  Mark as Complete
                </button>
              )}
            </div>
          )}

          {/* Quiz Display */}
          {showQuiz && course.quiz?.length > 0 && (
            <div className="quiz-display">
              <h3>Course Quiz</h3>
              {course.quiz.map((quiz, index) => (
                <div key={quiz.id} className="quiz-question">
                  <h4>{quiz.question}</h4>
                  <div className="quiz-options">
                    {quiz.options?.map((option, optIndex) => (
                      <label key={optIndex} className="option">
                        <input
                          type="radio"
                          name={`quiz-${quiz.id}`}
                          value={optIndex}
                          checked={quizAnswers[quiz.id] === optIndex}
                          onChange={(e) => setQuizAnswers(prev => ({
                            ...prev,
                            [quiz.id]: parseInt(e.target.value)
                          }))}
                        />
                        {option.text}
                      </label>
                    ))}
                  </div>
                </div>
              ))}
              <button className="btn primary" onClick={submitQuiz}>
                Submit Quiz
              </button>
            </div>
          )}
        </div>

        {/* AI Chat Sidebar */}
        <div className="chat-sidebar">
          <h3>AI Course Assistant</h3>
          <div className="chat-messages">
            {chat.map(message => (
              <div key={message.id} className={`message ${message.role}`}>
                <div className="message-content">{message.message}</div>
              </div>
            ))}
          </div>
          <div className="chat-input">
            <input
              type="text"
              value={chatInput}
              onChange={(e) => setChatInput(e.target.value)}
              placeholder="Ask me anything about this course..."
              onKeyDown={(e) => e.key === "Enter" && !sending && sendChatMessage()}
            />
            <button
              className="btn"
              disabled={sending}
              onClick={sendChatMessage}
            >
              {sending ? "..." : "Ask"}
            </button>
          </div>
        </div>
      </div>

      <style>{`
        .course-viewer {
          min-height: 100vh;
          background: #f8f9fa;
        }

        .course-header {
          background: white;
          padding: 2rem;
          border-bottom: 1px solid #e9ecef;
          display: flex;
          align-items: center;
          gap: 2rem;
        }

        .back-btn {
          background: #6c757d;
          color: white;
          border: none;
          padding: 0.75rem 1.5rem;
          border-radius: 6px;
          cursor: pointer;
          font-weight: 500;
        }

        .course-info h1 {
          margin: 0 0 0.5rem 0;
          font-size: 2rem;
          color: #2c3e50;
        }

        .course-meta {
          display: flex;
          gap: 1rem;
          color: #6c757d;
          font-size: 0.9rem;
        }

        .course-content {
          display: grid;
          grid-template-columns: 300px 1fr 300px;
          min-height: calc(100vh - 140px);
        }

        .lesson-sidebar {
          background: white;
          padding: 2rem;
          border-right: 1px solid #e9ecef;
        }

        .lesson-sidebar h3 {
          margin: 0 0 1.5rem 0;
          color: #2c3e50;
        }

        .lesson-list {
          display: flex;
          flex-direction: column;
          gap: 0.5rem;
        }

        .lesson-item {
          display: flex;
          align-items: center;
          gap: 1rem;
          padding: 1rem;
          border-radius: 8px;
          cursor: pointer;
          transition: all 0.3s;
        }

        .lesson-item:hover {
          background: #f8f9fa;
        }

        .lesson-item.active {
          background: #e3f2fd;
          border-left: 4px solid #2196f3;
        }

        .lesson-item.completed {
          background: #e8f5e8;
        }

        .lesson-number {
          width: 30px;
          height: 30px;
          border-radius: 50%;
          background: #e9ecef;
          display: flex;
          align-items: center;
          justify-content: center;
          font-weight: 600;
          color: #495057;
        }

        .lesson-item.completed .lesson-number {
          background: #28a745;
          color: white;
        }

        .lesson-title {
          flex: 1;
          font-weight: 500;
        }

        .checkmark {
          color: #28a745;
          font-weight: bold;
        }

        .lesson-content {
          padding: 2rem;
          background: white;
          margin: 1rem;
          border-radius: 12px;
          box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }

        .lesson-display h2 {
          margin: 0 0 1.5rem 0;
          color: #2c3e50;
          font-size: 1.5rem;
        }

        .lesson-text {
          line-height: 1.6;
          color: #495057;
          margin-bottom: 2rem;
        }

        .chat-sidebar {
          background: white;
          padding: 2rem;
          border-left: 1px solid #e9ecef;
          display: flex;
          flex-direction: column;
        }

        .chat-sidebar h3 {
          margin: 0 0 1.5rem 0;
          color: #2c3e50;
        }

        .chat-messages {
          flex: 1;
          overflow-y: auto;
          margin-bottom: 1rem;
          max-height: 400px;
        }

        .message {
          margin-bottom: 1rem;
          padding: 1rem;
          border-radius: 8px;
        }

        .message.user {
          background: #e3f2fd;
          margin-left: 1rem;
        }

        .message.assistant {
          background: #f8f9fa;
          margin-right: 1rem;
        }

        .chat-input {
          display: flex;
          gap: 0.5rem;
        }

        .chat-input input {
          flex: 1;
          padding: 0.75rem;
          border: 1px solid #ddd;
          border-radius: 6px;
        }

        .quiz-display {
          background: #fff3cd;
          padding: 2rem;
          border-radius: 8px;
          margin-top: 2rem;
        }

        .quiz-question {
          margin-bottom: 2rem;
        }

        .quiz-options {
          margin: 1rem 0;
        }

        .option {
          display: block;
          margin-bottom: 0.5rem;
          cursor: pointer;
        }

        .certificate-section {
          margin-top: 2rem;
          padding: 1rem;
          background: linear-gradient(135deg, #667eea, #764ba2);
          border-radius: 8px;
          text-align: center;
          color: white;
        }

        .certificate-display {
          margin-top: 2rem;
          padding: 1rem;
          background: #d4edda;
          border-radius: 8px;
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
          background: #2196f3;
          color: white;
        }

        .btn.success {
          background: #28a745;
          color: white;
        }

        .loading {
          display: flex;
          justify-content: center;
          align-items: center;
          height: 200px;
          font-size: 1.2rem;
          color: #6c757d;
        }
      `}</style>
    </div>
  );
}

export default CourseContentViewer;