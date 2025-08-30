import React, { useEffect, useState } from "react";
import api from "../services/api";

function AuditorDashboard() {
  const [courses, setCourses] = useState([]);
  const [search, setSearch] = useState("");
  useEffect(()=>{ api.get(`/courses`).then(r=>setCourses(r.data)); }, []);
  const filtered = courses.filter(c => c.title.toLowerCase().includes(search.toLowerCase()) || c.audience.toLowerCase().includes(search.toLowerCase()));
  return (
    <div className="container">
      <div className="card">
        <h3 className="subtitle">All Courses (Read-only)</h3>
        <input placeholder="Search courses..." value={search} onChange={(e)=>setSearch(e.target.value)} />
        <div className="list">{filtered.map(c => <div key={c.id} className="list-item"><div><div className="item-title">{c.title}</div><div className="item-sub">{c.audience} • {c.difficulty}</div></div></div>)}</div>
      </div>
    </div>
  );
}

export default AuditorDashboard;