import * as React from "react";
import { Link } from "react-router-dom";

import { suffixPosition } from "../commons/position";
class Menu extends React.Component<{}> {
  public render() {
    return (
      <div
        style={{
          background: "#2f3d6f",
          color: "#FFFFFF",
          padding: 2,
          zIndex: 2000
        }}
      >
        &nbsp;
        <Link to={suffixPosition("/areas", location)}>Areas setup</Link> |&nbsp;
        <Link to={suffixPosition("/views", location)}>Assets viewer</Link>
      </div>
    );
  }
}

export default Menu;
