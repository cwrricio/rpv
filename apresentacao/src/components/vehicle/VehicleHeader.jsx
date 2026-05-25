import { useVehicles } from "../../pages/Vehicle/VehicleProvider";

export default function VehicleHeader() {
  const { showForm, setShowForm } = useVehicles();
  return (
    <div className="teacher-header">
      <h1>Veículos</h1>
      <button className="btn-primary" onClick={() => setShowForm((s) => !s)}>
        {showForm ? "Cancelar" : "Adicionar veículo"}
      </button>
    </div>
  );
}
