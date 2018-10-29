import * as L from "leaflet";
import * as React from "react";
import ContainerDimensions from "react-container-dimensions";
import { Route, RouteComponentProps } from "react-router-dom";

import { getVehicles } from "src/api/vehicles";

import IPositionRouteProps from "../commons/IPositionRouteProps";
import Map from "../commons/Map/Map";
import { suffixPosition } from "../commons/position";

import VehicleDetail from "./VehicleDetail";

const CAR_ICON = L.icon({
  iconUrl: "/car_picto.png",

  iconAnchor: [0, 25],
  iconSize: [43, 25]
});

const SCOOTER_ICON = L.icon({
  iconUrl: "/scooter_picto.png",

  iconAnchor: [0, 25],
  iconSize: [43, 25]
});

class AssetsViewer extends React.Component<IPositionRouteProps> {
  public render() {
    const { match, position, onPositionChange } = this.props;
    return (
      <div style={{ display: "flex", flex: 1 }}>
        <ContainerDimensions>
          {({ width, height }) => (
            <>
              <Route
                path={`${match.path}/vehicle/:vehicleId`}
                render={this.bindDetailView(height)}
              />
              <Map
                position={position}
                onPositionChange={onPositionChange}
                onMapReady={this.handleMapReady}
                width={width}
                height={height}
              />
            </>
          )}
        </ContainerDimensions>
      </div>
    );
  }

  private bindDetailView = (height: number) => {
    return (subProps: RouteComponentProps<{ vehicleId: string }>) => {
      return (
        <VehicleDetail
          height={height}
          vehicleId={subProps.match.params.vehicleId}
          onRequestClose={this.handleRequestClose}
        />
      );
    };
  };

  private openDetail = (event: L.LeafletEvent) => {
    const { match, location, history } = this.props;
    const vehicleId = event.target.getElement().dataset.vehicleId;
    history.push(suffixPosition(`${match.url}/vehicle/${vehicleId}`, location));
  };

  private handleRequestClose = () => {
    const { match, location, history } = this.props;
    history.push(suffixPosition(match.url, location));
  };

  private handleMapReady = async (map: L.Map) => {
    const result = await getVehicles({});
    result.vehicles.forEach(vehicle => {
      const markerNode = L.marker(vehicle.current.position, {
        icon: vehicle.type === "car" ? CAR_ICON : SCOOTER_ICON
      })
        .on("click", this.openDetail)
        .addTo(map)
        .getElement();
      if (markerNode) {
        markerNode.dataset.vehicleId = vehicle.unique_id;
      }
    });
  };
}

export default AssetsViewer;
