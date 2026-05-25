import { createContext, useContext, useState, useEffect } from "react";

const StudentContext = createContext(null);
export const useStudents = () => useContext(StudentContext);

export default function StudentProvider({ children }) {
  const [students, setStudents] = useState([]);
  const [showForm, setShowForm] = useState(false);

  const API = (import.meta.env.VITE_API_URL || "http://127.0.0.1:8000").replace(
    /\/$/,
    ""
  );

  useEffect(() => {
    let mounted = true;
    async function load() {
      try {
        const res = await fetch(`${API}/discentes`);
        if (!res.ok) {
          setStudents([]);
          return;
        }
        const json = await res.json();
        const arr = Array.isArray(json)
          ? json
          : Object.keys(json || {})
              .filter((k) => k !== "_")
              .map((k) => ({ id: k, ...json[k] }));
        if (mounted) setStudents(arr);
      } catch (e) {
        if (mounted) setStudents([]);
      }
    }
    load();
    return () => (mounted = false);
  }, []);

  async function addStudent(payload) {
    const res = await fetch(`${API}/discentes`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error("Erro ao criar discente");
    const r2 = await fetch(`${API}/discentes`);
    const json2 = await r2.json();
    const arr = Array.isArray(json2)
      ? json2
      : Object.keys(json2 || {})
          .filter((k) => k !== "_")
          .map((k) => ({ id: k, ...json2[k] }));
    setStudents(arr);
  }

  async function updateStudent(id, patch) {
    const res = await fetch(`${API}/discentes/${encodeURIComponent(id)}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(patch),
    });
    if (!res.ok) throw new Error("Falha ao atualizar discente");
    const updated = await res.json();
    setStudents((s) =>
      s.map((x) => (String(x.id) === String(id) ? updated : x))
    );
    return updated;
  }

  async function deleteStudent(id) {
    const res = await fetch(`${API}/discentes/${encodeURIComponent(id)}`, {
      method: "DELETE",
    });
    if (!res.ok) throw new Error("Falha ao apagar discente");
    setStudents((s) => s.filter((x) => String(x.id) !== String(id)));
    return true;
  }

  return (
    <StudentContext.Provider
      value={{
        students,
        addStudent,
        updateStudent,
        deleteStudent,
        showForm,
        setShowForm,
      }}
    >
      {children}
    </StudentContext.Provider>
  );
}
