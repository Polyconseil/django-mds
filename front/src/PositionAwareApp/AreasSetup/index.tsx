import * as L from "leaflet";
import "leaflet-draw";
import "leaflet-draw/dist/leaflet.draw.css";
import "leaflet/dist/leaflet.css";
import * as React from "react";

import IPositionRouteProps from "../commons/IPositionRouteProps";

import { getServiceAreas } from "src/api/areas";

import Map from "../commons/Map";

interface IState {
  layerIdsToAreaIds: { [key: string]: string };
}

class AreaSetup extends React.Component<IPositionRouteProps, IState> {
  public state = {
    layerIdsToAreaIds: {} // mapping of leafet layer id to backend area id
  };

  public handleMapReady(map: L.Map) {
    const drawnItems = L.featureGroup().addTo(map);
    map.addControl(
      new L.Control.Draw({
        draw: {
          circle: false,
          circlemarker: false,
          marker: false,
          polygon: {
            allowIntersection: false,
            showArea: true
          },
          polyline: false,
          rectangle: false
        },
        edit: {
          featureGroup: drawnItems
        }
      })
    );

    map.on(L.Draw.Event.CREATED, async (event: L.DrawEvents.Created) => {
      const layer = event.layer as L.Polygon;
      drawnItems.addLayer(layer);

      const result = await getServiceAreas({
        area: layer.toGeoJSON().geometry,
        begin_date: "2012-01-01T00:00:00Z"
      });

      const layerIdsToAreaIds = { ...this.state.layerIdsToAreaIds };
      layerIdsToAreaIds[L.Util.stamp(layer)] = result.unique_id;
      this.setState({ layerIdsToAreaIds });
    });
    map.on(L.Draw.Event.EDITED, (event: L.DrawEvents.Edited) => {
      const layers = event.layers;
      layers.eachLayer((layer: L.Polygon) => {
        // tslint:disable-next-line:no-console
        console.log("editing", layer.getLatLngs());
      });
    });
    map.on(L.Draw.Event.DELETED, (event: L.DrawEvents.Deleted) => {
      const layers = event.layers;
      layers.eachLayer((layer: L.Polygon) => {
        drawnItems.removeLayer(layer);
        // tslint:disable-next-line:no-console
        console.log("deleting", layer);
      });
    });
  }

  public render() {
    const { position, onPositionChange } = this.props;
    return (
      <Map
        position={position}
        onPositionChange={onPositionChange}
        onMapReady={this.handleMapReady}
      />
    );
  }
}

export default AreaSetup;
