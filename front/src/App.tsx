import * as React from "react";
import { BrowserRouter, Route } from "react-router-dom";

import PositionAwareApp from "./PositionAwareApp";
class App extends React.Component {
  public render() {
    return (
      <BrowserRouter>
        <Route component={PositionAwareApp} />
      </BrowserRouter>
    );
  }
}

export default App;
