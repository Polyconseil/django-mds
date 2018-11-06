import * as L from "leaflet";
import "leaflet-draw";
import "leaflet-draw/dist/leaflet.draw.css";
import "leaflet/dist/leaflet.css";
import * as React from "react";

import IPositionRouteProps from "../commons/IPositionRouteProps";

import { deleteServiceArea, getServiceAreas, postServiceArea } from "src/api/areas";

import Map from "../commons/Map";

interface IState {
  layerIdsToAreaIds: { [key: string]: string };
}

class AreaSetup extends React.Component<IPositionRouteProps, IState> {
  public state = {
    layerIdsToAreaIds: {} // mapping of leafet layer id to backend area id
  };

  constructor (props: IPositionRouteProps) {
    super(props);
    this.handleMapReady = this.handleMapReady.bind(this);
  }

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

    getServiceAreas().then((areas) => {
      areas.forEach((area: any) => {
        const polygon = JSON.parse(area.area);
        polygon.type = "Polygon";
        polygon.coordinates = polygon.coordinates[0];
        const layerIdsToAreaIds = { ...this.state.layerIdsToAreaIds };
        L.geoJSON(polygon).eachLayer((l) => {
          drawnItems.addLayer(l);
          layerIdsToAreaIds[L.Util.stamp(l)] = area.unique_id;
        })
        this.setState({ layerIdsToAreaIds });
      })
    });

    map.on(L.Draw.Event.CREATED, async (event: L.DrawEvents.Created) => {
      const layer = event.layer as L.Polygon;
      drawnItems.addLayer(layer);

      const result = await postServiceArea({
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
      layers.eachLayer(async (layer: L.Polygon) => {
        drawnItems.removeLayer(layer);
        const areaId = this.state.layerIdsToAreaIds[L.Util.stamp(layer)];
        await deleteServiceArea(areaId);
        const layerIdsToAreaIds = { ...this.state.layerIdsToAreaIds };
        delete layerIdsToAreaIds[L.Util.stamp(layer)]
        this.setState({layerIdsToAreaIds})
      })
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
