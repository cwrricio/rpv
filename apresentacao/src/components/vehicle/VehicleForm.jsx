import { useState } from "react";
import { useVehicles } from "../../pages/Vehicle/VehicleProvider";

export default function VehicleForm() {
  const { showForm, addVehicle, setShowForm } = useVehicles();
  const [form, setForm] = useState({
    name: "",
    qualis: "",
    hIndex: "",
    h5Index: "",
  });

  function handleChange(e) {
    const { name, value } = e.target;
    setForm((f) => ({ ...f, [name]: value }));
  }

  function handleSave(e) {
    e.preventDefault();
    addVehicle({
      name: form.name || "Sem nome",
      qualis: form.qualis,
      hIndex: form.hIndex ? Number(form.hIndex) : undefined,
      h5Index: form.h5Index ? Number(form.h5Index) : undefined,
    });
    setForm({ name: "", qualis: "", hIndex: "", h5Index: "" });
    setShowForm(false);
  }

  if (!showForm) return null;

  return (
    <form className="teacher-form" onSubmit={handleSave}>
      <div className="form-row">
        <label>Nome</label>
        <input
          name="name"
          value={form.name}
          onChange={handleChange}
          placeholder="Nome do periódico/conferência"
        />
      </div>

      <div className="form-row">
        <label>Qualis</label>
        <input
          name="qualis"
          value={form.qualis}
          onChange={handleChange}
          placeholder="A1, A2, B1..."
        />
      </div>

      <div className="form-row-grid-2">
        <div className="small-field">
          <label>Índice-H</label>
          <input
            name="hIndex"
            value={form.hIndex}
            onChange={handleChange}
            type="number"
          />
        </div>
        <div className="small-field">
          <label>Índice H-5</label>
          <input
            name="h5Index"
            value={form.h5Index}
            onChange={handleChange}
            type="number"
          />
        </div>
      </div>

      <div className="form-actions">
        <button type="submit" className="btn-primary">
          Salvar
        </button>
      </div>
    </form>
  );
}
