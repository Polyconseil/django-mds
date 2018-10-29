import * as React from "react";

import { getVehicleDetail, IVehicleDetailResponse } from "src/api/vehicles";

interface IProps {
  height: number;
  vehicleId: string;
  onRequestClose: () => void;
}

interface IState {
  vehicle: IVehicleDetailResponse | null;
}

class VehicleDetail extends React.Component<IProps, IState> {
  public state = {
    vehicle: null
  };

  public componentDidMount() {
    const { vehicleId } = this.props;
    this.fetchData(vehicleId);
  }

  public componentDidUpdate(prevProps: IProps) {
    const { vehicleId } = this.props;
    if (vehicleId !== prevProps.vehicleId) {
      this.fetchData(vehicleId);
    }
  }

  public render() {
    const { height, onRequestClose, vehicleId } = this.props;

    return (
      <div
        style={{
          background: "#FFF",
          boxShadow: "7px 2px 19px -5px rgba(0,0,0,0.75)",
          height,
          position: "absolute",
          width: 400,
          zIndex: 1000
        }}
      >
        <div
          style={{
            cursor: "pointer",
            height: 20,
            position: "absolute",
            right: 5,
            top: 5,
            width: 20
          }}
          onClick={onRequestClose}
        >
          X
        </div>
        <div>Detail: {vehicleId}</div>
      </div>
    );
  }

  private fetchData = async (vehicleId: string) => {
    const vehicle = await getVehicleDetail(vehicleId);
    this.setState({ vehicle });
  };
}

export default VehicleDetail;
