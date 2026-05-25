import { useState } from "react";
import { useProductions } from "../../pages/Production/ProductionProvider";

export default function ProductionForm() {
  const { showForm, addProduction, setShowForm } = useProductions();
  const [form, setForm] = useState({
    type: "",
    authors: "",
    title: "",
    year: "",
    vehicle: "",
    url: "",
  });

  function handleChange(e) {
    const { name, value } = e.target;
    setForm((f) => ({ ...f, [name]: value }));
  }

  function handleSave(e) {
    e.preventDefault();
    addProduction({
      type: form.type || "Outro",
      authors: form.authors,
      title: form.title || "Sem título",
      year: form.year,
      vehicle: form.vehicle,
      url: form.url,
    });
    setForm({
      type: "",
      authors: "",
      title: "",
      year: "",
      vehicle: "",
      url: "",
    });
    setShowForm(false);
  }

  if (!showForm) return null;

  return (
    <form className="teacher-form" onSubmit={handleSave}>
      <div className="form-row">
        <label>Tipo</label>
        <input
          name="type"
          value={form.type}
          onChange={handleChange}
          placeholder="Artigo, Livro, Capítulo..."
        />
      </div>

      <div className="form-row">
        <label>Autores</label>
        <input
          name="authors"
          value={form.authors}
          onChange={handleChange}
          placeholder="Nome dos autores separados por vírgula"
        />
      </div>

      <div className="form-row">
        <label>Título</label>
        <input
          name="title"
          value={form.title}
          onChange={handleChange}
          placeholder="Título da produção"
        />
      </div>

      <div className="form-row-grid-3">
        <div className="small-field">
          <label>Ano</label>
          <input
            name="year"
            value={form.year}
            onChange={handleChange}
            placeholder="2024"
          />
        </div>
        <div className="small-field">
          <label>Veículo</label>
          <input
            name="vehicle"
            value={form.vehicle}
            onChange={handleChange}
            placeholder="Nome do periódico/conferência"
          />
        </div>
        <div className="small-field">
          <label>URL</label>
          <input
            name="url"
            value={form.url}
            onChange={handleChange}
            placeholder="https://..."
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
