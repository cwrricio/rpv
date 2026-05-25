import { useState } from "react";
import { useStudents } from "../../components/student/StudentContext";

const RESEARCH_LINES = [
  "Inteligência Artificial",
  "Sistemas Embarcados",
  "Redes de Computadores",
  "Engenharia de Software",
  "Ciência de Dados",
];

export default function StudentForm() {
  const { showForm, addStudent, setShowForm } = useStudents();
  const [form, setForm] = useState({
    name: "",
    advisor: "",
    research: RESEARCH_LINES[0],
    entryDate: "",
    qualifDate: "",
    defenseDate: "",
  });

  function handleChange(e) {
    const { name, value } = e.target;
    setForm((f) => ({ ...f, [name]: value }));
  }

  function handleSave(e) {
    e.preventDefault();
    addStudent({
      name: form.name || "Sem nome",
      advisor: form.advisor,
      research: form.research,
      entryDate: form.entryDate,
      qualifDate: form.qualifDate,
      defenseDate: form.defenseDate,
    });
    setForm({
      name: "",
      advisor: "",
      research: RESEARCH_LINES[0],
      entryDate: "",
      qualifDate: "",
      defenseDate: "",
    });
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
          placeholder="Nome completo"
        />
      </div>

      <div className="form-row">
        <label>Orientador</label>
        <input
          name="advisor"
          value={form.advisor}
          onChange={handleChange}
          placeholder="Nome do orientador"
        />
      </div>

      <div className="form-row">
        <label>Linha de Pesquisa</label>
        <select name="research" value={form.research} onChange={handleChange}>
          {RESEARCH_LINES.map((r) => (
            <option key={r} value={r}>
              {r}
            </option>
          ))}
        </select>
      </div>

      <div className="form-row-grid-3">
        <div className="small-field">
          <label>Data de Ingresso</label>
          <input
            name="entryDate"
            value={form.entryDate}
            onChange={handleChange}
            placeholder="dd/mm/aaaa"
          />
        </div>
        <div className="small-field">
          <label>Data de Qualificação</label>
          <input
            name="qualifDate"
            value={form.qualifDate}
            onChange={handleChange}
            placeholder="dd/mm/aaaa"
          />
        </div>
        <div className="small-field">
          <label>Data de Defesa</label>
          <input
            name="defenseDate"
            value={form.defenseDate}
            onChange={handleChange}
            placeholder="dd/mm/aaaa"
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
