import React, { useEffect, useMemo, useState } from "react";
import "./App.css";
import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Axios instance with auth
const api = axios.create({ baseURL: API });
api.interceptors.request.use((config) => {
  const t = localStorage.getItem("access_token");
  if (t) config.headers.Authorization = `Bearer ${t}`;
  return config;
});

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

function Auth({ onAuthed }) {
  const [mode, setMode] = useState("login");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  const submit = async (e) => {
    e.preventDefault(); setError("");
    try {
      if (mode === "register") {
        await api.post(`/auth/register`, { name, email, password });
      }
      const res = await api.post(`/auth/login`, { email, password });
      localStorage.setItem("access_token", res.data.access_token);
      localStorage.setItem("refresh_token", res.data.refresh_token);
      const me = await api.get(`/auth/me`);
      localStorage.setItem("me", JSON.stringify(me.data));
      onAuthed(me.data);
    } catch (err) {
      setError(err?.response?.data?.detail || err.message);
    }
  };

  return (
    <div className="card narrow">
      <h2 className="title">{mode === "login" ? "Sign In" : "Create Account"}</h2>
      <form onSubmit={submit} className="form">
        {mode === "register" && (
          <div className="row">
            <label>Name</label>
            <input value={name} onChange={(e) => setName(e.target.value)} required />
          </div>
        )}
        <div className="row">
          <label>Email</label>
          <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
        </div>
        <div className="row">
          <label>Password</label>
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
        </div>
        {error && <div className="error">{error}</div>}
        <button className="btn" type="submit">{mode === "login" ? "Login" : "Register"}</button>
      </form>
      <div className="alt">
        {mode === "login" ? (
          <button className="link" onClick={() => setMode("register")}>Need an account? Register</button>
        ) : (
          <button className="link" onClick={() => setMode("login")}>Have an account? Login</button>
        )}
      </div>
    </div>
  );
}

function Header({ me, onLogout }) {
  return (
    <header className="App-header">
      <h1 className="logo">AI LMS</h1>
      <div className="userbox">
        <span>{me?.name} • {me?.role}</span>
        <button className="btn light" onClick={onLogout}>Logout</button>
      </div>
    </header>
  );
}

function InstructorPanel({ me }) {
  const [title, setTitle] = useState("");
  const [audience, setAudience] = useState("Beginners");
  const [difficulty, setDifficulty] = useState("beginner");
  const [courses, setCourses] = useState([]);
  const [topic, setTopic] = useState("");
  const [lessonsCount, setLessonsCount] = useState(5);
  const [error, setError] = useState("");

  const refresh = () => api.get(`/courses`).then(r => setCourses(r.data));
  useEffect(() => { refresh(); }, []);

  const createCourse = async (e) => {
    e.preventDefault(); setError("");
    try {
      await api.post(`/courses`, { title, audience, difficulty });
      setTitle(""); refresh();
    } catch (err) { setError(err?.response?.data?.detail || err.message); }
  };

  const generateCourse = async (e) => {
    e.preventDefault(); setError("");
    try {
      await api.post(`/ai/generate_course`, { topic, audience, difficulty, lessons_count: Number(lessonsCount) });
      setTopic(""); refresh();
    } catch (err) { setError(err?.response?.data?.detail || err.message); }
  };

  return (
    <div className="container">
      <div className="grid2">
        <div className="card">
          <h3 className="subtitle">Manual Course</h3>
          <form onSubmit={createCourse} className="form">
            <div className="row"><label>Title</label><input value={title} onChange={(e)=>setTitle(e.target.value)} required /></div>
            <div className="row grid2"><div><label>Audience</label><input value={audience} onChange={(e)=>setAudience(e.target.value)} /></div><div><label>Difficulty</label><select value={difficulty} onChange={(e)=>setDifficulty(e.target.value)}><option value="beginner">Beginner</option><option value="intermediate">Intermediate</option><option value="advanced">Advanced</option></select></div></div>
            {error && <div className="error">{error}</div>}
            <button className="btn" type="submit">Create</button>
          </form>
        </div>
        <div className="card">
          <h3 className="subtitle">AI Course Generator</h3>
          <form onSubmit={generateCourse} className="form">
            <div className="row"><label>Topic</label><input value={topic} onChange={(e)=>setTopic(e.target.value)} required /></div>
            <div className="row grid2"><div><label>Audience</label><input value={audience} onChange={(e)=>setAudience(e.target.value)} /></div><div><label>Lessons</label><input type="number" min={1} max={20} value={lessonsCount} onChange={(e)=>setLessonsCount(e.target.value)} /></div></div>
            {error && <div className="error">{error}</div>}
            <button className="btn" type="submit">Generate</button>
          </form>
        </div>
      </div>

      <div className="card">
        <h3 className="subtitle">My Courses</h3>
        <div className="list">
          {courses.map(c => <CourseListItem key={c.id} course={c} me={me} />)}
        </div>
      </div>
    </div>
  );
}

