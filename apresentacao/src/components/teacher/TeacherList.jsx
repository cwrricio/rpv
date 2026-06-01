import TeacherCard from "./TeacherCard";
import { useTeachers } from "./TeacherContext";

export default function TeacherList() {
  const { teachers } = useTeachers();

  return (
    <div className="teacher-list">
      {teachers.map((t) => (
        <TeacherCard key={t.id} teacher={t} />
      ))}
    </div>
  );
}
