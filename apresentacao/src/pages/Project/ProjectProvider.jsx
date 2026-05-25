import { createContext, useContext, useState, useEffect } from "react";

const ProjectContext = createContext(null);
export const useProjects = () => useContext(ProjectContext);

export default function ProjectProvider({ children }) {
  const [projects, setProjects] = useState([]);
  const [showForm, setShowForm] = useState(false);

  const API = (import.meta.env.VITE_API_URL || "http://127.0.0.1:8000").replace(
    /\/$/,
    ""
  );

  useEffect(() => {
    let mounted = true;
    async function load() {
      try {
        const res = await fetch(`${API}/projetos`);
        if (!res.ok) return setProjects([]);
        const json = await res.json();
        const arr = Array.isArray(json)
          ? json
          : Object.keys(json || {})
              .filter((k) => k !== "_")
              .map((k) => ({ id: k, ...json[k] }));
        if (mounted) setProjects(arr);
      } catch (e) {
        if (mounted) setProjects([]);
      }
    }
    load();
    return () => (mounted = false);
  }, []);

  async function addProject(payload) {
    const res = await fetch(`${API}/projetos`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error("Erro ao criar projeto");
    // re-list
    const r2 = await fetch(`${API}/projetos`);
    const json2 = await r2.json();
    const arr = Array.isArray(json2)
      ? json2
      : Object.keys(json2 || {})
          .filter((k) => k !== "_")
          .map((k) => ({ id: k, ...json2[k] }));
    setProjects(arr);
  }

  async function updateProject(id, patch) {
    const res = await fetch(`${API}/projetos/${encodeURIComponent(id)}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(patch),
    });
    if (!res.ok) throw new Error("Falha ao atualizar projeto");
    const updated = await res.json();
    setProjects((p) =>
      p.map((x) => (String(x.id) === String(id) ? updated : x))
    );
    return updated;
  }

  async function deleteProject(id) {
    const res = await fetch(`${API}/projetos/${encodeURIComponent(id)}`, {
      method: "DELETE",
    });
    if (!res.ok) throw new Error("Falha ao apagar projeto");
    setProjects((p) => p.filter((x) => String(x.id) !== String(id)));
    return true;
  }

  return (
    <ProjectContext.Provider
      value={{
        projects,
        addProject,
        updateProject,
        deleteProject,
        showForm,
        setShowForm,
      }}
    >
      {children}
    </ProjectContext.Provider>
  );
}
