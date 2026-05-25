export default function VehicleCard({ vehicle }) {
  const display =
    (vehicle &&
      (vehicle.name ||
        vehicle.title ||
        vehicle.nome ||
        vehicle.titulo ||
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
    (vehicle &&
      (vehicle.name || vehicle.title || vehicle.nome || vehicle.titulo)) ||
    "Sem nome";

  return (
    <div className="teacher-card">
      <div className="card-left">
        <div className="avatar">{initials}</div>
      </div>
      <div className="card-body">
        <div className="card-title">{title}</div>
        <div className="badges">
          {vehicle?.qualis && <span className="badge">{vehicle.qualis}</span>}
        </div>
        <div className="meta">
          {vehicle?.hIndex !== undefined && <span>H: {vehicle.hIndex}</span>}
          {vehicle?.h5Index !== undefined && (
            <span> · H5: {vehicle.h5Index}</span>
          )}
        </div>
      </div>
    </div>
  );
}
