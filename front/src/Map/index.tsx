import * as React from "react";
import { matchPath } from "react-router";

import { LatLngLiteral } from "leaflet";

import Map from "./Map";
import { parsePosition, stringifyPosition } from "./positionInUrl";

interface IParams {
  search: string;
  position: string;
}

export interface IProps {
  match: { path: string };
  location: { pathname: string };
  history: { push: (path: string) => void };
}

export class MapViewer extends React.Component<IProps> {
  public map: React.RefObject<Map> = React.createRef();

  public render() {
    const { search, latlng, zoom } = this.parseUrl();

    return (
      <Map
        search={search}
        latlng={latlng}
        zoom={zoom}
        onMoveZoom={this.onMoveZoom}
        ref={this.map}
      />
    );
  }

  private onMoveZoom = (latlng: LatLngLiteral, zoom: number) => {
    const { match, history } = this.props;
    const { search } = this.parseUrl();

    history.push(
      `${match.path}${search && "/search/" + search}/@${stringifyPosition({
        latlng,
        zoom
      })}`
    );
  };

  private parseUrl = (): {
    search: string;
    latlng: LatLngLiteral | null;
    zoom: number | null;
  } => {
    const { match, location } = this.props;
    const submatch = matchPath<IParams>(location.pathname, {
      path: `${match.path}/search/:search`
    });

    let search = "";
    if (submatch) {
      search = submatch.params.search || "";
    }

    let latlng = null;
    let zoom = null;

    const positionIndex = location.pathname.lastIndexOf("/@");
    if (positionIndex !== -1) {
      const parsed = parsePosition(
        location.pathname.substring(positionIndex + 2)
      );
      if (parsed) {
        latlng = parsed.latlng;
        zoom = parsed.zoom || null;
      }
    }

    return { search, latlng, zoom };
  };
}
