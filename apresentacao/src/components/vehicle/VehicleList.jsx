import VehicleCard from "./VehicleCard";
import { useVehicles } from "../../pages/Vehicle/VehicleProvider";

export default function VehicleList() {
  const { vehicles } = useVehicles();
  return (
    <div className="teacher-list">
      {vehicles.map((v) => (
        <VehicleCard key={v.id} vehicle={v} />
      ))}
    </div>
  );
}
