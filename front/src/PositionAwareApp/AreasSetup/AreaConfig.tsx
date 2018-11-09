import * as React from "react";
import {
  getAllPricingPolicies,
  getPricingPolicies,
  IPolicy,
  postPricingPolicy,
  removePricingPolicy
} from "../../api/areas";

interface IProps {
  areaId: string;
  height: number;
  width: number;
  marginLeft: number;
  onAreaConfigMounted: (areaId: string) => void;
}

interface IState {
  areaId: string | null;
  policies: IPolicy[];
  policiesOptions: IPolicy[];
  showPolicySelector: boolean;
}

class AreaConfig extends React.Component<IProps, IState> {
  public state: IState = {
    areaId: null,
    policies: [] as IPolicy[],
    policiesOptions: [] as IPolicy[],
    showPolicySelector: false
  };

  public async componentDidMount() {
    const { areaId, onAreaConfigMounted } = this.props;
    const policiesPromise = getPricingPolicies(areaId);
    const policiesOptiosnPromise = getAllPricingPolicies();
    const [policies, policiesOptions] = await Promise.all([
      policiesPromise,
      policiesOptiosnPromise
    ]);
    this.setState({ policies, policiesOptions });
    onAreaConfigMounted(areaId);
  }

  public async componentDidUpdate(prevProps: IProps) {
    const { areaId } = this.props;
    if (!areaId || areaId === prevProps.areaId) {
      return;
    }
    if (!prevProps.areaId) {
      this.setState({ showPolicySelector: false });
    }
    const policies = await getPricingPolicies(areaId);
    this.setState({ policies });
  }

  public render() {
    const { height, marginLeft, width } = this.props;
    const { policies, showPolicySelector } = this.state;
    return (
      <div
        style={{
          background: "#8eaebd"
        }}
      >
        <div
          style={{
            background: "#30415d",
            color: "#fff",
            height,
            marginLeft,
            marginTop: 10,
            padding: "30px 10px 10px 10px",
            transition: "margin 0.2s ease-in",
            width
          }}
        >
          <div>
            <h3 style={{ margin: 0 }}>
              Area policies{" "}
              <i
                className="fas fa-plus-circle"
                style={{ cursor: "pointer" }}
                onClick={() => {
                  this.setState({ showPolicySelector: true });
                }}
              />
            </h3>
            <div>
              {policies.length === 0 && !showPolicySelector ? (
                <p>This area has no configured policy.</p>
              ) : (
                <ol style={{ paddingLeft: 20, paddingRight: 20 }}>
                  {policies.map((pol: IPolicy) => this.renderPolicy(pol))}
                  {showPolicySelector ? this.renderPolicyChoices() : ""}
                </ol>
              )}
            </div>
          </div>
        </div>
      </div>
    );
  }

  private renderPolicy(policy: IPolicy) {
    return (
      <li key={policy.id} style={{ marginBottom: 10 }}>
        {policy.display}
        <i
          className="fas fa-minus-circle"
          onClick={() => this.removePolicy(policy)}
          style={{
            cursor: "pointer",
            display: "inline-block",
            float: "right"
          }}
        />
      </li>
    );
  }

  private renderPolicyChoices() {
    const { policiesOptions } = this.state;
    return (
      <li style={{ marginBottom: 10 }}>
        <select
          onChange={e =>
            this.addPolicy(policiesOptions[e.target.selectedIndex - 1])
          }
        >
          <option value="-">---</option>
          {policiesOptions.map(opt => (
            <option key={opt.id} value={opt.id}>
              {opt.display}
            </option>
          ))}
        </select>
        <i
          className="fas fa-minus-circle"
          onClick={() => this.removePolicy()}
          style={{
            cursor: "pointer",
            display: "inline-block",
            float: "right"
          }}
        />
      </li>
    );
  }

  private removePolicy(policy?: IPolicy) {
    this.setState({ showPolicySelector: false });
    if (policy) {
      removePricingPolicy(this.props.areaId, policy.id);
      this.setState({
        policies: this.state.policies.filter((p: IPolicy) => p.id !== policy.id)
      });
    }
  }

  private addPolicy(policy: IPolicy) {
    postPricingPolicy(this.props.areaId, policy);
    this.setState({
      policies: this.state.policies.concat([policy]),
      showPolicySelector: false
    });
  }
}

export default AreaConfig;
