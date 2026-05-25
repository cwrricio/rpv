import React from "react";
import "./header.css";

// Mock user (temporariamente) usando imagem local em `public/emanuel.png`
const MOCK_USER = {
  displayName: "Gilleanes Guedes",
  photoURL: "/gilleanes.jpg",
};

export default function Header() {
  const user = MOCK_USER;

  return (
    <header className="app-header">
      <div className="header-left">&nbsp;</div>
      <div className="header-right">
        <div className="user-box">
          <img
            className="user-photo"
            src={user.photoURL}
            alt={user.displayName}
          />
          <div className="user-name">{user.displayName}</div>
        </div>
      </div>
    </header>
  );
}
