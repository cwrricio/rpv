import ProductionProvider from "./Production/ProductionProvider";
import ProductionHeader from "../components/production/ProductionHeader";
import ProductionForm from "../components/production/ProductionForm";
import ProductionList from "../components/production/ProductionList";
import "./Production.css";

export default function Production() {
  return (
    <ProductionProvider>
      <div className="teacher-page">
        <ProductionHeader />
        <ProductionForm />
        <ProductionList />
      </div>
    </ProductionProvider>
  );
}
