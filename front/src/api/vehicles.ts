import { prepRequest } from "./commons";

export interface IVehicleResponse {
  unique_id: string;
  type: "car" | "scooter" | "bicycle" | "car station" | "bicycle station";
  provider_id: string;
  current: {
    position: { lat: number; lng: number };
    status: "available" | "unavailable" | "reserved";
  };
  extra?: any;
}

export interface IVehicleDetailResponse {
  unique_id: string;
  type: "car" | "scooter" | "bicycle" | "car station" | "bicycle station";
  provider_id: string;
  current: {
    position: { lat: number; lng: number };
    status: "available" | "unavailable" | "reserved";
  };
  extra: any;
}

const BlueLAData = [
  {
    capacity: 5,
    availability: 3,
    type: "car station",
    address: " 2828 Beverly Blvd, LOS ANGELES, 90057, UNITED STATES",
    position: [34.0705694, -118.2798558]
  },
  {
    capacity: 5,
    availability: 5,
    type: "car station",
    address: " 225 E. 11th Street, LOS ANGELES, 90015, UNITED STATES",
    position: [34.03818770000001, -118.2563947]
  },
  {
    capacity: 5,
    availability: 3,
    type: "car station",
    address: " 503 E 8th Street, LOS ANGELES, 90014, UNITED STATES",
    status: "unavailable",
    position: [34.0402683, -118.2501367]
  },
  {
    capacity: 5,
    availability: 4,
    type: "car station",
    address: " 153 Glendale Boulevard, LOS ANGELES, 90026, UNITED STATES",
    position: [34.0634921, -118.2601084]
  },
  {
    capacity: 5,
    availability: 4,
    type: "car station",
    address: " 1629 James M Wood Blvd, LOS ANGELES, 90015, UNITED STATES",
    position: [34.05141, -118.273849]
  },
  {
    capacity: 5,
    availability: 2,
    type: "car station",
    address: " 306 Loma Drive Los Angeles, LOS ANGELES, 90017, UNITED STATES",
    position: [34.0593691, -118.2654073]
  },
  {
    capacity: 5,
    availability: 1,
    type: "car station",
    address: " 3921 Oakwood Avenue, LOS ANGELES, 90004, UNITED STATES",
    position: [34.0777087, -118.292559]
  },
  {
    capacity: 5,
    availability: 4,
    type: "car station",
    address:
      " 1332 S. Alvarado Street Los Angeles, LOS ANGELES, 90006, UNITED STATES",
    position: [34.0455726, -118.2835037]
  },
  {
    capacity: 5,
    availability: 4,
    type: "car station",
    address: " 1016 S. Berendo St., LOS ANGELES, 90006, UNITED STATES",
    status: "unavailable",
    position: [34.0523635, -118.2937284]
  },
  {
    capacity: 5,
    availability: 4,
    type: "car station",
    address: " 571 S. Bixel Street, LOS ANGELES, 90017, UNITED STATES",
    position: [34.05427, -118.2618419]
  },
  {
    capacity: 5,
    availability: 0,
    type: "car station",
    address: " 2308 S Grand Ave, LOS ANGELES, 90007, UNITED STATES",
    status: "unavailable",
    position: [34.028738, -118.270479]
  },
  {
    capacity: 5,
    availability: 4,
    type: "car station",
    address: " 301 S Grand View Street, LOS ANGELES, 90057, UNITED STATES",
    position: [34.06381400000001, -118.275224]
  },
  {
    capacity: 5,
    availability: 1,
    type: "car station",
    address: " 751 S Hoover Street, LOS ANGELES, 90005, UNITED STATES",
    position: [34.0584685, -118.2844088]
  },
  {
    capacity: 5,
    availability: 4,
    type: "car station",
    address: " 820 S Hope Street, LOS ANGELES, 90017, UNITED STATES",
    status: "unavailable",
    position: [34.045824, -118.2593737]
  },
  {
    capacity: 5,
    availability: 3,
    type: "car station",
    address: " 836 Stanford Ave, LOS ANGELES, 90021, UNITED STATES",
    position: [34.0353812, -118.2473173]
  },
  {
    capacity: 5,
    availability: 0,
    type: "car station",
    address: " 1711 Sunset Blvd, LOS ANGELES, 90026, UNITED STATES",
    status: "unavailable",
    position: [34.0776698, -118.258705]
  },
  {
    capacity: 5,
    availability: 5,
    type: "car station",
    address: " 615 S Virgil Avenue, LOS ANGELES, 90005, UNITED STATES",
    position: [34.063071, -118.287448]
  },
  {
    capacity: 5,
    availability: 1,
    type: "car station",
    address: " 3260 W 4th St., LOS ANGELES, 90020, UNITED STATES",
    status: "unavailable",
    position: [34.0664099, -118.2910036]
  },
  {
    capacity: 5,
    availability: 3,
    type: "car station",
    address: " 224 W 7th Street, LOS ANGELES, 90014, UNITED STATES",
    status: "unavailable",
    position: [34.0448795, -118.2532741]
  },
  {
    capacity: 5,
    availability: 1,
    type: "car station",
    address: " 1901 West 7th Street, LOS ANGELES, CA 90057, UNITED STATES",
    position: [34.0557407, -118.2748053]
  },
  {
    capacity: 5,
    availability: 0,
    type: "car station",
    address: " 4626 Willow Brook Ave, LOS ANGELES, 90029, UNITED STATES",
    position: [34.0894441, -118.292313]
  },
  {
    capacity: 5,
    availability: 3,
    type: "car station",
    address:
      " 2121 W Temple Street Los Angeles, LOS ANGELES, 90026, UNITED STATES",
    position: [34.070656, -118.2686048]
  }
];

