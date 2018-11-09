import * as React from "react";
import { NavLink } from "react-router-dom";

import { suffixPosition } from "../commons/position";

function isMenuActive(menu: string) {
  return function(match: any, location: any) {
    if (location && location.pathname) {
      const pathname: string = location.pathname;
      return pathname.startsWith(`/${menu}`);
    }
    return false;
  };
}

class Menu extends React.Component<{}> {
  public render() {
    return (
      <div
        style={{
          background: "#031424",
          color: "#FFFFFF",
          padding: 10,
          zIndex: 2000
        }}
      >
        &nbsp;
        <NavLink
          to={suffixPosition("/areas", location)}
          style={{ display: "inline-block", borderBottom: "solid 2px #031424" }}
          activeStyle={{ borderBottom: "solid 2px #fff" }}
          isActive={isMenuActive("areas")}
        >
          Areas setup
        </NavLink>{" "}
        |&nbsp;
        <NavLink
          to={suffixPosition("/views", location)}
          style={{ display: "inline-block", borderBottom: "solid 2px #031424" }}
          activeStyle={{ borderBottom: "solid 2px #fff" }}
          isActive={isMenuActive("views")}
        >
          Assets viewer
        </NavLink>
      </div>
    );
  }
}

export default Menu;
