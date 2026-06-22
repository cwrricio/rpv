import { useState } from "react";
import { useNavigate } from "react-router-dom";
import "./Login.css";

export default function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const navigate = useNavigate();

  function onSubmit(e) {
    e.preventDefault();
    // mock: go to home
    navigate("/");
  }

  return (
    <div className="login-page">
      <div className="login-card">
        <img src="/poshboard.png" alt="Poshboard" className="login-logo" />

        <form onSubmit={onSubmit} className="login-form">
          <label>
            Email
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="seu@exemplo.com"
            />
          </label>
          <label>
            Senha
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="********"
            />
          </label>

          <div className="actions">
            <button className="btn btn-primary" type="submit">
              Entrar
            </button>
          </div>
        </form>

        <div className="divider">ou</div>

        <button className="btn btn-sso" type="button">
          Entrar com SSO institucional
        </button>
      </div>
    </div>
  );
}
