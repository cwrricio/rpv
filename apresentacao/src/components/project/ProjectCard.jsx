export default function ProjectCard({ project }) {
  const display =
    (project &&
      (project.name ||
        project.title ||
        project.nome ||
        project.titulo ||
        "")) ||
    "";
  const initials = display
    ? display
        .split(" ")
        .map((n) => (n && n[0]) || "")
        .slice(0, 2)
        .join("")
        .toUpperCase()
    : "--";

  const title =
    (project &&
      (project.name || project.title || project.nome || project.titulo)) ||
    "Sem nome";

  const research =
    project?.research || project?.linha || project?.linha_de_pesquisa || "";

  const coordName =
    project?.coordinator?.name ||
    project?.coordinator?.nome ||
    (typeof project?.coordinator === "string" ? project.coordinator : null);

  const teachersList = (project?.teachers || []).map(
    (t) =>
      (t && (t.name || t.nome || t.label || t.display_name)) || String(t || "")
  );

  const studentsList = (project?.students || []).map(
    (s) =>
      (s && (s.name || s.nome || s.label || s.display_name)) || String(s || "")
  );

  return (
    <div className="teacher-card">
      <div className="card-left">
        <div className="avatar">{initials}</div>
      </div>
      <div className="card-body">
        <div className="card-title">{title}</div>
        <div className="badges">
          <span className="badge">{research}</span>
        </div>
        <div className="meta">
          {coordName && <span>Coordenador: {coordName}</span>}
          {teachersList.length > 0 && (
            <span> · Docentes: {teachersList.join(", ")}</span>
          )}
          {studentsList.length > 0 && (
            <span> · Discentes: {studentsList.join(", ")}</span>
          )}
        </div>
      </div>
    </div>
  );
}
