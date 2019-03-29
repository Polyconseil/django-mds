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

const BICYCLE_ICON = L.icon({
  iconUrl: "/bicycle_picto.png",

  iconAnchor: [0, 25],
  iconSize: [43, 25],
  popupAnchor: [20, -25]
});

const CARSTATION_ICON = L.icon({
  iconUrl: "/carstation_picto.svg",

  iconAnchor: [12, 30],
  iconSize: [43, 43],
  popupAnchor: [12, -24]
});

const BICYCLESTATION_ICON = L.icon({
  iconUrl: "/bicyclestation_picto.svg",

  iconAnchor: [12, 30],
  iconSize: [43, 43],
  popupAnchor: [12, -24]
});

function capitalize(s: string) {
  if (s.length > 0) {
    return s[0].toUpperCase() + s.substr(1);
  }
  return "";
}

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
    result.forEach(vehicle => {
      let popupHTML = `
          <table>
            <tr><td style="text-align: right;">Id:</td><td>${vehicle.unique_id.substring(
              0,
              4
            )}</td></tr>
            <tr><td style="text-align: right;">Provider:</td><td>${capitalize(
              vehicle.provider_id
            )}</td></tr>
            <tr><td style="text-align: right;">Type:</td><td>${capitalize(
              vehicle.type
            )}</td></tr>
            <tr><td style="text-align: right;">Status:</td><td>${capitalize(
              vehicle.current.status
            )}</td></tr>
        `;
      if (
        vehicle.extra &&
        vehicle.extra.availability &&
        vehicle.extra.capacity
      ) {
        popupHTML =
          popupHTML +
          `
            <tr><td style="text-align: right;">${
              vehicle.type === "car station" ? "Parking" : "Docks"
            }:</td><td>${vehicle.extra.capacity -
            vehicle.extra.availability}</td></tr>
          ` +
          `
            <tr><td style="text-align: right;">${
              vehicle.type === "car station" ? "Cars" : "Bicycles"
            }:</td><td>${vehicle.extra.availability}</td></tr>
          `;
      }
      popupHTML += "</table>";
      const markerNode = L.marker(vehicle.current.position, {
        icon:
          vehicle.type === "car"
            ? CAR_ICON
            : vehicle.type === "scooter"
            ? SCOOTER_ICON
            : vehicle.type === "bicycle"
            ? BICYCLE_ICON
            : vehicle.type === "car station"
            ? CARSTATION_ICON
            : BICYCLESTATION_ICON
      })
        .bindPopup(popupHTML)
        .addTo(map)
        .getElement();
      if (markerNode) {
        markerNode.dataset.vehicleId = vehicle.unique_id;
      }
    });
  };
}

export default AssetsViewer;
