import ProjectCard from "./ProjectCard";
import { useProjects } from "../../pages/project/ProjectProvider";

export default function ProjectList() {
  const ctx = useProjects() || {};
  const { projects = [] } = ctx;
  return (
    <div className="teacher-list">
      {projects.map((p) => (
        <ProjectCard key={p.id} project={p} />
      ))}
    </div>
  );
}
