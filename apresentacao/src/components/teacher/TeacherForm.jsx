import { useState } from "react";
import { useTeachers } from "../../pages/teacher/TeacherProvider";

const RESEARCH_LINES = [
  "Inteligência Artificial",
  "Sistemas Embarcados",
  "Redes de Computadores",
  "Engenharia de Software",
  "Ciência de Dados",
];

export default function TeacherForm() {
  const { showForm, addTeacher, setShowForm } = useTeachers();
  const [form, setForm] = useState({
    name: "",
    research: RESEARCH_LINES[0],
    lattes: "",
    orcid: "",
    scholar: "",
    instagram: "",
    linkedin: "",
    hIndex: "",
    h5Index: "",
  });

  function handleChange(e) {
    const { name, value } = e.target;
    setForm((f) => ({ ...f, [name]: value }));
  }

  function handleSave(e) {
    e.preventDefault();
    addTeacher({
      name: form.name || "Sem nome",
      research: form.research,
      lattes: form.lattes,
      orcid: form.orcid,
      scholar: form.scholar,
      instagram: form.instagram,
      linkedin: form.linkedin,
      hIndex: form.hIndex,
      h5Index: form.h5Index,
    });
    setForm({
      name: "",
      research: RESEARCH_LINES[0],
      lattes: "",
      orcid: "",
      scholar: "",
      instagram: "",
      linkedin: "",
      hIndex: "",
      h5Index: "",
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
        <label>Linha de Pesquisa</label>
        <select name="research" value={form.research} onChange={handleChange}>
          {RESEARCH_LINES.map((r) => (
            <option key={r} value={r}>
              {r}
            </option>
          ))}
        </select>
      </div>

      <div className="form-row">
        <label>URL do Lattes</label>
        <input
          name="lattes"
          value={form.lattes}
          onChange={handleChange}
          placeholder="https://lattes.cnpq.br/..."
        />
      </div>

      <div className="form-row">
        <label>ORCID</label>
        <input
          name="orcid"
          value={form.orcid}
          onChange={handleChange}
          placeholder="0000-0000-0000-0000"
        />
      </div>

      <div className="form-row-grid-3">
        <div className="small-field">
          <label>Google Scholar</label>
          <input
            name="scholar"
            value={form.scholar}
            onChange={handleChange}
            placeholder="URL do Scholar"
          />
        </div>
        <div className="small-field">
          <label>Instagram</label>
          <input
            name="instagram"
            value={form.instagram}
            onChange={handleChange}
            placeholder="@usuario ou URL"
          />
        </div>
        <div className="small-field">
          <label>LinkedIn</label>
          <input
            name="linkedin"
            value={form.linkedin}
            onChange={handleChange}
            placeholder="URL do LinkedIn"
          />
        </div>
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
