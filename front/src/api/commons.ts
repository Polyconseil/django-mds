import * as urljoin from "url-join";
import settings from "../settings";

export function buildUrl(...parts: string[]): string {
  let url = urljoin(settings.urls.apiBaseUrl, ...parts);
  if (url[url.length - 1] !== "/") {
    url = url + "/";
  }
  return url;
}
