import * as L from "leaflet";
import "leaflet-draw";
import "leaflet-draw/dist/leaflet.draw.css";
import "leaflet/dist/leaflet.css";
import * as React from "react";

import { IPosition, PositionChanger } from "../position";

const DEFAULT_ZOOM = 14;

function areSame(p1: IPosition, p2: IPosition) {
  const threshold = 0.00001;
  if (
    Math.abs(p1.latlng.lat - p2.latlng.lat) < threshold &&
    Math.abs(p1.latlng.lng - p2.latlng.lng) < threshold &&
    p1.zoom === p2.zoom
  ) {
    return true;
  }
  return false;
}

export interface IProps {
  width?: number;
  height?: number;
  position: IPosition;
  onPositionChange?: PositionChanger;
  onMapReady?: (map: L.Map) => void;
}

class Map extends React.Component<IProps> {
  public map: L.Map;
  private updateSource: "url" | "map" | null = null; // not linked with render => keep outside of state
  private leafElementRef: React.RefObject<HTMLDivElement> = React.createRef();

  public componentDidMount() {
    if (!this.leafElementRef.current) {
      return; // Guard
    }
    const { position } = this.props;

    this.map = L.map(this.leafElementRef.current, {
      zoomControl: false,
    }).setView(position.latlng, position.zoom || DEFAULT_ZOOM);

    L.control.zoom({ position: "bottomright" }).addTo(this.map);

    // TODO get a token from mapbox
    L.tileLayer(
      "https://api.tiles.mapbox.com/v4/{id}/{z}/{x}/{y}.png?access_token=pk.eyJ1IjoibWFwYm94IiwiYSI6ImNpejY4NXVycTA2emYycXBndHRqcmZ3N3gifQ.rJcFIG214AriISLbB6B5aw",
      {
        attribution:
          'Map data &copy; <a href="https://www.openstreetmap.org/">OpenStreetMap</a> contributors, ' +
          '<a href="https://creativecommons.org/licenses/by-sa/2.0/">CC-BY-SA</a>, ' +
          'Imagery © <a href="https://www.mapbox.com/">Mapbox</a>',
        id: "mapbox.streets",
        maxZoom: 18,
      }
    ).addTo(this.map);
    this.map.on("moveend", this.handleMoveZoom);

    if (this.props.onMapReady) {
      this.props.onMapReady(this.map);
    }
  }

  public componentDidUpdate(prevProps: IProps) {
    const { position } = this.props;
    const prevPosition = prevProps.position;
    if (this.updateSource !== "map" && !areSame(prevPosition, position)) {
      this.updateSource = "url";
      this.map.setView(position.latlng, position.zoom || DEFAULT_ZOOM);
    } else {
      this.updateSource = null;
    }

    const prevSize = this.getSize(prevProps);
    const newSize = this.getSize(this.props);
    if (
      prevSize.width !== newSize.width ||
      prevSize.height !== newSize.height
    ) {
      this.map.invalidateSize();
    }
  }

  public componentWillUnmount() {
    this.map.remove();
  }

  public render() {
    const { width, height } = this.getSize(this.props);

    return (
      <div>
        <div style={{ width, height }} ref={this.leafElementRef} />
      </div>
    );
  }

  private getSize = (props: IProps) => {
    const { width = 800, height = 600 } = props;
    return { width, height };
  };

  private handleMoveZoom = () => {
    const { position, onPositionChange } = this.props;
    if (!onPositionChange) {
      return;
    }
    const latlng = this.map.getCenter();
    const zoom = this.map.getZoom();

    if (areSame(position, { latlng, zoom })) {
      return;
    }

    this.updateSource = this.updateSource || "map";
    if (this.updateSource === "map") {
      // The map was updated through the user dragging the map.
      // Propage this change in parent components in order to
      // e.g. update the URL
      onPositionChange({ latlng, zoom });
    } else {
      // The map was updated through props, the parent components
      // are already aware of it and don't need to be notified
      this.updateSource = null;
    }
  };
}

export default Map;
