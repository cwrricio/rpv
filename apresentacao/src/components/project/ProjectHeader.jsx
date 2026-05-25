import { useProjects } from "../../pages/project/ProjectProvider";

export default function ProjectHeader() {
  const ctx = useProjects() || {};
  const { showForm = false, setShowForm = () => {} } = ctx;
  return (
    <div className="teacher-header">
      <h1>Projetos</h1>
      <button
        className="btn-primary"
        onClick={() => {
          console.debug(
            "ProjectHeader: botão Adicionar clicado. showForm=",
            showForm
          );
          setShowForm((s) => !s);
        }}
      >
        {showForm ? "Cancelar" : "Adicionar projeto"}
      </button>
    </div>
  );
}
