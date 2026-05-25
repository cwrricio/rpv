import ProjectProvider from "./project/ProjectProvider";
import ProjectHeader from "../components/project/ProjectHeader";
import ProjectForm from "../components/project/ProjectForm";
import ProjectList from "../components/project/ProjectList";
import "./Project.css";
import TeacherProvider from "../components/teacher/TeacherContext";
import StudentProvider from "../components/student/StudentContext";

export default function Project() {
  return (
    <TeacherProvider>
      <StudentProvider>
        <ProjectProvider>
          <div className="teacher-page">
            <ProjectHeader />
            <ProjectForm />
            <ProjectList />
          </div>
        </ProjectProvider>
      </StudentProvider>
    </TeacherProvider>
  );
}
