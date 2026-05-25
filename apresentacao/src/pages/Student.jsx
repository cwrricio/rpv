import StudentProvider from "./student/StudentProvider";
import StudentHeader from "../components/student/StudentHeader";
import StudentForm from "../components/student/StudentForm";
import StudentList from "../components/student/StudentList";
import "./Teacher.css";

export default function Student() {
  return (
    <StudentProvider>
      <div className="teacher-page">
        <StudentHeader />
        <StudentForm />
        <StudentList />
      </div>
    </StudentProvider>
  );
}
