import * as L from "leaflet";
import "leaflet/dist/leaflet.css";
import * as React from "react";

import ILatLng from "../commons/ILatLng";

const DEFAULT_COORDINATES: [number, number] = [51.505, -0.09];
const DEFAULT_ZOOM = 14;

interface IProps {
  search: string;
  latlng: ILatLng | null;
  zoom: number | null;
  onMoveZoom: (latlng: ILatLng, zoom: number) => void;
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

    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution:
        '&copy; <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a>',
      id: "OpenStreetMap.Mapnik",
      maxZoom: 18
    }).addTo(this.map);

    this.map.on("moveend", this.handleMoveZoom);
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
    this.props.onMoveZoom(latlng, zoom);
  };
}

export default Viewer;
