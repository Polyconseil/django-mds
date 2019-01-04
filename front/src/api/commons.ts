import * as urljoin from "url-join";
import settings from "../settings";

export function buildUrl(...parts: string[]): string {
  let url = urljoin(settings.urls.apiBaseUrl, ...parts);
  if (url[url.length - 1] !== "/") {
    url = url + "/";
  }
  return url;
}

export function prepRequest(parts: string | string[], options: RequestInit | undefined = {}): Request {
  let url;
  if (typeof parts === "string") {
    url = buildUrl(parts);
  } else {
    url = buildUrl(...parts);
  }

  const request = new Request(url, {
    method: "GET",
    mode: "cors",
    ...options,
    headers: {
      "Authorization": "Bearer " + settings.urls.apiAccessToken,
      "Content-Type": "application/json",
      ...options.headers
    },
  });

  return request;
}