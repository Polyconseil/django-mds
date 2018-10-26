import * as React from "react";

import { IProps, MapViewer } from "../Map";


class AssetsViewer extends React.Component<IProps> {
  public render() {
    return (
      <MapViewer
        history={ this.props.history }
        location={ this.props.location }
        match={ this.props.match }
      />
    )
  }
}

export default AssetsViewer;
