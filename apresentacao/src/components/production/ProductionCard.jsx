export default function ProductionCard({ production }) {
  const display =
    (production &&
      (production.type ||
        production.title ||
        production.nome ||
        production.titulo ||
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
    production?.title ||
    production?.type ||
    production?.titulo ||
    production?.nome ||
    "Sem título";

  return (
    <div className="teacher-card">
      <div className="card-left">
        <div className="avatar">{initials}</div>
      </div>
      <div className="card-body">
        <div className="card-title">{title}</div>
        <div className="badges">
          <span className="badge">{production?.type}</span>
        </div>
        <div className="meta">
          {production?.authors && <span>{production.authors}</span>}
          {production?.year && <span> · {production.year}</span>}
          {production?.vehicle && <span> · {production.vehicle}</span>}
          {production?.url && (
            <span>
              {" "}
              ·{" "}
              <a href={production.url} target="_blank" rel="noreferrer">
                Link
              </a>
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
