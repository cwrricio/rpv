import { useState } from "react";
import { useProjects } from "../../pages/project/ProjectProvider";
import { useTeachers } from "../../components/teacher/TeacherContext";
import { useStudents } from "../../components/student/StudentContext";
import SearchSelect from "../ui/SearchSelect";

const RESEARCH_LINES = [
  "Inteligência Artificial",
  "Sistemas Embarcados",
  "Redes de Computadores",
  "Engenharia de Software",
  "Ciência de Dados",
];

export default function ProjectForm() {
  const { showForm, addProject, setShowForm } = useProjects() || {};
  const { teachers = [] } = useTeachers() || {};
  const { students = [] } = useStudents() || {};

  const [form, setForm] = useState({
    name: "",
    research: RESEARCH_LINES[0],
    coordinator: null,
    teachers: [],
    students: [],
  });

  function handleSave(e) {
    e.preventDefault();
    addProject({
      name: form.name || "Sem nome",
      research: form.research,
      coordinator: form.coordinator,
      teachers: form.teachers,
      students: form.students,
    });
    setForm({
      name: "",
      research: RESEARCH_LINES[0],
      coordinator: null,
      teachers: [],
      students: [],
    });
    setShowForm(false);
  }

  if (!showForm) return null;

  return (
    <form className="teacher-form" onSubmit={handleSave}>
      <div className="form-row">
        <label>Nome do projeto</label>
        <input
          name="name"
          value={form.name}
          onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
          placeholder="Nome do projeto"
        />
      </div>

      <div className="form-row">
        <label>Linha de Pesquisa</label>
        <select
          value={form.research}
          onChange={(e) => setForm((f) => ({ ...f, research: e.target.value }))}
        >
          {RESEARCH_LINES.map((r) => (
            <option key={r} value={r}>
              {r}
            </option>
          ))}
        </select>
      </div>

      <div className="form-row">
        <label>Coordenador</label>
        <SearchSelect
          items={teachers.map((t) => ({
            id: t.id,
            name: t.name || t.nome || t.display_name || "",
          }))}
          multiple={false}
          placeholder="Pesquisar docente"
          onChange={(v) => setForm((f) => ({ ...f, coordinator: v }))}
        />
      </div>

      <div className="form-row">
        <label>Membros docentes</label>
        <SearchSelect
          items={teachers.map((t) => ({
            id: t.id,
            name: t.name || t.nome || t.display_name || "",
          }))}
          multiple={true}
          placeholder="Pesquisar docentes"
          onChange={(v) => setForm((f) => ({ ...f, teachers: v }))}
        />
      </div>

      <div className="form-row">
        <label>Membros discentes</label>
        <SearchSelect
          items={students.map((s) => ({
            id: s.id,
            name: s.name || s.nome || s.display_name || "",
          }))}
          multiple={true}
          placeholder="Pesquisar discentes"
          onChange={(v) => setForm((f) => ({ ...f, students: v }))}
        />
      </div>

      <div className="form-actions">
        <button type="submit" className="btn-primary">
          Salvar
        </button>
      </div>
    </form>
  );
}
