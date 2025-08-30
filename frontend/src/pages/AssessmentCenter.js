import React, { useEffect, useState, useRef } from "react";
import api from "../services/api";

function AssessmentCenter() {
  const [activeTab, setActiveTab] = useState("banks");
  const [questionBanks, setQuestionBanks] = useState([]);
  const [selectedBank, setSelectedBank] = useState(null);
  const [questions, setQuestions] = useState([]);
  const [quizTemplates, setQuizTemplates] = useState([]);
  const [currentQuiz, setCurrentQuiz] = useState(null);
  const [quizAttempt, setQuizAttempt] = useState(null);
  const [answers, setAnswers] = useState({});
  const [timeRemaining, setTimeRemaining] = useState(0);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [proctoringEnabled, setProctoringEnabled] = useState(false);
  const [incidents, setIncidents] = useState([]);
  const videoRef = useRef(null);
  const canvasRef = useRef(null);

  useEffect(() => {
    loadAssessmentData();
  }, [activeTab]);

  useEffect(() => {
    let timer;
    if (timeRemaining > 0 && quizAttempt) {
      timer = setInterval(() => {
        setTimeRemaining(prev => {
          if (prev <= 1) {
            // Auto-submit when time runs out
            handleSubmitQuiz();
            return 0;
          }
          return prev - 1;
        });
      }, 1000);
    }
    return () => clearInterval(timer);
  }, [timeRemaining, quizAttempt]);

  const loadAssessmentData = async () => {
    try {
      if (activeTab === "banks") {
        const res = await api.get("/assessment/question-banks?tenant_id=default");
        setQuestionBanks(res.data);
      } else if (activeTab === "templates") {
        const res = await api.get("/assessment/quiz-templates?tenant_id=default");
        setQuizTemplates(res.data);
      }
    } catch (error) {
      console.error("Failed to load assessment data:", error);
    }
  };

  const createQuestionBank = async () => {
    const name = prompt("Enter question bank name:");
    const subject = prompt("Enter subject:");
    if (!name || !subject) return;

    try {
      await api.post("/assessment/question-banks", {
        tenant_id: "default",
        name,
        subject,
        grade_level: "general"
      });
      loadAssessmentData();
    } catch (error) {
      alert("Failed to create question bank");
    }
  };

  const generateQuestionsAI = async (bankId) => {
    const count = parseInt(prompt("How many questions to generate?", "5"));
    const topic = prompt("Enter topic:");
    const difficulty = prompt("Enter difficulty (easy/medium/hard):", "medium");

    if (!count || !topic) return;

    try {
      const res = await api.post("/assessment/ai/generate-questions", {
        bank_id: bankId,
        count,
        subject: topic,
        topic,
        difficulty,
        tenant_id: "default"
      });
      alert(`Generated ${res.data.count} questions successfully!`);
      loadQuestions(bankId);
    } catch (error) {
      alert("Failed to generate questions");
    }
  };

  const loadQuestions = async (bankId) => {
    try {
      const res = await api.get(`/assessment/question-banks/${bankId}/questions`);
      setSelectedBank(bankId);
      setQuestions(res.data);
    } catch (error) {
      console.error("Failed to load questions:", error);
      // If endpoint doesn't exist yet, show empty state
      setSelectedBank(bankId);
      setQuestions([]);
    }
  };

  const startQuiz = async (templateId) => {
    try {
      const res = await api.post(`/assessment/quizzes/${templateId}/attempts`, {});
      setQuizAttempt(res.data);
      setTimeRemaining(res.data.time_remaining || 3600); // 1 hour default
      setProctoringEnabled(res.data.proctoring_enabled || false);

      if (res.data.proctoring_enabled) {
        enterFullscreen();
        startProctoring();
      }
    } catch (error) {
      alert("Failed to start quiz");
    }
  };

  const handleAnswerChange = (questionId, answer) => {
    setAnswers(prev => ({
      ...prev,
      [questionId]: answer
    }));
  };

  const handleSubmitQuiz = async () => {
    if (!quizAttempt) return;

    try {
      const res = await api.post(`/assessment/quiz-attempts/${quizAttempt._id}/finish`);
      alert(`Quiz completed! Score: ${res.data.percentage}%`);
      setQuizAttempt(null);
      setAnswers({});
      setTimeRemaining(0);
      exitFullscreen();
      stopProctoring();
    } catch (error) {
      alert("Failed to submit quiz");
    }
  };

  const enterFullscreen = () => {
    if (document.documentElement.requestFullscreen) {
      document.documentElement.requestFullscreen();
      setIsFullscreen(true);
    }
  };

  const exitFullscreen = () => {
    if (document.exitFullscreen) {
      document.exitFullscreen();
      setIsFullscreen(false);
    }
  };

  const startProctoring = async () => {
    try {
      // Request camera access
      const stream = await navigator.mediaDevices.getUserMedia({
        video: true,
        audio: false
      });
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
      }

      // Start monitoring
      setInterval(() => {
        detectTabSwitch();
        captureScreenshot();
      }, 30000); // Every 30 seconds
    } catch (error) {
      console.error("Failed to start proctoring:", error);
    }
  };

  const stopProctoring = () => {
    if (videoRef.current && videoRef.current.srcObject) {
      const stream = videoRef.current.srcObject;
      stream.getTracks().forEach(track => track.stop());
    }
  };

  const detectTabSwitch = () => {
    if (document.hidden) {
      reportIncident("tab_switch", "User switched tabs/windows");
    }
  };

  const captureScreenshot = () => {
    if (canvasRef.current && videoRef.current) {
      const canvas = canvasRef.current;
      const video = videoRef.current;
      const ctx = canvas.getContext('2d');
      ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

      // In production, you'd upload this to server
      console.log("Screenshot captured");
    }
  };

  const reportIncident = async (type, description) => {
    if (!quizAttempt) return;

    try {
      await api.post("/assessment/proctoring/incidents", {
        quiz_attempt_id: quizAttempt._id,
        type,
        description
      });
      setIncidents(prev => [...prev, { type, description, timestamp: new Date() }]);
    } catch (error) {
      console.error("Failed to report incident:", error);
    }
  };

  const formatTime = (seconds) => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
    return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <div className="assessment-center">
      <div className="assessment-header">
        <h1>📝 Assessment Center</h1>
        <p>Create, manage, and take assessments with advanced proctoring</p>
      </div>

      <div className="assessment-tabs">
        <button
          className={activeTab === "banks" ? "active" : ""}
          onClick={() => setActiveTab("banks")}
        >
          📚 Question Banks
        </button>
        <button
          className={activeTab === "templates" ? "active" : ""}
          onClick={() => setActiveTab("templates")}
        >
          📋 Quiz Templates
        </button>
        <button
          className={activeTab === "integrity" ? "active" : ""}
          onClick={() => setActiveTab("integrity")}
        >
          🛡️ Academic Integrity
        </button>
        <button
          className={activeTab === "credentials" ? "active" : ""}
          onClick={() => setActiveTab("credentials")}
        >
          🏆 Credentials
        </button>
      </div>

      <div className="assessment-content">
        {/* Question Banks Tab */}
        {activeTab === "banks" && (
          <div className="question-banks">
            <div className="section-header">
              <h2>Question Banks</h2>
              <button className="btn primary" onClick={createQuestionBank}>
                + Create Bank
              </button>
            </div>

            <div className="banks-grid">
              {questionBanks.map(bank => (
                <div key={bank._id} className="bank-card">
                  <h3>{bank.name}</h3>
                  <p>{bank.subject} • {bank.questions_count || 0} questions</p>
                  <div className="bank-actions">
                    <button
                      className="btn secondary"
                      onClick={() => loadQuestions(bank._id)}
                    >
                      View Questions
                    </button>
                    <button
                      className="btn accent"
                      onClick={() => generateQuestionsAI(bank._id)}
                    >
                      🤖 Generate AI
                    </button>
                  </div>
                </div>
              ))}
            </div>

            {selectedBank && questions.length > 0 && (
              <div className="questions-section">
                <h3>Questions in Selected Bank</h3>
                <div className="questions-list">
                  {questions.map(question => (
                    <div key={question.id} className="question-item">
                      <div className="question-header">
                        <span className="question-type">{question.type}</span>
                        <span className="question-points">1 pt</span>
                      </div>
                      <div className="question-text">{question.question_text}</div>

                      {question.type === "multiple_choice" && (
                        <div className="question-options">
                          {question.question_data.options.map((option, index) => (
                            <div key={index} className="option">
                              <input
                                type="radio"
                                name={`question-${question.id}`}
                                value={option.text}
                                checked={answers[question.id] === option.text}
                                onChange={(e) => handleAnswerChange(question.id, e.target.value)}
                              />
                              <label>{option.text}</label>
                              {option.is_correct && <span className="correct-indicator">✓</span>}
                            </div>
                          ))}
                        </div>
                      )}

                      {question.type === "true_false" && (
                        <div className="question-options">
                          <div className="option">
                            <input
                              type="radio"
                              name={`question-${question.id}`}
                              value="true"
                              checked={answers[question.id] === "true"}
                              onChange={(e) => handleAnswerChange(question.id, "true")}
                            />
                            <label>True</label>
                          </div>
                          <div className="option">
                            <input
                              type="radio"
                              name={`question-${question.id}`}
                              value="false"
                              checked={answers[question.id] === "false"}
                              onChange={(e) => handleAnswerChange(question.id, "false")}
                            />
                            <label>False</label>
                          </div>
                        </div>
                      )}

                      {question.type === "short_answer" && (
                        <textarea
                          placeholder="Enter your answer..."
                          value={answers[question.id] || ""}
                          onChange={(e) => handleAnswerChange(question.id, e.target.value)}
                          rows="3"
                        />
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Quiz Templates Tab */}
        {activeTab === "templates" && (
          <div className="quiz-templates">
            <div className="section-header">
              <h2>Quiz Templates</h2>
              <button className="btn primary" onClick={() => alert("Create template functionality")}>
                + Create Template
              </button>
            </div>

            <div className="templates-grid">
              {quizTemplates.map(template => (
                <div key={template._id} className="template-card">
                  <h3>{template.name}</h3>
                  <p>{template.description}</p>
                  <div className="template-meta">
                    <span>⏱️ {template.settings?.time_limit || "No limit"}</span>
                    <span>📊 {template.settings?.attempts_allowed || 1} attempts</span>
                  </div>
                  <button
                    className="btn primary"
                    onClick={() => startQuiz(template._id)}
                  >
                    Start Quiz
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Quiz Taking Interface */}
        {quizAttempt && (
          <div className="quiz-interface">
            <div className="quiz-header">
              <div className="quiz-info">
                <h2>Quiz in Progress</h2>
                <div className="quiz-stats">
                  <span className="time">⏱️ {formatTime(timeRemaining)}</span>
                  <span className="questions">📝 {Object.keys(answers).length} answered</span>
                </div>
              </div>
              <button className="btn danger" onClick={handleSubmitQuiz}>
                Submit Quiz
              </button>
            </div>

            {proctoringEnabled && (
              <div className="proctoring-notice">
                <div className="notice-content">
                  <h3>🛡️ Proctoring Active</h3>
                  <p>This quiz is being monitored. Please stay in fullscreen mode.</p>
                  <div className="proctoring-indicators">
                    <span className={`indicator ${isFullscreen ? 'active' : 'inactive'}`}>
                      Fullscreen: {isFullscreen ? 'Active' : 'Inactive'}
                    </span>
                    <span className="indicator active">Camera: Active</span>
                  </div>
                </div>
                <video ref={videoRef} autoPlay muted className="proctoring-video" />
                <canvas ref={canvasRef} style={{ display: 'none' }} width="320" height="240" />
              </div>
            )}

            {incidents.length > 0 && (
              <div className="incidents-panel">
                <h3>⚠️ Proctoring Incidents</h3>
                <div className="incidents-list">
                  {incidents.map((incident, index) => (
                    <div key={index} className="incident-item">
                      <span className="incident-type">{incident.type}</span>
                      <span className="incident-description">{incident.description}</span>
                      <span className="incident-time">
                        {incident.timestamp.toLocaleTimeString()}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className="quiz-questions">
              {/* Quiz questions would be rendered here */}
              <div className="question-placeholder">
                <p>Quiz questions would be displayed here with the same interface as question banks.</p>
                <p>Each question type (MCQ, True/False, Short Answer, Essay, Code) would have appropriate input controls.</p>
              </div>
            </div>
          </div>
        )}

        {/* Academic Integrity Tab */}
        {activeTab === "integrity" && (
          <div className="academic-integrity">
            <h2>Academic Integrity Tools</h2>
            <div className="integrity-tools">
              <div className="tool-card">
                <h3>🔍 Plagiarism Detection</h3>
                <p>Check submissions against multiple sources</p>
                <button className="btn secondary">Run Check</button>
              </div>
              <div className="tool-card">
                <h3>🤖 AI Content Detection</h3>
                <p>Identify AI-generated content in submissions</p>
                <button className="btn secondary">Analyze</button>
              </div>
              <div className="tool-card">
                <h3>📊 Integrity Reports</h3>
                <p>View detailed integrity analysis reports</p>
                <button className="btn secondary">View Reports</button>
              </div>
            </div>
          </div>
        )}

        {/* Credentials Tab */}
        {activeTab === "credentials" && (
          <div className="credentials">
            <h2>Blockchain Credentials</h2>
            <div className="credentials-tools">
              <div className="tool-card">
                <h3>🎓 Issue Certificate</h3>
                <p>Issue blockchain-verifiable certificates</p>
                <button className="btn primary">Issue Certificate</button>
              </div>
              <div className="tool-card">
                <h3>✅ Verify Credential</h3>
                <p>Verify the authenticity of credentials</p>
                <button className="btn secondary">Verify</button>
              </div>
              <div className="tool-card">
                <h3>📜 Certificate Templates</h3>
                <p>Manage certificate templates and designs</p>
                <button className="btn secondary">Manage Templates</button>
              </div>
            </div>
          </div>
        )}
      </div>

      <style jsx>{`
        .assessment-center {
          min-height: 100vh;
          background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
          padding: 2rem;
        }

        .assessment-header {
          text-align: center;
          margin-bottom: 2rem;
        }

        .assessment-header h1 {
          background: linear-gradient(135deg, #667eea, #764ba2);
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
          background-clip: text;
          font-size: 2.5rem;
          margin-bottom: 0.5rem;
        }

        .assessment-header p {
          color: #6c757d;
          font-size: 1.1rem;
        }

        .assessment-tabs {
          display: flex;
          justify-content: center;
          margin-bottom: 2rem;
          background: white;
          border-radius: 12px;
          padding: 0.5rem;
          box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }

        .assessment-tabs button {
          padding: 0.75rem 1.5rem;
          border: none;
          background: transparent;
          border-radius: 8px;
          font-weight: 600;
          cursor: pointer;
          transition: all 0.3s;
          color: #6c757d;
        }

        .assessment-tabs button.active {
          background: #667eea;
          color: white;
        }

        .assessment-tabs button:hover {
          background: #f8f9fa;
        }

        .assessment-content {
          max-width: 1200px;
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

        .banks-grid, .templates-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
          gap: 1rem;
        }

        .bank-card, .template-card {
          background: white;
          padding: 1.5rem;
          border-radius: 12px;
          box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }

        .bank-card h3, .template-card h3 {
          margin: 0 0 0.5rem 0;
          color: #2c3e50;
        }

        .bank-card p, .template-card p {
          color: #6c757d;
          margin: 0 0 1rem 0;
        }

        .bank-actions {
          display: flex;
          gap: 0.5rem;
        }

        .template-meta {
          display: flex;
          gap: 1rem;
          margin-bottom: 1rem;
          font-size: 0.9rem;
          color: #6c757d;
        }

        .questions-section {
          background: white;
          padding: 2rem;
          border-radius: 12px;
          margin-top: 2rem;
          box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }

        .questions-list {
          display: flex;
          flex-direction: column;
          gap: 1.5rem;
        }

        .question-item {
          border: 2px solid #e9ecef;
          border-radius: 8px;
          padding: 1.5rem;
        }

        .question-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 1rem;
        }

        .question-type {
          background: #667eea;
          color: white;
          padding: 0.25rem 0.5rem;
          border-radius: 12px;
          font-size: 0.8rem;
          text-transform: capitalize;
        }

        .question-points {
          color: #28a745;
          font-weight: 600;
        }

        .question-text {
          font-weight: 600;
          color: #2c3e50;
          margin-bottom: 1rem;
        }

        .question-options {
          display: flex;
          flex-direction: column;
          gap: 0.5rem;
        }

        .option {
          display: flex;
          align-items: center;
          gap: 0.5rem;
        }

        .option input {
          margin: 0;
        }

        .correct-indicator {
          color: #28a745;
          font-weight: bold;
        }

        .question-item textarea {
          width: 100%;
          padding: 0.75rem;
          border: 2px solid #e9ecef;
          border-radius: 8px;
          font-family: inherit;
          resize: vertical;
        }

        .quiz-interface {
          background: white;
          border-radius: 12px;
          padding: 2rem;
          box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        }

        .quiz-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 2rem;
          padding-bottom: 1rem;
          border-bottom: 2px solid #e9ecef;
        }

        .quiz-info h2 {
          margin: 0 0 0.5rem 0;
          color: #2c3e50;
        }

        .quiz-stats {
          display: flex;
          gap: 2rem;
          font-size: 1.1rem;
          font-weight: 600;
        }

        .time {
          color: #dc3545;
        }

        .questions {
          color: #667eea;
        }

        .proctoring-notice {
          background: #fff3cd;
          border: 1px solid #ffeaa7;
          border-radius: 8px;
          padding: 1rem;
          margin-bottom: 2rem;
          display: flex;
          align-items: center;
          gap: 1rem;
        }

        .notice-content {
          flex: 1;
        }

        .notice-content h3 {
          margin: 0 0 0.5rem 0;
          color: #856404;
        }

        .notice-content p {
          margin: 0 0 0.5rem 0;
          color: #856404;
        }

        .proctoring-indicators {
          display: flex;
          gap: 1rem;
        }

        .indicator {
          padding: 0.25rem 0.5rem;
          border-radius: 12px;
          font-size: 0.8rem;
          font-weight: 600;
        }

        .indicator.active {
          background: #d4edda;
          color: #155724;
        }

        .indicator.inactive {
          background: #f8d7da;
          color: #721c24;
        }

        .proctoring-video {
          width: 200px;
          height: 150px;
          border-radius: 8px;
          object-fit: cover;
        }

        .incidents-panel {
          background: #f8d7da;
          border: 1px solid #f5c6cb;
          border-radius: 8px;
          padding: 1rem;
          margin-bottom: 2rem;
        }

        .incidents-panel h3 {
          margin: 0 0 1rem 0;
          color: #721c24;
        }

        .incidents-list {
          display: flex;
          flex-direction: column;
          gap: 0.5rem;
        }

        .incident-item {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 0.5rem;
          background: rgba(255,255,255,0.5);
          border-radius: 4px;
        }

        .incident-type {
          font-weight: 600;
          color: #721c24;
          text-transform: capitalize;
        }

        .incident-description {
          flex: 1;
          margin: 0 1rem;
          color: #721c24;
        }

        .incident-time {
          color: #721c24;
          font-size: 0.8rem;
        }

        .question-placeholder {
          text-align: center;
          padding: 3rem;
          color: #6c757d;
        }

        .integrity-tools, .credentials-tools {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
          gap: 1rem;
        }

        .tool-card {
          background: white;
          padding: 2rem;
          border-radius: 12px;
          box-shadow: 0 2px 8px rgba(0,0,0,0.1);
          text-align: center;
        }

        .tool-card h3 {
          color: #2c3e50;
          margin-bottom: 0.5rem;
        }

        .tool-card p {
          color: #6c757d;
          margin-bottom: 1rem;
        }

        .btn {
          padding: 0.75rem 1.5rem;
          border: none;
          border-radius: 8px;
          font-weight: 600;
          cursor: pointer;
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

        .btn.accent {
          background: #28a745;
          color: white;
        }

        .btn.danger {
          background: #dc3545;
          color: white;
        }

        .btn:hover {
          transform: translateY(-2px);
          box-shadow: 0 4px 12px rgba(0,0,0,0.2);
        }

        @media (max-width: 768px) {
          .assessment-tabs {
            flex-direction: column;
          }

          .banks-grid, .templates-grid {
            grid-template-columns: 1fr;
          }

          .bank-actions {
            flex-direction: column;
          }

          .quiz-header {
            flex-direction: column;
            gap: 1rem;
          }

          .quiz-stats {
            flex-direction: column;
            gap: 0.5rem;
          }

          .proctoring-notice {
            flex-direction: column;
          }

          .incident-item {
            flex-direction: column;
            gap: 0.5rem;
            align-items: flex-start;
          }
        }
      `}</style>
    </div>
  );
}

export default AssessmentCenter;