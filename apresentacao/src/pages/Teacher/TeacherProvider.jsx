import { createContext, useContext, useState, useEffect } from "react";

const TeacherContext = createContext(null);
export const useTeachers = () => useContext(TeacherContext);

export default function TeacherProvider({ children }) {
  const [teachers, setTeachers] = useState([]);
  const [showForm, setShowForm] = useState(false);

  const API = (import.meta.env.VITE_API_URL || "http://127.0.0.1:8000").replace(
    /\/$/,
    ""
  );

  useEffect(() => {
    let mounted = true;
    async function load() {
      try {
        const res = await fetch(`${API}/docentes`);
        if (!res.ok) {
          setTeachers([]);
          return;
        }
        const json = await res.json();
        const arr = Array.isArray(json)
          ? json
          : Object.keys(json || {})
              .filter((k) => k !== "_")
              .map((k) => ({ id: k, ...json[k] }));
        if (mounted) setTeachers(arr);
      } catch (e) {
        if (mounted) setTeachers([]);
      }
    }
    load();
    return () => (mounted = false);
  }, []);

  async function addTeacher(payload) {
    const res = await fetch(`${API}/docentes`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error("Erro ao criar docente");
    const r2 = await fetch(`${API}/docentes`);
    const json2 = await r2.json();
    const arr = Array.isArray(json2)
      ? json2
      : Object.keys(json2 || {})
          .filter((k) => k !== "_")
          .map((k) => ({ id: k, ...json2[k] }));
    setTeachers(arr);
  }

  return (
    <TeacherContext.Provider
      value={{ teachers, addTeacher, showForm, setShowForm }}
    >
      {children}
    </TeacherContext.Provider>
  );
}
