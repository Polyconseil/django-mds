import { buildUrl } from "./commons";

export interface IServiceAreasRequest {
  area: any;
  begin_date?: string;
}

export async function getServiceAreas() {
  const request = new Request(buildUrl("service_area"), {
    headers: {
      "Content-Type": "application/json"
    },
    method: "GET",
    mode: "cors"
  });
  return await (await fetch(request)).json();
}

export async function updateServiceArea(
  areaId: string,
  requestBody: IServiceAreasRequest
) {
  const request = new Request(buildUrl("service_area/", areaId), {
    body: JSON.stringify(requestBody),
    headers: {
      "Content-Type": "application/json"
    },
    method: "PATCH",
    mode: "cors"
  });
  return await (await fetch(request)).json();
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

const pricingPoliciesStore = {};

export interface IPolicy {
  display: string;
  id: string;
}

export function getAllPricingPolicies() {
  return Promise.resolve([
    {
      display: "Pricing zone 1 scooters",
      id: "1"
    },
    {
      display: "Pricing zone 2 scooters",
      id: "2"
    },
    {
      display: "Pricing zone A cars",
      id: "3"
    }
  ]);
}

export function getPricingPolicies(areaId: string) {
  return Promise.resolve(pricingPoliciesStore[areaId] || ([] as IPolicy[]));
}

export function postPricingPolicy(areaId: string, policy: IPolicy) {
  pricingPoliciesStore[areaId] = (pricingPoliciesStore[areaId] || []).concat([
    policy
  ]);
  return Promise.resolve(policy);
}

export function removePricingPolicy(areaId: string, policyId: string) {
  pricingPoliciesStore[areaId] = pricingPoliciesStore[areaId].filter(
    (p: IPolicy) => p.id !== policyId
  );
  return Promise.resolve(null);
}
