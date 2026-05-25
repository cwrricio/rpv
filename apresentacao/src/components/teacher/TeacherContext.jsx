import { createContext, useContext, useState, useEffect } from "react";

const TeacherContext = createContext(null);
export const useTeachers = () => useContext(TeacherContext);

function normalizeDocentes(raw) {
  if (!raw) return [];
  if (Array.isArray(raw)) {
    return raw.map((d) => ({
      id: d.id || d._id || d.key,
      name: d.nome || d.name || d.display_name || "--",
      orcid: d.orcid || "",
      lattes: d.lattes || "",
      hIndex: d.hIndex || d.h_index || undefined,
      citations: d.citations || d.cited_by_count || undefined,
      works: d.works || null,
      raw: d,
    }));
  }
  return Object.keys(raw)
    .filter((k) => k !== "_")
    .map((k) => {
      const a = raw[k] || {};
      return {
        id: a.id || k,
        name: a.nome || a.name || a.display_name || "--",
        orcid: a.orcid || "",
        lattes: a.lattes || "",
        hIndex: a.hIndex || a.h_index || undefined,
        citations:
          a.cited_by_count ||
          a.citations ||
          a.metrics?.cited_by_count ||
          undefined,
        works: a.works || a.work || a.publications || null,
        raw: a,
      };
    });
}

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
        const arr = normalizeDocentes(json);
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
    // re-lista
    const r2 = await fetch(`${API}/docentes`);
    const json2 = await r2.json();
    setTeachers(normalizeDocentes(json2));
  }

  async function updateTeacher(id, patch) {
    const res = await fetch(`${API}/docentes/${encodeURIComponent(id)}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(patch),
    });
    if (!res.ok) throw new Error("Falha ao atualizar docente");
    const updated = await res.json();
    setTeachers((t) =>
      t.map((x) => (String(x.id) === String(id) ? updated : x))
    );
    return updated;
  }

  async function deleteTeacher(id) {
    const res = await fetch(`${API}/docentes/${encodeURIComponent(id)}`, {
      method: "DELETE",
    });
    if (!res.ok) throw new Error("Falha ao apagar docente");
    setTeachers((t) => t.filter((x) => String(x.id) !== String(id)));
    return true;
  }

  return (
    <TeacherContext.Provider
      value={{
        teachers,
        addTeacher,
        updateTeacher,
        deleteTeacher,
        showForm,
        setShowForm,
      }}
    >
      {children}
    </TeacherContext.Provider>
  );
}
