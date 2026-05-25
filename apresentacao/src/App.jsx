import {
  BrowserRouter as Router,
  Routes,
  Route,
  useLocation,
} from "react-router-dom";
import { useState } from "react";
import reactLogo from "./assets/react.svg";
import viteLogo from "/vite.svg"; 
import Sidebar from "./components/Sidebar";
import Login from "./pages/Login";
import Home from "./pages/Home";
import Teacher from "./pages/Teacher";
import Student from "./pages/Student";
import Project from "./pages/Project";
import Production from "./pages/Production";
import Vehicle from "./pages/Vehicle";
import Report from "./pages/Report";
import RelatorioProducao from "./pages/RelatorioProducao";
import Header from "./components/Header";
import Footer from "./components/Footer";
import "./App.css";
import Qualis from "./pages/Qualis/Qualis"; 

function AppInner() {
  const location = useLocation();
  const [count, setCount] = useState(0);
  const isLogin = location.pathname === "/login";

  return (
    <div style={{ display: "flex" }}>
      {!isLogin && <Sidebar />}
      <div
        style={{
          flex: 1,
          padding: "2rem",
          marginLeft: !isLogin ? "200px" : 0,
          paddingBottom: "84px",
        }}
      >
        {!isLogin && <Header />}
        <div style={{ paddingTop: !isLogin ? 64 : 0 }}>
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/login" element={<Login />} />
            <Route path="/teacher" element={<Teacher />} />
            <Route path="/student" element={<Student />} />
            <Route path="/project" element={<Project />} />
            <Route path="/production" element={<Production />} />
            <Route path="/vehicle" element={<Vehicle />} />
            <Route path="/reports" element={<Report />} />
            <Route path="/relatorio-producao" element={<RelatorioProducao />} />
            <Route path="/qualis" element={<Qualis />} />
          </Routes>
          {!isLogin && <Footer />}
        </div>
      </div>
    </div>
  );
}

function App() {
  return (
    <Router>
      <AppInner />
    </Router>
  );
}

export default App;