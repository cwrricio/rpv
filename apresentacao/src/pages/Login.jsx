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

        <button className="btn btn-google" type="button">
          <svg
            width="18"
            height="18"
            viewBox="0 0 24 24"
            xmlns="http://www.w3.org/2000/svg"
          >
            <path
              d="M21.35 11.1H12v2.8h5.35c-.23 1.48-1.44 3.5-5.35 3.5-3.22 0-5.85-2.65-5.85-5.92s2.63-5.92 5.85-5.92c1.84 0 3.08.78 3.78 1.45l2.6-2.5C17.93 3.07 15.73 2 12 2 6.48 2 2 6.5 2 12s4.48 10 10 10c5.77 0 9.66-4.04 9.66-9.84 0-.66-.07-1.16-.31-1.96z"
              fill="none"
            />
            <g>
              <path
                d="M21.6 12.227c0-.714-.064-1.4-.182-2.064H12v3.912h5.66c-.244 1.32-.98 2.442-2.09 3.203v2.664h3.378c1.976-1.82 3.114-4.496 3.114-7.715z"
                fill="#4285F4"
              />
              <path
                d="M12 22c2.7 0 4.964-.9 6.652-2.438l-3.378-2.664c-.938.632-2.126 1.008-3.274 1.008-2.516 0-4.648-1.696-5.41-3.976H2.957v2.494C4.65 19.884 8.06 22 12 22z"
                fill="#34A853"
              />
              <path
                d="M6.59 13.93A6.002 6.002 0 016 12c0-.68.09-1.336.273-1.93V7.576H2.957A9.99 9.99 0 002 12c0 1.62.388 3.152 1.07 4.536l3.52-2.606z"
                fill="#FBBC05"
              />
              <path
                d="M12 6.5c1.47 0 2.8.504 3.85 1.49l2.89-2.89C16.95 3.47 14.69 2.5 12 2.5 8.06 2.5 4.65 4.616 2.957 7.576L6.59 10c.762-2.28 2.894-3.976 5.41-3.976z"
                fill="#EA4335"
              />
            </g>
          </svg>
          Entrar com Google
        </button>
      </div>
    </div>
  );
}
