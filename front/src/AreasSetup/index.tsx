import * as L from "leaflet";
import "leaflet-draw";
import "leaflet-draw/dist/leaflet.draw.css";
import "leaflet/dist/leaflet.css";
import * as React from "react";

import { IProps, MapViewer } from "../Map";

interface IState {
  layerIdsToAreaIds: { [key:string]: string; }
}

class AreaSetup extends React.Component<IProps, IState> {
  private mapViewer: React.RefObject<MapViewer> = React.createRef();

  constructor(props: IProps) {
    super(props);
    this.state = {
      layerIdsToAreaIds: {}, // mapping of leafet layer id to backend area id
    };
  }

  public componentDidMount() {

    if (!this.mapViewer.current || !this.mapViewer.current.map.current) {
      return
    }
    const map = this.mapViewer.current.map.current.map
    const drawnItems = L.featureGroup().addTo(map);
    map.addControl(new L.Control.Draw({
        draw: {
            circle: false,
            circlemarker: false,
            marker: false,
            polygon: {
                allowIntersection: false,
                showArea: true
            },
            polyline: false,
            rectangle: false,
        },
        edit: {
            featureGroup: drawnItems,
        },
    }));

    map.on(L.Draw.Event.CREATED, async (event: L.DrawEvents.Created) => {
        const layer = event.layer as L.Polygon;
        drawnItems.addLayer(layer);
        const request = new Request(
          "http://127.0.0.1:8000/service_area/", // TODO use true URL
          {
            body: JSON.stringify({
              area: layer.toGeoJSON().geometry,
              begin_date: "2012-01-01T00:00:00Z",
            }),
            headers: {
              "Content-Type": "application/json",
            },
            method: "POST",
            mode: "cors",
          }
        )
        const result = await (await fetch(request)).json()
        const layerIdsToAreaIds = Object.assign({}, this.state.layerIdsToAreaIds);
        layerIdsToAreaIds[L.Util.stamp(layer)] = result.unique_id
        this.setState({layerIdsToAreaIds})
    });
    map.on(L.Draw.Event.EDITED, (event: L.DrawEvents.Edited) => {
        const layers = event.layers;
        layers.eachLayer((layer: L.Polygon) => {
          // tslint:disable-next-line:no-console
          console.log("editing", layer.getLatLngs())
        })
    });
    map.on(L.Draw.Event.DELETED, (event: L.DrawEvents.Deleted) => {
        const layers = event.layers;
        layers.eachLayer((layer: L.Polygon) => {
          drawnItems.removeLayer(layer)
          // tslint:disable-next-line:no-console
          console.log("deleting", layer)
        })
    });
  };

  public render() {
    return (
      <MapViewer
        history={ this.props.history }
        location={ this.props.location }
        match={ this.props.match }
        ref={ this.mapViewer }
      />
    )
  };
}

export default AreaSetup;
