export default function StudentCard({ student = {} }) {
  const name = String(student.name || student.nome || "").trim();

  const researchList = Array.isArray(student.research)
    ? student.research
    : student.research
    ? [student.research]
    : [];

  const initials = name
    ? name
        .split(/\s+/)
        .filter(Boolean)
        .map((n) => n[0])
        .slice(0, 2)
        .join("")
        .toUpperCase()
    : "--";

  return (
    <div className="teacher-card">
      <div className="card-left">
        <div className="avatar">{initials}</div>
      </div>
      <div className="card-body">
        <div className="card-title">{name || "—"}</div>
        <div className="badges">
          {researchList.map((r) => (
            <span key={r} className="badge">
              {r}
            </span>
          ))}
        </div>
        <div className="meta">
          {student.advisor && <span>Orientador: {student.advisor}</span>}
          {student.entryDate && <span>  Ingresso: {student.entryDate}</span>}
          {student.qualifDate && (
            <span>  Qualificação: {student.qualifDate}</span>
          )}
          {student.defenseDate && <span>  Defesa: {student.defenseDate}</span>}
        </div>
      </div>
    </div>
  );
}
