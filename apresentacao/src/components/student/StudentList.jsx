import StudentCard from "./StudentCard";
import { useStudents } from "../../components/student/StudentContext";

export default function StudentList() {
  const { students } = useStudents();

  return (
    <div className="teacher-list">
      {students.map((s) => (
        <StudentCard key={s.id} student={s} />
      ))}
    </div>
  );
}
