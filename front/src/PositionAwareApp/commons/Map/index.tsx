import * as React from "react";
import ContainerDimensions from "react-container-dimensions";

import Map, { IProps } from "./Map";

export default class AutosizedMap extends React.Component<IProps> {
  public render() {
    return (
      <ContainerDimensions>
        {({ width, height }) => (
          <Map {...this.props} width={width} height={height} />
        )}
      </ContainerDimensions>
    );
  }
}
