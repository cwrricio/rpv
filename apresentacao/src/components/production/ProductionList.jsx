import ProductionCard from "./ProductionCard";
import { useProductions } from "../../pages/Production/ProductionProvider";

export default function ProductionList() {
  const { productions } = useProductions();
  return (
    <div className="teacher-list">
      {productions.map((p) => (
        <ProductionCard key={p.id} production={p} />
      ))}
    </div>
  );
}
