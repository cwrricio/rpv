import VehicleProvider from "./Vehicle/VehicleProvider";
import VehicleHeader from "../components/vehicle/VehicleHeader";
import VehicleForm from "../components/vehicle/VehicleForm";
import VehicleList from "../components/vehicle/VehicleList";
import "./Vehicle.css";

export default function Vehicle() {
  return (
    <VehicleProvider>
      <div className="teacher-page">
        <VehicleHeader />
        <VehicleForm />
        <VehicleList />
      </div>
    </VehicleProvider>
  );
}
