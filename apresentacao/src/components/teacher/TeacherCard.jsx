export default function TeacherCard({ teacher }) {
  // defensive: if teacher is not provided, render nothing
  if (!teacher) return null;

  const researchList = Array.isArray(teacher.research)
    ? teacher.research
    : teacher.research
    ? [teacher.research]
    : [];

  const displayName =
    teacher.name || teacher.nome || teacher.label || teacher.display_name || "";

  const initials = (
    String(displayName)
      .split(/\s+/)
      .filter(Boolean)
      .map((n) => n[0])
      .slice(0, 2)
      .join("") || (teacher.id ? String(teacher.id).slice(0, 2) : "")
  ).toUpperCase();

  return (
    <div className="teacher-card">
      <div className="card-left">
        <div className="avatar">{initials}</div>
      </div>
      <div className="card-body">
        <div className="card-title">{displayName || teacher.id || "—"}</div>
        <div className="badges">
          {researchList.map((r) => (
            <span key={r} className="badge">
              {r}
            </span>
          ))}
        </div>
        <div className="meta">
          {teacher.lattes && (
            <a href={teacher.lattes} target="_blank" rel="noreferrer">
              Lattes
            </a>
          )}
          {teacher.orcid && <span> · ORCID: {teacher.orcid}</span>}

          {teacher.citations !== undefined && (
            <span> · Citações: {teacher.citations}</span>
          )}
          {teacher.citations5 !== undefined && (
            <span> · Citações (5y): {teacher.citations5}</span>
          )}

          {teacher.hIndex !== undefined && <span> · H: {teacher.hIndex}</span>}
          {teacher.h5Index !== undefined && (
            <span> · H5: {teacher.h5Index}</span>
          )}
        </div>
      </div>
    </div>
  );
}
