import * as L from "leaflet";
import "leaflet/dist/leaflet.css";
import * as React from "react";

import { LatLngLiteral } from "leaflet"

const DEFAULT_COORDINATES: [number, number] = [51.505, -0.09];
const DEFAULT_ZOOM = 14;

interface IProps {
  search: string;
  latlng: LatLngLiteral | null;
  zoom: number | null;
  onMoveZoom: (latlng: LatLngLiteral, zoom: number) => void;
}

class Viewer extends React.Component<IProps> {
  private leafElementRef: React.RefObject<HTMLDivElement> = React.createRef();
  private map: L.Map;

  public componentDidMount() {
    if (!this.leafElementRef.current) {
      return; // Guard
    }
    const { latlng, zoom } = this.props;

    const center: L.LatLngExpression = latlng || DEFAULT_COORDINATES;
    const safeZoom = zoom || DEFAULT_ZOOM;
    this.map = L.map(this.leafElementRef.current).setView(center, safeZoom);

    // TODO get a token from mapbox
    L.tileLayer('https://api.tiles.mapbox.com/v4/{id}/{z}/{x}/{y}.png?access_token=pk.eyJ1IjoibWFwYm94IiwiYSI6ImNpejY4NXVycTA2emYycXBndHRqcmZ3N3gifQ.rJcFIG214AriISLbB6B5aw', {
      attribution: 'Map data &copy; <a href="https://www.openstreetmap.org/">OpenStreetMap</a> contributors, ' +
        '<a href="https://creativecommons.org/licenses/by-sa/2.0/">CC-BY-SA</a>, ' +
        'Imagery © <a href="https://www.mapbox.com/">Mapbox</a>',
      id: 'mapbox.streets',
      maxZoom: 18,
    }).addTo(this.map);

    this.map.on("moveend", this.handleMoveZoom);
  }

  public componentDidUpdate() {
    if (this.props.latlng && this.props.zoom) {
      this.map.setView(this.props.latlng, this.props.zoom)
    }
  }

  public componentWillUnmount() {
    this.map.remove();
  }

  public render() {
    return (
      <div>
        <div>The map {JSON.stringify(this.props)}</div>
        <div style={{ width: 800, height: 600 }} ref={this.leafElementRef} />
      </div>
    );
  }

  private handleMoveZoom = () => {
    const latlng = this.map.getCenter();
    const zoom = this.map.getZoom();
    if (this.props.latlng && this.props.zoom) {
      if (latlng.lat === this.props.latlng.lat && latlng.lng === this.props.latlng.lng && zoom === this.props.zoom) {
        return
      }
    }
    this.props.onMoveZoom(latlng, zoom);
  };
}

export default Viewer;
