import { Link } from "react-router-dom";
import "../assets/styles/sidebar.css";

const Icon = ({ name }) => {
  switch (name) {
    case "home":
      return (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
          <path
            d="M3 10.5L12 3l9 7.5"
            stroke="currentColor"
            strokeWidth="1.6"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
          <path
            d="M5 21V11h14v10"
            stroke="currentColor"
            strokeWidth="1.6"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      );
    case "teacher":
      return (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
          <path
            d="M12 12a4 4 0 100-8 4 4 0 000 8z"
            stroke="currentColor"
            strokeWidth="1.6"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
          <path
            d="M4 21a8 8 0 0116 0"
            stroke="currentColor"
            strokeWidth="1.6"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      );
    case "student":
      return (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
          <path
            d="M12 2l8 4-8 4-8-4 8-4z"
            stroke="currentColor"
            strokeWidth="1.4"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
          <path
            d="M4 10v6a8 8 0 008 8 8 8 0 008-8v-6"
            stroke="currentColor"
            strokeWidth="1.4"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      );
    case "project":
      return (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
          <rect
            x="3"
            y="7"
            width="18"
            height="12"
            rx="2"
            stroke="currentColor"
            strokeWidth="1.6"
          />
          <path
            d="M7 7V5a2 2 0 012-2h6a2 2 0 012 2v2"
            stroke="currentColor"
            strokeWidth="1.6"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      );
    case "production":
      return (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
          <circle cx="12" cy="12" r="3" stroke="currentColor" strokeWidth="1.6" />
          <path
            d="M19.4 15a7 7 0 10-14.8 0"
            stroke="currentColor"
            strokeWidth="1.6"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      );
    case "qualis":
      return (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
          <rect
            x="3"
            y="3"
            width="18"
            height="18"
            rx="2"
            stroke="currentColor"
            strokeWidth="1.6"
          />
          <path
            d="M8 8h8M8 12h8M8 16h8"
            stroke="currentColor"
            strokeWidth="1.6"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      );
    case "vehicle":
      return (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
          <rect
            x="3"
            y="11"
            width="18"
            height="6"
            rx="2"
            stroke="currentColor"
            strokeWidth="1.6"
          />
          <circle cx="7.5" cy="18" r="1.5" stroke="currentColor" strokeWidth="1.6" />
          <circle cx="16.5" cy="18" r="1.5" stroke="currentColor" strokeWidth="1.6" />
        </svg>
      );
    case "reports":
      return (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
          <path
            d="M9 17H7a2 2 0 01-2-2V7a2 2 0 012-2h6l6 6v4"
            stroke="currentColor"
            strokeWidth="1.6"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
          <path
            d="M9 9h6M9 13h3"
            stroke="currentColor"
            strokeWidth="1.6"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      );
    case "info":
      return (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
          <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="1.6" />
          <path
            d="M12 8v.01"
            stroke="currentColor"
            strokeWidth="1.6"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
          <path
            d="M11 12h1v4h1"
            stroke="currentColor"
            strokeWidth="1.6"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      );
    case "logout":
      return (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
          <path
            d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4"
            stroke="currentColor"
            strokeWidth="1.6"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
          <path
            d="M16 17l5-5-5-5"
            stroke="currentColor"
            strokeWidth="1.6"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
          <path
            d="M21 12H9"
            stroke="currentColor"
            strokeWidth="1.6"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      );
    default:
      return null;
  }
};

const Sidebar = () => (
  <nav className="sidebar">
    <div className="sidebar-top">
      <div className="logo-wrap">
        <img src="/poshboard.png" alt="Poshboard" className="sidebar-logo" />
      </div>
    </div>

    <ul className="sidebar-list">
      <li>
        <Link to="/">
          <span className="sb-icon"><Icon name="home" /></span>
          <span>Home</span>
        </Link>
      </li>
      <li>
        <Link to="/teacher">
          <span className="sb-icon"><Icon name="teacher" /></span>
          <span>Professor</span>
        </Link>
      </li>
      <li>
        <Link to="/student">
          <span className="sb-icon"><Icon name="student" /></span>
          <span>Estudante</span>
        </Link>
      </li>
      <li>
        <Link to="/project">
          <span className="sb-icon"><Icon name="project" /></span>
          <span>Projeto</span>
        </Link>
      </li>
      <li>
        <Link to="/production">
          <span className="sb-icon"><Icon name="production" /></span>
          <span>Produção</span>
        </Link>
      </li>
      <li>
        <Link to="/qualis">
          <span className="sb-icon"><Icon name="qualis" /></span>
          <span>Qualis</span>
        </Link>
      </li>
      <li>
        <Link to="/vehicle">
          <span className="sb-icon"><Icon name="vehicle" /></span>
          <span>Veículo</span>
        </Link>
      </li>
      <li>
        <Link to="/reports">
          <span className="sb-icon"><Icon name="reports" /></span>
          <span>Relatórios</span>
        </Link>
      </li>
      <li>
        <Link to="/relatorio-producao">
          <span className="sb-icon">
            <Icon name="production" />
          </span>
          <span>Relatórios Produções</span>
        </Link>
      </li>
    </ul>

    <ul className="sidebar-bottom">
      <li>
        <Link to="/about">
          <span className="sb-icon"><Icon name="info" /></span>
          <span>Sobre</span>
        </Link>
      </li>
      <li>
        <a
          href="#"
          onClick={(e) => {
            e.preventDefault();
            alert("Sair (mock)");
          }}
        >
          <span className="sb-icon"><Icon name="logout" /></span>
          <span>Sair</span>
        </a>
      </li>
    </ul>
  </nav>
);

export default Sidebar;
