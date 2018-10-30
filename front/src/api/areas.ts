import { buildUrl } from "./commons";

export interface IServiceAreasRequest {
  area: any;
  begin_date: string;
}

export async function postServiceArea(requestBody: IServiceAreasRequest) {
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

export async function deleteServiceArea(areaId: string) {
  const request = new Request(buildUrl("service_area/", areaId), {
    headers: {
      "Content-Type": "application/json"
    },
    method: "DELETE",
    mode: "cors"
  });
  return await fetch(request);
}