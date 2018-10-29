import { buildUrl } from "./commons";

export interface IServiceAreasRequest {
  area: any;
  begin_date: string;
}

export async function getServiceAreas(requestBody: IServiceAreasRequest) {
  const request = new Request(buildUrl("service_area"), {
    body: JSON.stringify(requestBody),
    headers: {
      "Content-Type": "application/json"
    },
    method: "POST",
    mode: "cors"
  });
  return await (await fetch(request)).json();
}
