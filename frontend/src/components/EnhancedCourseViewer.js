import React, { useState, useEffect, useRef } from "react";
import api from "../services/api";

function EnhancedCourseViewer({ course, onProgressUpdate, onQuizSubmit }) {
  const [currentLessonIndex, setCurrentLessonIndex] = useState(0);
  const [lessonProgress, setLessonProgress] = useState({});
  const [showQuiz, setShowQuiz] = useState(false);
  const [quizAnswers, setQuizAnswers] = useState({});
  const [isCompleted, setIsCompleted] = useState(false);
  const [readingTime, setReadingTime] = useState(0);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const startTimeRef = useRef(Date.now());
  const contentRef = useRef(null);

  const currentLesson = course?.lessons?.[currentLessonIndex];
  const currentQuiz = course?.quiz?.find(q => q.id === currentLesson?.id);

  useEffect(() => {
    if (currentLesson) {
      startTimeRef.current = Date.now();
      setReadingTime(0);
      setIsCompleted(false);

      // Auto-save progress every 30 seconds
      const progressInterval = setInterval(() => {
        const currentTime = Date.now();
        const timeSpent = Math.floor((currentTime - startTimeRef.current) / 1000);
        setReadingTime(timeSpent);

        // Auto-mark as read after 2 minutes
        if (timeSpent >= 120 && !lessonProgress[currentLesson.id]?.completed) {
          markLessonComplete();
        }
      }, 1000);

      return () => clearInterval(progressInterval);
    }
  }, [currentLessonIndex, currentLesson]);

  const markLessonComplete = async () => {
    try {
      await api.post(`/courses/${course.id}/progress`, {
        lesson_id: currentLesson.id,
        completed: true
      });

      setLessonProgress(prev => ({
        ...prev,
        [currentLesson.id]: {
          ...prev[currentLesson.id],
          completed: true,
          completedAt: new Date().toISOString()
        }
      }));

      setIsCompleted(true);
      onProgressUpdate?.(currentLesson.id, true);
    } catch (error) {
      console.error('Error updating progress:', error);
    }
  };

  const handleQuizAnswer = (questionId, answerIndex) => {
    setQuizAnswers(prev => ({
      ...prev,
      [questionId]: answerIndex
    }));
  };

  const submitQuiz = async () => {
    if (!currentQuiz) return;

    const selectedAnswer = quizAnswers[currentQuiz.id];
    if (selectedAnswer === undefined) return;

    try {
      const response = await api.post(`/quizzes/${course.id}/submit`, {
        question_id: currentQuiz.id,
        selected_index: selectedAnswer
      });

      const isCorrect = response.data.correct;

      // Update progress with quiz score
      await api.post(`/courses/${course.id}/progress`, {
        lesson_id: currentLesson.id,
        completed: true,
        quiz_score: isCorrect ? 100 : 0
      });

      setLessonProgress(prev => ({
        ...prev,
        [currentLesson.id]: {
          ...prev[currentLesson.id],
          completed: true,
          quizScore: isCorrect ? 100 : 0,
          quizPassed: isCorrect
        }
      }));

      onQuizSubmit?.(currentQuiz.id, isCorrect);
      setShowQuiz(false);
      setIsCompleted(true);
    } catch (error) {
      console.error('Error submitting quiz:', error);
    }
  };

  const nextLesson = () => {
    if (currentLessonIndex < (course?.lessons?.length || 0) - 1) {
      setCurrentLessonIndex(currentLessonIndex + 1);
      setShowQuiz(false);
      setQuizAnswers({});
      setIsCompleted(false);
    }
  };

  const prevLesson = () => {
    if (currentLessonIndex > 0) {
      setCurrentLessonIndex(currentLessonIndex - 1);
      setShowQuiz(false);
      setQuizAnswers({});
      setIsCompleted(false);
    }
  };

  const toggleFullscreen = () => {
    setIsFullscreen(!isFullscreen);
  };

  const formatReadingTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  if (!course || !currentLesson) {
    return (
      <div className="enhanced-course-viewer loading">
        <div className="loading-skeleton">
          <div className="skeleton-title"></div>
          <div className="skeleton-text"></div>
          <div className="skeleton-text"></div>
          <div className="skeleton-text"></div>
        </div>
      </div>
    );
  }

  return (
    <div className={`enhanced-course-viewer ${isFullscreen ? 'fullscreen' : ''}`}>
      {/* Header */}
      <div className="viewer-header">
        <div className="lesson-nav">
          <button
            className="nav-btn"
            onClick={prevLesson}
            disabled={currentLessonIndex === 0}
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
              <path d="M15 18L9 12L15 6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
            Previous
          </button>

          <div className="lesson-indicator">
            <span className="current">{currentLessonIndex + 1}</span>
            <span className="separator">of</span>
            <span className="total">{course.lessons.length}</span>
          </div>

          <button
            className="nav-btn"
            onClick={nextLesson}
            disabled={currentLessonIndex === course.lessons.length - 1}
          >
            Next
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
              <path d="M9 18L15 12L9 6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </button>
        </div>

        <div className="lesson-actions">
          <div className="reading-timer">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
              <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2"/>
              <path d="M12 6V12L16 14" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
            {formatReadingTime(readingTime)}
          </div>

          <button className="action-btn" onClick={toggleFullscreen}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
              <path d="M8 3V5C8 5.53043 7.78929 6.03914 7.41421 6.41421C7.03914 6.78929 6.53043 7 6 7H4M20 9V7C20 6.46957 20.2107 5.96086 20.5858 5.58579C20.9609 5.21071 21.4696 5 22 5H20M16 21H14C13.4696 21 12.9609 20.7893 12.5858 20.4142C12.2107 20.0391 12 19.5304 12 19V17M4 15V17C4 17.5304 3.78929 18.0391 3.41421 18.4142C3.03914 18.7893 2.53043 19 2 19H4" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </button>
        </div>
      </div>

      {/* Progress Bar */}
      <div className="progress-container">
        <div className="progress-bar">
          <div
            className="progress-fill"
            style={{
              width: `${((currentLessonIndex + 1) / course.lessons.length) * 100}%`
            }}
          ></div>
        </div>
        <div className="progress-text">
          {Math.round(((currentLessonIndex + 1) / course.lessons.length) * 100)}% Complete
        </div>
      </div>

      {/* Main Content */}
      <div className="lesson-content" ref={contentRef}>
        {!showQuiz ? (
          <div className="lesson-display">
            {/* Lesson Header */}
            <div className="lesson-header">
              <div className="lesson-meta">
                <span className="lesson-number">Lesson {currentLessonIndex + 1}</span>
                {lessonProgress[currentLesson.id]?.completed && (
                  <span className="completion-badge">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                      <path d="M9 12L11 14L15 10M21 12C21 16.9706 16.9706 21 12 21C7.02944 21 3 16.9706 3 12C3 7.02944 7.02944 3 12 3C16.9706 3 21 7.02944 21 12Z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                    </svg>
                    Completed
                  </span>
                )}
              </div>
              <h1 className="lesson-title">{currentLesson.title}</h1>
            </div>

            {/* Lesson Content */}
            <div className="lesson-body">
              <div className="content-wrapper">
                {currentLesson.content && (
                  <div className="content-section">
                    <div className="content-text">
                      {currentLesson.content.split('\n').map((paragraph, index) => (
                        <p key={index} className={paragraph.trim() === '' ? 'spacer' : ''}>
                          {paragraph}
                        </p>
                      ))}
                    </div>
                  </div>
                )}

                {currentLesson.resources && currentLesson.resources.length > 0 && (
                  <div className="resources-section">
                    <h3>Resources</h3>
                    <div className="resources-list">
                      {currentLesson.resources.map((resource, index) => (
                        <div key={index} className="resource-item">
                          <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                            <path d="M14 2H6C4.89543 2 4 2.89543 4 4V20C4 21.1046 4.89543 22 6 22H18C19.1046 22 20 21.1046 20 20V8L14 2Z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                            <path d="M14 2V8H20" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                          </svg>
                          <span>{resource}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Lesson Actions */}
            <div className="lesson-actions">
              {!isCompleted ? (
                <button className="btn primary" onClick={markLessonComplete}>
                  Mark as Complete
                </button>
              ) : (
                <div className="completion-actions">
                  {currentQuiz ? (
                    <button className="btn secondary" onClick={() => setShowQuiz(true)}>
                      Take Quiz
                    </button>
                  ) : (
                    <button className="btn primary" onClick={nextLesson}>
                      Next Lesson
                    </button>
                  )}
                </div>
              )}
            </div>
          </div>
        ) : (
          <div className="quiz-display">
            <div className="quiz-header">
              <h2>Knowledge Check</h2>
              <p>Test your understanding of this lesson</p>
            </div>

            {currentQuiz && (
              <div className="quiz-content">
                <div className="quiz-question">
                  <h3>{currentQuiz.question}</h3>
                  <div className="quiz-options">
                    {currentQuiz.options.map((option, index) => (
                      <label
                        key={index}
                        className={`quiz-option ${
                          quizAnswers[currentQuiz.id] === index ? 'selected' : ''
                        }`}
                      >
                        <input
                          type="radio"
                          name={`quiz-${currentQuiz.id}`}
                          value={index}
                          checked={quizAnswers[currentQuiz.id] === index}
                          onChange={() => handleQuizAnswer(currentQuiz.id, index)}
                        />
                        <span className="option-text">{option.text}</span>
                      </label>
                    ))}
                  </div>
                </div>

                <div className="quiz-actions">
                  <button
                    className="btn secondary"
                    onClick={() => setShowQuiz(false)}
                  >
                    Back to Lesson
                  </button>
                  <button
                    className="btn primary"
                    onClick={submitQuiz}
                    disabled={quizAnswers[currentQuiz.id] === undefined}
                  >
                    Submit Answer
                  </button>
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      <style jsx>{`
        .enhanced-course-viewer {
          display: flex;
          flex-direction: column;
          height: 100%;
          background: var(--gray-50);
          border-radius: var(--radius-xl);
          overflow: hidden;
          transition: all var(--transition-normal);
        }

        .enhanced-course-viewer.fullscreen {
          position: fixed;
          top: 0;
          left: 0;
          width: 100vw;
          height: 100vh;
          z-index: 1000;
          border-radius: 0;
        }

        .viewer-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: var(--space-4) var(--space-6);
          background: rgba(255, 255, 255, 0.9);
          backdrop-filter: blur(20px);
          border-bottom: 1px solid var(--gray-200);
        }

        .lesson-nav {
          display: flex;
          align-items: center;
          gap: var(--space-4);
        }

        .nav-btn {
          display: flex;
          align-items: center;
          gap: var(--space-2);
          padding: var(--space-2) var(--space-4);
          background: var(--gray-100);
          border: 1px solid var(--gray-200);
          border-radius: var(--radius-lg);
          color: var(--gray-700);
          cursor: pointer;
          transition: all var(--transition-fast);
          font-size: 0.875rem;
          font-weight: 500;
        }

        .nav-btn:hover:not(:disabled) {
          background: var(--gray-200);
          transform: translateY(-1px);
        }

        .nav-btn:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }

        .lesson-indicator {
          display: flex;
          align-items: center;
          gap: var(--space-2);
          font-weight: 600;
          color: var(--gray-900);
        }

        .current {
          font-size: 1.25rem;
          color: var(--primary-600);
        }

        .separator {
          color: var(--gray-500);
        }

        .total {
          color: var(--gray-600);
        }

        .lesson-actions {
          display: flex;
          align-items: center;
          gap: var(--space-4);
        }

        .reading-timer {
          display: flex;
          align-items: center;
          gap: var(--space-2);
          padding: var(--space-2) var(--space-3);
          background: var(--gray-100);
          border-radius: var(--radius-lg);
          font-size: 0.875rem;
          font-weight: 500;
          color: var(--gray-700);
        }

        .action-btn {
          display: flex;
          align-items: center;
          justify-content: center;
          width: 40px;
          height: 40px;
          background: var(--gray-100);
          border: 1px solid var(--gray-200);
          border-radius: var(--radius-lg);
          color: var(--gray-700);
          cursor: pointer;
          transition: all var(--transition-fast);
        }

        .action-btn:hover {
          background: var(--gray-200);
          transform: translateY(-1px);
        }

        .progress-container {
          padding: 0 var(--space-6);
          background: rgba(255, 255, 255, 0.9);
        }

        .progress-bar {
          width: 100%;
          height: 6px;
          background: var(--gray-200);
          border-radius: var(--radius-full);
          overflow: hidden;
          margin-bottom: var(--space-2);
        }

        .progress-fill {
          height: 100%;
          background: linear-gradient(90deg, var(--primary-500), var(--secondary-500));
          border-radius: var(--radius-full);
          transition: width var(--transition-normal);
        }

        .progress-text {
          font-size: 0.875rem;
          font-weight: 500;
          color: var(--gray-600);
          text-align: center;
        }

        .lesson-content {
          flex: 1;
          overflow-y: auto;
          padding: var(--space-6);
        }

        .lesson-display {
          max-width: 800px;
          margin: 0 auto;
        }

        .lesson-header {
          margin-bottom: var(--space-6);
        }

        .lesson-meta {
          display: flex;
          align-items: center;
          gap: var(--space-3);
          margin-bottom: var(--space-3);
        }

        .lesson-number {
          padding: var(--space-1) var(--space-3);
          background: var(--primary-100);
          color: var(--primary-700);
          border-radius: var(--radius-full);
          font-size: 0.875rem;
          font-weight: 600;
        }

        .completion-badge {
          display: flex;
          align-items: center;
          gap: var(--space-2);
          padding: var(--space-1) var(--space-3);
          background: var(--success-100);
          color: var(--success-700);
          border-radius: var(--radius-full);
          font-size: 0.875rem;
          font-weight: 600;
        }

        .lesson-title {
          font-size: 2rem;
          font-weight: 800;
          color: var(--gray-900);
          line-height: 1.2;
          margin: 0;
        }

        .lesson-body {
          margin-bottom: var(--space-8);
        }

        .content-wrapper {
          background: white;
          border-radius: var(--radius-xl);
          padding: var(--space-6);
          box-shadow: var(--shadow-lg);
        }

        .content-section {
          margin-bottom: var(--space-6);
        }

        .content-text {
          line-height: 1.7;
          color: var(--gray-700);
        }

        .content-text p {
          margin-bottom: var(--space-4);
          font-size: 1rem;
        }

        .content-text p.spacer {
          margin-bottom: var(--space-2);
        }

        .resources-section h3 {
          font-size: 1.25rem;
          font-weight: 700;
          color: var(--gray-900);
          margin-bottom: var(--space-4);
        }

        .resources-list {
          display: grid;
          gap: var(--space-3);
        }

        .resource-item {
          display: flex;
          align-items: center;
          gap: var(--space-3);
          padding: var(--space-3);
          background: var(--gray-50);
          border-radius: var(--radius-lg);
          color: var(--gray-700);
          transition: all var(--transition-fast);
        }

        .resource-item:hover {
          background: var(--gray-100);
          transform: translateX(4px);
        }

        .lesson-actions {
          display: flex;
          justify-content: center;
          gap: var(--space-4);
        }

        .completion-actions {
          display: flex;
          gap: var(--space-4);
        }

        .quiz-display {
          max-width: 600px;
          margin: 0 auto;
        }

        .quiz-header {
          text-align: center;
          margin-bottom: var(--space-6);
        }

        .quiz-header h2 {
          font-size: 1.5rem;
          font-weight: 700;
          color: var(--gray-900);
          margin-bottom: var(--space-2);
        }

        .quiz-header p {
          color: var(--gray-600);
        }

        .quiz-content {
          background: white;
          border-radius: var(--radius-xl);
          padding: var(--space-6);
          box-shadow: var(--shadow-lg);
        }

        .quiz-question h3 {
          font-size: 1.125rem;
          font-weight: 600;
          color: var(--gray-900);
          margin-bottom: var(--space-4);
          line-height: 1.4;
        }

        .quiz-options {
          display: grid;
          gap: var(--space-3);
        }

        .quiz-option {
          display: flex;
          align-items: flex-start;
          gap: var(--space-3);
          padding: var(--space-4);
          background: var(--gray-50);
          border: 2px solid var(--gray-200);
          border-radius: var(--radius-lg);
          cursor: pointer;
          transition: all var(--transition-fast);
        }

        .quiz-option:hover {
          background: var(--gray-100);
          border-color: var(--primary-300);
        }

        .quiz-option.selected {
          background: var(--primary-50);
          border-color: var(--primary-500);
        }

        .quiz-option input[type="radio"] {
          margin-top: 2px;
          accent-color: var(--primary-600);
        }

        .option-text {
          flex: 1;
          color: var(--gray-700);
          line-height: 1.5;
        }

        .quiz-actions {
          display: flex;
          justify-content: space-between;
          gap: var(--space-4);
          margin-top: var(--space-6);
        }

        .loading {
          display: flex;
          align-items: center;
          justify-content: center;
          height: 400px;
        }

        .loading-skeleton {
          width: 100%;
          max-width: 600px;
        }

        .skeleton-title {
          height: 2rem;
          width: 70%;
          margin-bottom: var(--space-4);
        }

        .skeleton-text {
          height: 1rem;
          width: 100%;
          margin-bottom: var(--space-3);
        }

        .skeleton-text:nth-child(3) {
          width: 80%;
        }

        .skeleton-text:nth-child(4) {
          width: 60%;
        }

        /* Responsive Design */
        @media (max-width: 768px) {
          .viewer-header {
            padding: var(--space-3) var(--space-4);
            flex-direction: column;
            gap: var(--space-4);
          }

          .lesson-nav {
            width: 100%;
            justify-content: space-between;
          }

          .lesson-indicator {
            order: 2;
          }

          .lesson-actions {
            order: 3;
          }

          .lesson-title {
            font-size: 1.5rem;
          }

          .content-wrapper {
            padding: var(--space-4);
          }

          .quiz-content {
            padding: var(--space-4);
          }
        }

        @media (max-width: 480px) {
          .viewer-header {
            padding: var(--space-2);
          }

          .nav-btn {
            padding: var(--space-2) var(--space-3);
            font-size: 0.8125rem;
          }

          .lesson-title {
            font-size: 1.25rem;
          }

          .quiz-option {
            padding: var(--space-3);
          }

          .quiz-actions {
            flex-direction: column;
          }
        }
      `}</style>
    </div>
  );
}

export default EnhancedCourseViewer;