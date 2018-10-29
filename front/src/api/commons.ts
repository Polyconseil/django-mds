import * as urljoin from "url-join";

export function buildUrl(...parts: string[]): string {
  return urljoin(process.env.API_BASE_URL || "", ...parts);
}
