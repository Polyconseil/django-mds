import * as React from "react";
import { Redirect, Route, RouteComponentProps, Switch } from "react-router-dom";

import IPositionRouteProps from "./commons/IPositionRouteProps";
import NoMatch from "./commons/NoMatch";
import {
  IPosition,
  parsePosition,
  stringifyPosition
} from "./commons/position";

import AreasSetup from "./AreasSetup";
import AssetsViewer from "./AssetsViewer";
import Menu from "./Menu";

export default class PositionAwareApp extends React.Component<
  RouteComponentProps
> {
  public render() {
    const { match } = this.props;
    const position = this.extractPosition();

    return (
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          height: "100%",
          position: "absolute",
          width: "100%"
        }}
      >
        <Menu />
        <div style={{ display: "flex", flex: 1, overflow: "hidden" }}>
          <Switch>
            <Route
              path={`${match.path}areas`}
              render={this.positionAwareChild(position, AreasSetup)}
            />
            <Route
              path={`${match.path}views`}
              render={this.positionAwareChild(position, AssetsViewer)}
            />
            <Redirect path="/" exact={true} to="views" />
            <Route component={NoMatch} />
          </Switch>
        </div>
      </div>
    );
  }

  private positionAwareChild = (
    position: IPosition,
    Component: React.ComponentType<IPositionRouteProps>
  ) => {
    return (props: RouteComponentProps) => (
      <Component
        {...props}
        position={position}
        onPositionChange={this.handlePositionChange}
      />
    );
  };

  private extractPosition(): IPosition {
    const { location } = this.props;
    const positionIndex = location.pathname.lastIndexOf("/@");
    if (positionIndex !== -1) {
      const parsed = parsePosition(
        location.pathname.substring(positionIndex + 2)
      );
      if (parsed) {
        return parsed;
      }
    }

    // Default position (TODO: could be fetched from server as current city center)
    return {
      latlng: { lat: 34.0513838, lng: -118.2451737 },
      zoom: 14
    };
  }

  private handlePositionChange = (position: IPosition) => {
    const { history } = this.props;

    let pathWithoutPosition = location.pathname;
    const positionIndex = location.pathname.lastIndexOf("/@");
    if (positionIndex !== -1) {
      pathWithoutPosition = location.pathname.substring(0, positionIndex);
    }

    const stringifiedPosition = stringifyPosition(position);
    history.replace(`${pathWithoutPosition}/@${stringifiedPosition}`);
  };
}
