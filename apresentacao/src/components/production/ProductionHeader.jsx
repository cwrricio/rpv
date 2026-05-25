import { useProductions } from "../../pages/Production/ProductionProvider";

export default function ProductionHeader() {
  const { showForm, setShowForm } = useProductions();
  return (
    <div className="teacher-header">
      <h1>Produção</h1>
      <button className="btn-primary" onClick={() => setShowForm((s) => !s)}>
        {showForm ? "Cancelar" : "Adicionar registro"}
      </button>
    </div>
  );
}
