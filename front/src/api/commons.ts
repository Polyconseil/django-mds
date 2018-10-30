import * as urljoin from "url-join";

export function buildUrl(...parts: string[]): string {
  let url = urljoin(process.env.REACT_APP_API_BASE_URL || "", ...parts);
  if (url[url.length - 1] !== "/") {
    url = url + "/";
  }
  return url
}
