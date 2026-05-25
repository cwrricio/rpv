import { useTeachers } from "../../pages/teacher/TeacherProvider";

export default function TeacherHeader() {
  const { showForm, setShowForm } = useTeachers();
  return (
    <div className="teacher-header">
      <h1>Docentes</h1>
      <button className="btn-primary" onClick={() => setShowForm((s) => !s)}>
        {showForm ? "Cancelar" : "Adicionar docente"}
      </button>
    </div>
  );
}
