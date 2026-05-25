import { useStudents } from "../../components/student/StudentContext";

export default function StudentHeader() {
  const { showForm, setShowForm } = useStudents();
  return (
    <div className="teacher-header">
      <h1>Discentes</h1>
      <button className="btn-primary" onClick={() => setShowForm((s) => !s)}>
        {showForm ? "Cancelar" : "Adicionar discente"}
      </button>
    </div>
  );
}
