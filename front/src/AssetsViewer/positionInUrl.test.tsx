import { parsePosition, stringifyPosition } from "./positionInUrl";

it("parses position (when possible) from the URL", () => {
  expect(parsePosition("48.8821014,2.3354308,14z")).toEqual({
    latlng: { lat: 48.8821014, lng: 2.3354308 },
    zoom: 14
  });
  expect(parsePosition("48.8821014,2.3354308")).toEqual({
    latlng: { lat: 48.8821014, lng: 2.3354308 }
  });
  expect(parsePosition("@crap")).toEqual(null);
  expect(parsePosition("crap")).toEqual(null);
});

it("stringifies position for the URL", () => {
  expect(
    stringifyPosition({
      latlng: { lat: 48.8821014, lng: 2.3354308 },
      zoom: 14
    })
  ).toEqual("48.8821014,2.3354308,14z");
  expect(
    stringifyPosition({
      latlng: { lat: 48.8821014, lng: 2.3354308 }
    })
  ).toEqual("48.8821014,2.3354308");
  expect(stringifyPosition(null)).toEqual("");
});