function CourseListItem({ course, me }) {
  const [open, setOpen] = useState(false);
  const sessionId = useSessionId(course.id);
  const [chatInput, setChatInput] = useState("");
  const [chat, setChat] = useState([]);
  const [sending, setSending] = useState(false);
  const [assignments, setAssignments] = useState([]);

  useEffect(()=>{ api.get(`/courses/${course.id}/assignments`).then(r=>setAssignments(r.data)); },[course.id]);

  const send = async () => {
    if (!chatInput.trim()) return;
    const msg = { id: crypto.randomUUID(), role: "user", message: chatInput, created_at: new Date().toISOString() };
    setChat((c) => [...c, msg]);
    setChatInput("");
    setSending(true);
    try {
      const res = await api.post(`/ai/chat`, { course_id: course.id, session_id: sessionId, message: msg.message });
      const reply = { id: crypto.randomUUID(), role: "assistant", message: res.data.reply, created_at: new Date().toISOString() };
      setChat((c) => [...c, reply]);
    } catch (err) {
      const reply = { id: crypto.randomUUID(), role: "assistant", message: err?.response?.data?.detail || err.message, created_at: new Date().toISOString() };
      setChat((c) => [...c, reply]);
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

  return (
    <div className="list-item column">
      <div className="row-between" onClick={()=>setOpen(!open)}>
        <div>
          <div className="item-title">{course.title}</div>
          <div className="item-sub">{course.audience} • {course.difficulty} • {course.lessons?.length || 0} lessons</div>
        </div>
        <span>⯈</span>
      </div>
      {open && (
        <div className="course">
          <div className="grid">
            <div className="pane">
              <h4 className="subtitle">Lessons</h4>
              {(course.lessons || []).map(l => (
                <div className="lesson" key={l.id}>
                  <div className="lesson-title">{l.title}</div>
                  <div className="lesson-content">{l.content}</div>
                </div>
              ))}
              <button className="btn mt" onClick={addLesson}>+ Add Lesson</button>
              <h4 className="subtitle mt">Assignments</h4>
              {assignments.map(a => (
                <div className="quiz" key={a.id}>
                  <div className="quiz-q">{a.title}</div>
                  <div className="item-sub">Due: {a.due_at || 'N/A'}</div>
                </div>
              ))}
              <button className="btn mt" onClick={createAssignment}>+ Create Assignment</button>
            </div>
            <div className="pane chat">
              <h4 className="subtitle">Course Q&amp;A</h4>
              <div className="chat-box">
                {chat.map(m => <div key={m.id} className={`bubble ${m.role}`}><div className="bubble-inner">{m.message}</div></div>)}
              </div>
              <div className="chat-input">
                <input value={chatInput} onChange={(e)=>setChatInput(e.target.value)} placeholder="Ask anything about this course..." onKeyDown={(e)=> (e.key === "Enter" && !sending ? (send(), null) : null)} />
                <button className="btn" disabled={sending} onClick={send}>{sending ? "Thinking..." : "Send"}</button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function StudentPanel({ me }) {
  const [courses, setCourses] = useState([]);
  const [selected, setSelected] = useState(null);
  const [chat, setChat] = useState([]);
  const [chatInput, setChatInput] = useState("");
  const [sending, setSending] = useState(false);
  const sessionId = useSessionId(selected?.id);

  const refresh = () => api.get(`/courses`).then(r => setCourses(r.data));
  useEffect(()=>{ refresh(); },[]);

  const enroll = async (c) => { await api.post(`/courses/${c.id}/enroll`); refresh(); };
  const open = async (c) => { setSelected(c); const h = await api.get(`/chats/${c.id}/${sessionId}`); setChat(h.data); };
  const send = async () => {
    if (!chatInput.trim() || !selected) return;
    const msg = { id: crypto.randomUUID(), role: "user", message: chatInput, created_at: new Date().toISOString() };
    setChat((c) => [...c, msg]); setChatInput(""); setSending(true);
    try {
      const res = await api.post(`/ai/chat`, { course_id: selected.id, session_id: sessionId, message: msg.message });
      setChat((c) => [...c, { id: crypto.randomUUID(), role: "assistant", message: res.data.reply, created_at: new Date().toISOString() }]);
    } finally { setSending(false); }
  };

  const submitAssignment = async (a) => {
    const text = prompt("Paste your answer"); if (!text) return;
    await api.post(`/assignments/${a.id}/submit`, { text_answer: text, file_ids: [] });
    alert("Submitted.");
  };

  return (
    <div className="container">
      {!selected ? (
        <div className="card">
          <h3 className="subtitle">Available Courses</h3>
          <div className="list">
            {courses.map(c => (
              <div key={c.id} className="list-item">
                <div>
                  <div className="item-title">{c.title}</div>
                  <div className="item-sub">{c.audience} • {c.difficulty} • {c.lessons?.length || 0} lessons</div>
                </div>
                <div className="row-gap">
                  <button className="btn light" onClick={()=>open(c)}>Open</button>
                  <button className="btn" onClick={()=>enroll(c)}>Enroll</button>
                </div>
              </div>
            ))}
          </div>
        </div>
      ) : (
        <div className="course">
          <button className="back" onClick={()=>setSelected(null)}>← Back</button>
          <h2 className="title">{selected.title}</h2>
          <div className="grid">
            <div className="pane">
              <h3 className="subtitle">Lessons</h3>
              {(selected.lessons || []).map(l => (
                <div className="lesson" key={l.id}>
                  <div className="lesson-title">{l.title}</div>
                  <div className="lesson-content">{l.content}</div>
                </div>
              ))}
              <h3 className="subtitle mt">Assignments</h3>
              <StudentAssignments courseId={selected.id} onSubmit={submitAssignment} />
            </div>
            <div className="pane chat">
              <h3 className="subtitle">Course Q&amp;A</h3>
              <div className="chat-box">{chat.map(m => <div key={m.id} className={`bubble ${m.role}`}><div className="bubble-inner">{m.message}</div></div>)}</div>
              <div className="chat-input">
                <input value={chatInput} onChange={(e)=>setChatInput(e.target.value)} placeholder="Ask anything about this course..." onKeyDown={(e)=> (e.key === "Enter" && !sending ? (send(), null) : null)} />
                <button className="btn" disabled={sending} onClick={send}>{sending ? "Thinking..." : "Send"}</button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

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

function AuditorPanel() {
  const [courses, setCourses] = useState([]);
  useEffect(()=>{ api.get(`/courses`).then(r=>setCourses(r.data)); }, []);
  return (
    <div className="container">
      <div className="card">
        <h3 className="subtitle">All Courses (Read-only)</h3>
        <div className="list">{courses.map(c => <div key={c.id} className="list-item"><div><div className="item-title">{c.title}</div><div className="item-sub">{c.audience} • {c.difficulty}</div></div></div>)}</div>
      </div>
    </div>
  );
}

function AdminPanel() {
  const [analytics, setAnalytics] = useState(null);
  const [users, setUsers] = useState([]);
  useEffect(()=>{ api.get(`/analytics/admin`).then(r=>setAnalytics(r.data)); },[]);
  useEffect(()=>{ api.get(`/auth/me`).then(()=>{}); },[]);
  return (
    <div className="container">
      <div className="card"><h3 className="subtitle">Platform Analytics</h3>{analytics && <div className="stats">Users: {analytics.users} • Courses: {analytics.courses} • Submissions: {analytics.submissions}</div>}</div>
    </div>
  );
}

function App() {
  const [me, setMe] = useState(null);
  useEffect(()=>{
    const cached = localStorage.getItem("me");
    if (cached) setMe(JSON.parse(cached));
  },[]);
  const logout = () => { localStorage.clear(); setMe(null); };

  return (
    <div className="App">
      <Header me={me} onLogout={logout} />
      {!me ? (
        <main className="container"><Auth onAuthed={setMe} /></main>
      ) : me.role === "admin" ? (
        <main><AdminPanel /></main>
      ) : me.role === "instructor" ? (
        <main><InstructorPanel me={me} /></main>
      ) : me.role === "student" ? (
        <main><StudentPanel me={me} /></main>
      ) : (
        <main><AuditorPanel /></main>
      )}
      <footer className="foot">Backend via REACT_APP_BACKEND_URL • All API routes under /api</footer>
    </div>
  );
}

export default App;