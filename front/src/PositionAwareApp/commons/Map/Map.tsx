import * as L from "leaflet";
import "leaflet-draw";
import "leaflet-draw/dist/leaflet.draw.css";
import "leaflet/dist/leaflet.css";
import * as React from "react";

import { IPosition, PositionChanger } from "../position";

const DEFAULT_ZOOM = 14;

export interface IProps {
  width?: number;
  height?: number;
  position: IPosition;
  onPositionChange?: PositionChanger;
  onMapReady?: (map: L.Map) => void;
}

class Map extends React.Component<IProps> {
  public map: L.Map;
  private leafElementRef: React.RefObject<HTMLDivElement> = React.createRef();

  public componentDidMount() {
    if (!this.leafElementRef.current) {
      return; // Guard
    }
    const { position } = this.props;

    this.map = L.map(this.leafElementRef.current, {
      zoomControl: false
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
        maxZoom: 18
      }
    ).addTo(this.map);
    this.map.on("moveend", this.handleMoveZoom);

    if (this.props.onMapReady) {
      this.props.onMapReady(this.map);
    }
  }

  public componentDidUpdate(prevProps: IProps) {
    const { position } = this.props;
    this.map.setView(position.latlng, position.zoom || DEFAULT_ZOOM);

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

    if (
      latlng.lat === position.latlng.lat &&
      latlng.lng === position.latlng.lng &&
      zoom === position.zoom
    ) {
      return;
    }

    onPositionChange({ latlng, zoom });
  };
}

export default Map;
