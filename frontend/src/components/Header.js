import React from "react";

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

export default Header;