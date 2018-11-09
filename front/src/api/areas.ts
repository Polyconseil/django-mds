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
      display: "Pricing zone 3 scooters",
      id: "3"
    },
    {
      display: "Pricing zone 4 scooters",
      id: "4"
    },
    {
      display: "Pricing zone 1 cars",
      id: "5"
    },
    {
      display: "Pricing zone 2 cars",
      id: "6"
    },
    {
      display: "Pricing zone 3 cars",
      id: "7"
    },
    {
      display: "Pricing zone 4 cars",
      id: "8"
    },
    {
      display: "Low emission area",
      id: "9"
    },
    {
      display: "Restricted area",
      id: "10"
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