const LADOT = [34.0513838, -118.245173];
function randomPosition(center?: number[], amplitude?: number) {
  center = center || LADOT;
  amplitude = amplitude || 0.15;
  return {
    lat: center[0] + (0.5 - Math.random()) * (amplitude * Math.random()),
    lng: center[1] + (0.5 - Math.random()) * (amplitude * Math.random())
  };
}
function uniqueId() {
  return `${Math.floor((Math.random() * 10 + Math.random()) * 1000)}`;
}

function randomVehicle(): IVehicleResponse {
  if (Math.random() > 0.2) {
    return {
      current: {
        position: randomPosition([34.048971, -118.348616], 0.25),
        status:
          Math.random() > 0.3
            ? "available"
            : Math.random() > 0.3
            ? "reserved"
            : "unavailable"
      },
      provider_id: Math.random() > 0.5 ? "bird" : "lime",
      type: "scooter",
      unique_id: uniqueId()
    };
  }
  if (Math.random() > 0.2) {
    const provider = Math.random() > 0.5 ? "JUMP" : "Metro Bike";
    let origin = [34.02495, -118.478006];
    let radius = 0.04;
    if (provider !== "JUMP" && Math.random() > 0.5) {
      origin = [34.042824, -118.262655];
      radius = 0.15;
    }
    return {
      current: {
        position: randomPosition(origin, radius),
        status:
          Math.random() > 0.3
            ? "available"
            : Math.random() > 0.3
            ? "reserved"
            : "unavailable"
      },
      provider_id: provider,
      type: "bicycle",
      unique_id: uniqueId()
    };
  }
  let origin = [34.02495, -118.478006];
  if (Math.random() > 0.5) {
    origin = [34.042824, -118.262655];
  }
  return {
    current: {
      position: randomPosition(origin, 0.04),
      status: "available"
    },
    provider_id: "Metro Bike",
    type: "bicycle station",
    unique_id: uniqueId(),
    extra: {
      capacity: 20,
      availability: Math.floor(Math.random() * 20)
    }
  };
}

const vehiclesStore = {};

export async function getVehicles(requestBody: {}): Promise<
  IVehicleResponse[]
> {
  // TODO
  // For now, mock data

  if (Object.keys(vehiclesStore).length === 0) {
    for (let i = 0; i < 200; i++) {
      const ve = randomVehicle();
      vehiclesStore[ve.unique_id] = ve;
    }
    for (let station of BlueLAData) {
      const stationObj: IVehicleResponse = {
        unique_id: uniqueId(),
        type: "car station",
        provider_id: "BlueLA",
        current: {
          position: {
            lat: station.position[0] as number,
            lng: station.position[1] as number
          },
          status: (station.status as "unavailable") || "available"
        },
        extra: {
          capacity: station.status === "unavailable" ? 0 : station.capacity,
          availability:
            station.status === "unavailable" ? 0 : station.availability
        }
      };
      vehiclesStore[stationObj.unique_id] = stationObj;
    }
  }
  const mockData = Object.keys(vehiclesStore).map(key => vehiclesStore[key]);

  const request = prepRequest("vehicle");
  let serverData = await (await fetch(request)).json();
  serverData = serverData
    .map((vehicle: any) => {
      if (
        !vehicle.position ||
        !vehicle.position.geometry ||
        !vehicle.position.geometry.coordinates
      ) {
        return null;
      }
      // TODO: map to old version of model to avoid rewriting the rendering logic
      // To be cleaned up later.
      const vehicleFormatted: IVehicleResponse = {
        unique_id: vehicle.id,
        type: "car",
        provider_id: "BlueLA",
        current: {
          position: {
            lat: vehicle.position.geometry.coordinates[1] as number,
            lng: vehicle.position.geometry.coordinates[0] as number
          },
          status: vehicle.status as "available"
        }
      };
      return vehicleFormatted;
    })
    .filter((vehicle: any) => !!vehicle);
  return serverData.concat(mockData);
}

export async function getVehicleDetail(
  vehicleId: string
): Promise<IVehicleDetailResponse> {
  return vehiclesStore[vehicleId] || randomVehicle();
}
