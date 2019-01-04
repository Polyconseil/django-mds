/* global __SETTINGS__ */

declare var __SETTINGS__: any;

const SETTINGS = {} as any;
const envSettings = {
  urls: {
    apiBaseUrl: process.env.REACT_APP_API_BASE_URL,
    apiAccessToken: process.env.REACT_APP_ACCESS_TOKEN,
  }
};

if (typeof __SETTINGS__ === "undefined") {
  Object.assign(SETTINGS, envSettings);
} else {
  Object.assign(SETTINGS, __SETTINGS__);
}

export default SETTINGS;
