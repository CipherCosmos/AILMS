import React, { useState } from "react";
import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const api = axios.create({ baseURL: API });
api.interceptors.request.use((config) => {
  const t = localStorage.getItem("access_token");
  if (t) config.headers.Authorization = `Bearer ${t}`;
  return config;
});

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

export default Auth;