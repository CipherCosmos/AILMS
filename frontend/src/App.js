import React, { useEffect, useMemo, useState } from "react";
import "./App.css";
import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

function useSessionId(courseId) {
  return useMemo(() => {
    if (!courseId) return "";
    const key = `session-${courseId}`;
    let sid = localStorage.getItem(key);
    if (!sid) {
      sid = crypto.randomUUID();
      localStorage.setItem(key, sid);
    }
    return sid;
  }, [courseId]);
}

function Generator({ onCreated }) {
  const [topic, setTopic] = useState("");
  const [audience, setAudience] = useState("Beginners");
  const [difficulty, setDifficulty] = useState("beginner");
  const [lessons, setLessons] = useState(5);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const submit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      const res = await axios.post(`${API}/ai/generate_course`, {
        topic,
        audience,
        difficulty,
        lessons_count: Number(lessons),
      });
      onCreated(res.data);
    } catch (err) {
      setError(err?.response?.data?.detail || err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="card">
      <h2 className="title">AI Course &amp; Quiz Generator</h2>
      <form onSubmit={submit} className="form">
        <div className="row">
          <label>Topic</label>
          <input value={topic} onChange={(e) => setTopic(e.target.value)} placeholder="e.g. Intro to Prompt Engineering" required />
        </div>
        <div className="row grid2">
          <div>
            <label>Audience</label>
            <input value={audience} onChange={(e) => setAudience(e.target.value)} />
          </div>
          <div>
            <label>Difficulty</label>
            <select value={difficulty} onChange={(e) => setDifficulty(e.target.value)}>
              <option value="beginner">Beginner</option>
              <option value="intermediate">Intermediate</option>
              <option value="advanced">Advanced</option>
            </select>
          </div>
        </div>
        <div className="row">
          <label>Lessons</label>
          <input type="number" min={1} max={20} value={lessons} onChange={(e) => setLessons(e.target.value)} />
        </div>
        {error && <div className="error">{error}</div>}
        <button className="btn" type="submit" disabled={loading}>
          {loading ? "Generating..." : "Generate Course"}
        </button>
      </form>
    </div>
  );
}

function CourseList({ courses, onOpen }) {
  return (
    <div className="card">
      <h3 className="subtitle">Your Courses</h3>
      <div className="list">
        {courses.map((c) => (
          <button key={c.id} className="list-item" onClick={() => onOpen(c)}>
            <div>
              <div className="item-title">{c.topic}</div>
              <div className="item-sub">{c.audience} • {c.difficulty} • {c.lessons_count} lessons</div>
            </div>
            <span>→</span>
          </button>
        ))}
      </div>
    </div>
  );
}

function CourseView({ course, onBack }) {
  const sessionId = useSessionId(course?.id);
  const [chatInput, setChatInput] = useState("");
  const [chat, setChat] = useState([]);
  const [sending, setSending] = useState(false);

  useEffect(() => {
    if (!course) return;
    axios
      .get(`${API}/chats/${course.id}/${sessionId}`)
      .then((res) => setChat(res.data))
      .catch(() => {});
  }, [course, sessionId]);

  const send = async () => {
    if (!chatInput.trim()) return;
    const msg = { id: crypto.randomUUID(), role: "user", message: chatInput, created_at: new Date().toISOString() };
    setChat((c) => [...c, msg]);
    setChatInput("");
    setSending(true);
    try {
      const res = await axios.post(`${API}/ai/chat`, {
        course_id: course.id,
        session_id: sessionId,
        message: msg.message,
      });
      const reply = { id: crypto.randomUUID(), role: "assistant", message: res.data.reply, created_at: new Date().toISOString() };
      setChat((c) => [...c, reply]);
    } catch (err) {
      const reply = { id: crypto.randomUUID(), role: "assistant", message: err?.response?.data?.detail || err.message, created_at: new Date().toISOString() };
      setChat((c) => [...c, reply]);
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="course">
      <button className="back" onClick={onBack}>← Back</button>
      <h2 className="title">{course.topic}</h2>
      <div className="grid">
        <div className="pane">
          <h3 className="subtitle">Lessons</h3>
          {course.lessons.map((l) => (
            <div className="lesson" key={l.id}>
              <div className="lesson-title">{l.title}</div>
              <div className="lesson-content">{l.content}</div>
            </div>
          ))}
          <h3 className="subtitle mt">Quiz</h3>
          {course.quiz.map((q) => (
            <div className="quiz" key={q.id}>
              <div className="quiz-q">{q.question}</div>
              <ul className="quiz-opts">
                {q.options.map((o, i) => (
                  <li key={i}>• {o.text}</li>
                ))}
              </ul>
              {q.explanation && <div className="quiz-exp">Explanation: {q.explanation}</div>}
            </div>
          ))}
        </div>
        <div className="pane chat">
          <h3 className="subtitle">Course Q&amp;A</h3>
          <div className="chat-box">
            {chat.map((m) => (
              <div key={m.id} className={`bubble ${m.role}`}>
                <div className="bubble-inner">{m.message}</div>
              </div>
            ))}
          </div>
          <div className="chat-input">
            <input
              value={chatInput}
              onChange={(e) => setChatInput(e.target.value)}
              placeholder="Ask anything about this course..."
              onKeyDown={(e) => e.key === "Enter" &amp;&amp; !sending ? send() : null}
            />
            <button className="btn" disabled={sending} onClick={send}>{sending ? "Thinking..." : "Send"}</button>
          </div>
        </div>
      </div>
    </div>
  );
}

function App() {
  const [courses, setCourses] = useState([]);
  const [current, setCurrent] = useState(null);

  const refresh = () => {
    axios.get(`${API}/courses`).then((res) => setCourses(res.data)).catch(() => {});
  };

  useEffect(() => {
    refresh();
  }, []);

  return (
    <div className="App">
      <header className="App-header">
        <h1 className="logo">AI LMS</h1>
        <p className="tag">Generate courses with quizzes, then chat with them.</p>
      </header>
      <main className="container">
        {!current ? (
          <>
            <Generator onCreated={(c) => { setCurrent(c); refresh(); }} />
            <CourseList courses={courses} onOpen={(c) => setCurrent(c)} />
          </>
        ) : (
          <CourseView course={current} onBack={() => setCurrent(null)} />
        )}
      </main>
      <footer className="foot">Backend: using REACT_APP_BACKEND_URL • All routes prefixed with /api</footer>
    </div>
  );
}

export default App;