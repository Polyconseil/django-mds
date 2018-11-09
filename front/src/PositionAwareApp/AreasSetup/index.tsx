import * as L from "leaflet";
import "leaflet-draw";
import "leaflet-draw/dist/leaflet.draw.css";
import "leaflet/dist/leaflet.css";
import * as React from "react";
import ContainerDimensions from "react-container-dimensions";
import { Route, RouteComponentProps } from "react-router-dom";

import IPositionRouteProps from "../commons/IPositionRouteProps";
import { suffixPosition } from "../commons/position";
import AreaConfig from "./AreaConfig";

import {
  deleteServiceArea,
  getServiceAreas,
  postServiceArea,
  updateServiceArea
} from "src/api/areas";

import Map from "../commons/Map";

const DEFAULT_SHAPE_COLOR = "#3388ff";

interface IState {
  activeArea: L.GeoJSON | null;
  areasLayerGroup: L.FeatureGroup | null;
  isUserEditing: boolean;
  layerIdsToAreaIds: { [key: string]: string };
  map: L.Map | null;
  startupAreaId: string | null;
}

class AreaSetup extends React.Component<IPositionRouteProps, IState> {
  public state: IState = {
    activeArea: null,
    areasLayerGroup: null,
    isUserEditing: false,
    layerIdsToAreaIds: {}, // mapping of leafet layer id to backend area id
    map: null,
    startupAreaId: null
  };

  constructor(props: IPositionRouteProps) {
    super(props);
    this.handleMapReady = this.handleMapReady.bind(this);
    this.onAreaConfigMounted = this.onAreaConfigMounted.bind(this);
  }

  public handleMapReady(map: L.Map) {
    const drawnItems = L.featureGroup().addTo(map);
    this.setState({ areasLayerGroup: drawnItems, map });

    const drawControl = new L.Control.Draw({
      draw: {
        circle: false,
        circlemarker: false,
        marker: false,
        polygon: {
          allowIntersection: false,
          showArea: true
        },
        polyline: false,
        rectangle: false
      },
      edit: {
        featureGroup: drawnItems
      }
    });
    map.addControl(drawControl);

    getServiceAreas().then(areas => {
      areas.forEach((area: any) => {
        const polygon = area.area;
        const layerIdsToAreaIds = { ...this.state.layerIdsToAreaIds };
        L.geoJSON(polygon).eachLayer((l: L.GeoJSON) => {
          drawnItems.addLayer(l);
          l.on("click", this.openDetail);
          layerIdsToAreaIds[L.Util.stamp(l)] = area.id;
          if (area.id === this.state.startupAreaId) {
            this.setState({ activeArea: l });
            l.setStyle({ fillColor: "red" });
          }
        });
        this.setState({ layerIdsToAreaIds });
      });
    });

    map.on(L.Draw.Event.CREATED, async (event: L.DrawEvents.Created) => {
      const layer = event.layer as L.Polygon;
      drawnItems.addLayer(layer);
      layer.on("click", this.openDetail);

      const result = await postServiceArea({
        area: layer.toGeoJSON().geometry,
        begin_date: "2012-01-01T00:00:00Z"
      });

      const layerIdsToAreaIds = { ...this.state.layerIdsToAreaIds };
      layerIdsToAreaIds[L.Util.stamp(layer)] = result.id;
      this.setState({ layerIdsToAreaIds });
    });
    map.on(L.Draw.Event.EDITED, (event: L.DrawEvents.Edited) => {
      const layers = event.layers;
      layers.eachLayer(async (layer: L.Polygon) => {
        const id = this.state.layerIdsToAreaIds[L.Util.stamp(layer)];
        await updateServiceArea(id, {
          area: layer.toGeoJSON().geometry
        });
      });
    });
    map.on(L.Draw.Event.DELETED, (event: L.DrawEvents.Deleted) => {
      const layers = event.layers;
      layers.eachLayer(async (layer: L.Polygon) => {
        drawnItems.removeLayer(layer);
        const areaId = this.state.layerIdsToAreaIds[L.Util.stamp(layer)];
        await deleteServiceArea(areaId);
        const layerIdsToAreaIds = { ...this.state.layerIdsToAreaIds };
        delete layerIdsToAreaIds[L.Util.stamp(layer)];
        this.setState({ layerIdsToAreaIds });
      });
    });
    map.on(L.Draw.Event.EDITSTART, (e: L.DrawEvents.EditStart) => {
      this.closeDetail();
      this.setState({ isUserEditing: true });
    });
    map.on(L.Draw.Event.EDITSTOP, (e: L.DrawEvents.EditStart) =>
      this.setState({ isUserEditing: false })
    );
    map.on(L.Draw.Event.DELETESTART, (e: L.DrawEvents.EditStart) => {
      this.closeDetail();
      this.setState({ isUserEditing: true });
    });
    map.on(L.Draw.Event.DELETESTOP, (e: L.DrawEvents.EditStart) =>
      this.setState({ isUserEditing: false })
    );
    map.on("click", (event: L.LeafletMouseEvent) => {
      this.closeDetail();
    });
  }

  public render() {
    const { match, position, onPositionChange } = this.props;
    return (
      <div style={{ display: "flex", flex: 1 }}>
        <ContainerDimensions>
          {({ width, height }) => (
            <>
              <Route
                path={`${match.path}/details/:areaId`}
                children={this.bindDetailView(height)}
              />
              <Map
                position={position}
                onPositionChange={onPositionChange}
                onMapReady={this.handleMapReady}
                height={height}
              />
            </>
          )}
        </ContainerDimensions>
      </div>
    );
  }

  private openDetail = (event: Event) => {
    const { match, location, history } = this.props;
    const { activeArea, isUserEditing, map } = this.state;
    if (isUserEditing || !map) {
      return;
    }
    const areaId = this.state.layerIdsToAreaIds[L.Util.stamp(event.target)];
    history.push(suffixPosition(`${match.url}/details/${areaId}`, location));
    const layer = (event.target as unknown) as L.GeoJSON;
    if (activeArea) {
      activeArea.setStyle({ fillColor: DEFAULT_SHAPE_COLOR });
    }
    layer.setStyle({ fillColor: "red" });
    this.setState({
      activeArea: layer
    });
    L.DomEvent.stopPropagation(event);
  };

  private closeDetail = () => {
    const { match, location, history } = this.props;
    const { activeArea } = this.state;
    if (activeArea) {
      activeArea.setStyle({ fillColor: DEFAULT_SHAPE_COLOR });
      this.setState({
        activeArea: null
      });
    }
    history.push(suffixPosition(match.url, location));
  };

  private onAreaConfigMounted(areaId: string) {
    this.setState({ startupAreaId: areaId });
  }

  private bindDetailView = (height: number) => {
    return (subProps: RouteComponentProps<{ areaId: string }>) => {
      return (
        <AreaConfig
          areaId={subProps.match && subProps.match.params.areaId}
          height={height}
          width={300}
          marginLeft={subProps.match ? 0 : -320}
          onAreaConfigMounted={this.onAreaConfigMounted}
        />
      );
    };
  };
}

export default AreaSetup;
