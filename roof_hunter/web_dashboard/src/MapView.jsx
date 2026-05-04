import { useEffect, useState } from 'react';
import { MapContainer, TileLayer, Marker } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import markerIcon2x from 'leaflet/dist/images/marker-icon-2x.png';
import markerIcon from 'leaflet/dist/images/marker-icon.png';
import markerShadow from 'leaflet/dist/images/marker-shadow.png';

/* Default marker images break under Vite unless paths are explicit */
const defaultIcon = L.icon({
  iconRetinaUrl: markerIcon2x,
  iconUrl: markerIcon,
  shadowUrl: markerShadow,
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41],
});
L.Marker.mergeOptions({ icon: defaultIcon });

/**
 * Street-level Leaflet view — pair with GET /imagery or POST /property lat/lng.
 */
export default function MapView({
  center = [35.4676, -97.5164],
  zoom = 18,
  markerPosition = [35.4676, -97.5164],
}) {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) {
    return (
      <div
        className="map-view-skeleton"
        style={{ height: 320, width: '100%', borderRadius: 12 }}
        aria-hidden
      />
    );
  }

  return (
    <div
      className="map-view-wrap"
      style={{ height: 320, width: '100%', borderRadius: 12, overflow: 'hidden' }}
    >
      <MapContainer
        center={center}
        zoom={zoom}
        style={{ height: '100%', width: '100%' }}
        scrollWheelZoom
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <Marker position={markerPosition} />
      </MapContainer>
    </div>
  );
}
