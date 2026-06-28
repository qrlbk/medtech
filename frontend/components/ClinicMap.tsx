"use client";

import { MapContainer, Marker, Popup, TileLayer } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { formatKzt } from "@/lib/api";
import type { PriceOffer } from "@/lib/types";

// Inline SVG pin so we don't depend on bundled marker image assets.
const icon = L.divIcon({
  className: "",
  html: `<div style="background:#1f6fd4;width:18px;height:18px;border-radius:50% 50% 50% 0;transform:rotate(-45deg);border:2px solid white;box-shadow:0 1px 4px rgba(0,0,0,.4)"></div>`,
  iconSize: [18, 18],
  iconAnchor: [9, 18],
});

export default function ClinicMap({ offers }: { offers: PriceOffer[] }) {
  const points = offers.filter((o) => o.clinic.lat != null && o.clinic.lon != null);
  if (points.length === 0) {
    return (
      <div className="grid h-full place-items-center rounded-xl bg-slate-100 text-sm text-slate-400">
        Нет координат клиник для отображения на карте
      </div>
    );
  }
  const center: [number, number] = [points[0].clinic.lat!, points[0].clinic.lon!];
  return (
    <MapContainer center={center} zoom={11} scrollWheelZoom={false} style={{ height: "100%" }}>
      <TileLayer
        attribution='&copy; OpenStreetMap'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      {points.map((o) => (
        <Marker key={o.price_id} position={[o.clinic.lat!, o.clinic.lon!]} icon={icon}>
          <Popup>
            <strong>{o.clinic.name}</strong>
            <br />
            {formatKzt(o.price_kzt)}
            <br />
            {o.clinic.address}
          </Popup>
        </Marker>
      ))}
    </MapContainer>
  );
}
