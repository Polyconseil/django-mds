import * as React from "react";
import { BrowserRouter, Link, Redirect, Route, Switch } from "react-router-dom";

import NoMatch from "./commons/NoMatch";

import AreasSetup from "./AreasSetup";
import AssetsViewer from "./AssetsViewer";

class App extends React.Component {
  public render() {
    return (
      <BrowserRouter>
        <div>
          <div>
            Pages: <Link to="/areas">Areas setup</Link>
            <Link to="/viewer">Assets viewer</Link>
          </div>
          <Switch>
            <Route path="/areas" component={AreasSetup} />
            <Route path="/viewer" component={AssetsViewer} />
            <Redirect path="/" exact={true} to="viewer" />
            <Route component={NoMatch} />
          </Switch>
        </div>
      </BrowserRouter>
    );
  }
}

export default App;
