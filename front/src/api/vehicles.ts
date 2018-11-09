export interface IVehicleResponse {
  unique_id: string;
  type: "car" | "scooter" | "bicycle";
  provider_id: string;
  current: {
    position: { lat: number; lng: number };
    status: "available" | "unavailable" | "reserved";
  };
}

export interface IVehicleDetailResponse {
  unique_id: string;
  type: "car" | "scooter" | "bicycle";
  provider_id: string;
  current: {
    position: { lat: number; lng: number };
    status: "available" | "unavailable" | "reserved";
  };
}

export interface IVehiclesResponse {
  vehicles: IVehicleResponse[];
}

const LADOT = [34.0513838, -118.245173];
function randomPosition() {
  return {
    lat: LADOT[0] + (0.5 - Math.random()) * 0.15 + Math.random() * 0.05,
    lng: LADOT[1] + (0.5 - Math.random()) * 0.15 + Math.random() * 0.05
  };
}

function randomVehicle(): IVehicleResponse {
  if (Math.random() > 0.9) {
    return {
      current: {
        position: randomPosition(),
        status:
          Math.random() > 0.3
            ? "available"
            : Math.random() > 0.3
            ? "reserved"
            : "unavailable"
      },
      provider_id: "BlueLA",
      type: "car",
      unique_id: `${Math.floor((Math.random() * 10 + Math.random()) * 1000)}`
    };
  }
  if (Math.random() > 0.2) {
    return {
      current: {
        position: randomPosition(),
        status:
          Math.random() > 0.3
            ? "available"
            : Math.random() > 0.3
            ? "reserved"
            : "unavailable"
      },
      provider_id: Math.random() > 0.5 ? "bird" : "lime",
      type: "scooter",
      unique_id: `${Math.floor((Math.random() * 10 + Math.random()) * 1000)}`
    };
  }
  return {
    current: {
      position: randomPosition(),
      status:
        Math.random() > 0.3
          ? "available"
          : Math.random() > 0.3
          ? "reserved"
          : "unavailable"
    },
    provider_id: "Metro Bike",
    type: "bicycle",
    unique_id: `${Math.floor((Math.random() * 10 + Math.random()) * 1000)}`
  };
}

const vehiclesStore = {};

export async function getVehicles(requestBody: {}): Promise<IVehiclesResponse> {
  // TODO
  // For now, mock data

  if (Object.keys(vehiclesStore).length === 0) {
    for (let i = 0; i < 200; i++) {
      const ve = randomVehicle();
      vehiclesStore[ve.unique_id] = ve;
    }
  }

  return Promise.resolve({
    vehicles: Object.keys(vehiclesStore).map(key => vehiclesStore[key])
  });
}

export async function getVehicleDetail(
  vehicleId: string
): Promise<IVehicleDetailResponse> {
  return vehiclesStore[vehicleId] || randomVehicle();
}
