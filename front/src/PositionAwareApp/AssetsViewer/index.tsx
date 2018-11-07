import * as L from "leaflet";
import * as React from "react";
import ContainerDimensions from "react-container-dimensions";

import { getVehicles } from "src/api/vehicles";

import IPositionRouteProps from "../commons/IPositionRouteProps";
import Map from "../commons/Map/Map";

const CAR_ICON = L.icon({
  iconUrl: "/car_picto.png",

  iconAnchor: [0, 25],
  iconSize: [43, 25],
  popupAnchor: [20, -25]
});

const SCOOTER_ICON = L.icon({
  iconUrl: "/scooter_picto.png",

  iconAnchor: [0, 25],
  iconSize: [43, 25],
  popupAnchor: [20, -25]
});

class AssetsViewer extends React.Component<IPositionRouteProps> {
  public render() {
    const { position, onPositionChange } = this.props;
    return (
      <div style={{ display: "flex", flex: 1 }}>
        <ContainerDimensions>
          {({ width, height }) => (
            <Map
              position={position}
              onPositionChange={onPositionChange}
              onMapReady={this.handleMapReady}
              width={width}
              height={height}
            />
          )}
        </ContainerDimensions>
      </div>
    );
  }

  private handleMapReady = async (map: L.Map) => {
    const result = await getVehicles({});
    result.vehicles.forEach(vehicle => {
      const markerNode = L.marker(vehicle.current.position, {
        icon: vehicle.type === "car" ? CAR_ICON : SCOOTER_ICON
      })
        .bindPopup(`
          <table>
            <tr><td style="text-align: right;">Provider:</td><td>${vehicle.provider_id}</td></tr>
            <tr><td style="text-align: right;">Type:</td><td>${vehicle.type}</td></tr>
            <tr><td style="text-align: right;">Status:</td><td>${vehicle.current.status}</td></tr>
          </table>
        `)
        .addTo(map)
        .getElement();
      if (markerNode) {
        markerNode.dataset.vehicleId = vehicle.unique_id;
      }
    });
  };
}

export default AssetsViewer;
