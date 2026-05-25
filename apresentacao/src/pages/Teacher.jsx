import TeacherProvider from "./teacher/TeacherProvider";
import TeacherHeader from "../components/teacher/TeacherHeader";
import TeacherForm from "../components/teacher/TeacherForm";
import TeacherList from "../components/teacher/TeacherList";
import "./Teacher.css";

export default function Teacher() {
    return (
        <TeacherProvider>
            <div className="teacher-page">
                <TeacherHeader />
                <TeacherForm />
                <TeacherList />
            </div>
        </TeacherProvider>
    );
}