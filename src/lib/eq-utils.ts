import turkeyJson from "./assets/turkey.json" with { type: "json" };

export interface GeometryJson {
  type: string
  name: string
  crs: Crs
  features: Feature[]
}

export interface Crs {
  type: string
  properties: Properties
}

export interface Properties {
  name: string
}

export interface Feature {
  type: string
  properties: Properties2
  geometry: Geometry
}

export interface Properties2 {
  GID_2: string
  GID_0: string
  COUNTRY: string
  GID_1: string
  NAME_1: string
  NL_NAME_1: string
  NAME_2: string
  VARNAME_2: string
  NL_NAME_2: string
  TYPE_2: string
  ENGTYPE_2: string
  CC_2: string
  HASC_2: string
}

export interface Geometry {
  type: string
  coordinates: number[][][][]
}

const geometryJson = turkeyJson as GeometryJson;

export function getAffectedProvinces(magnitude: number, lat: number, lng: number) {
  const affectedProvinces: Set<string> = new Set();
  const maxDistance = Math.exp(magnitude * 0.666 + 1.6); // i found it on reddit its good enough

  geometryJson.features.forEach((feature) => {
    const provinceLat = feature.geometry.coordinates[0][0][0][1];
    const provinceLng = feature.geometry.coordinates[0][0][0][0];
    const distance = getDistance(lat, lng, provinceLat, provinceLng);
    if (distance <= maxDistance) {
      affectedProvinces.add(feature.properties.NAME_1);
    }
  });

  return Array.from(affectedProvinces);
}

function getDistance(lat1: number, lng1: number, lat2: number, lng2: number) {
  const R = 6371; // Radius of the Earth in km
  const dLat = toRadians(lat2 - lat1);
  const dLng = toRadians(lng2 - lng1);
  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos(toRadians(lat1)) * Math.cos(toRadians(lat2)) *
    Math.sin(dLng / 2) * Math.sin(dLng / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return R * c; // Distance in km
}

function toRadians(degrees: number) {
  return degrees * (Math.PI / 180);
}

console.log(getAffectedProvinces(5, 35.6342005, 31.157176));
