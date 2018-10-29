import * as uuidv4 from "uuid/v4";

export interface IVehicleResponse {
  unique_id: string;
  type: "car" | "scooter";
  provider_id: string;
  current: {
    position: { lat: number; lng: number };
  };
}

export interface IVehicleDetailResponse {
  unique_id: string;
  type: "car" | "scooter";
  provider_id: string;
  current: {
    position: { lat: number; lng: number };
  };
}

export interface IVehiclesResponse {
  vehicles: IVehicleResponse[];
}

const LADOT = [34.0513838, -118.245173];
function randomPosition() {
  return {
    lat: LADOT[0] + (0.5 - Math.random()) * 0.2,
    lng: LADOT[1] + (0.5 - Math.random()) * 0.2
  };
}

function randomVehicle(): IVehicleResponse {
  if (Math.random() > 0.9) {
    return {
      current: {
        position: randomPosition()
      },
      provider_id: "bluela",
      type: "car",
      unique_id: uuidv4()
    };
  }

  return {
    current: {
      position: randomPosition()
    },
    provider_id: Math.random() > 0.5 ? "bird" : "lime",
    type: "scooter",
    unique_id: uuidv4()
  };
}

export async function getVehicles(requestBody: {}): Promise<IVehiclesResponse> {
  // TODO
  // For now, mock data

  const vehicles = [];
  for (let i = 0; i < 200; i++) {
    vehicles.push(randomVehicle());
  }

  return Promise.resolve({ vehicles });
}

export async function getVehicleDetail(
  vehicleId: string
): Promise<IVehicleDetailResponse> {
  return randomVehicle();
}
