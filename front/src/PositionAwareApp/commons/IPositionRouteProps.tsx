import { RouteComponentProps } from "react-router-dom";

import { IPosition, PositionChanger } from "./position";

export interface IPositionAware {
  position: IPosition;
  onPositionChange: PositionChanger;
}

export default interface IPositionRoute
  extends IPositionAware,
    RouteComponentProps {}
