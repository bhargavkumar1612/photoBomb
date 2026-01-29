
import React, { useState, useEffect } from "react";
import { MapContainer, TileLayer, Marker, Popup } from "react-leaflet";
import MarkerClusterGroup from "react-leaflet-cluster";
import "leaflet/dist/leaflet.css";
import L from "leaflet";
import api from "../services/api";

// Fix Leaflet detail: Marker icons are missing by default in webpack/vite environments
import icon from "leaflet/dist/images/marker-icon.png";
import iconShadow from "leaflet/dist/images/marker-shadow.png";

let DefaultIcon = L.icon({
    iconUrl: icon,
    shadowUrl: iconShadow,
    iconSize: [25, 41],
    iconAnchor: [12, 41],
});
L.Marker.prototype.options.icon = DefaultIcon;

const MapPage = () => {
    const [photos, setPhotos] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetchMapPhotos();
    }, []);

    const fetchMapPhotos = async () => {
        try {
            const response = await api.get("/photos/map");
            setPhotos(response.data);
        } catch (error) {
            console.error("Failed to fetch locations", error);
        } finally {
            setLoading(false);
        }
    };

    if (loading) {
        return (
            <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
                <div className="loader">Loading...</div>
            </div>
        );
    }

    return (
        <div style={{ height: "calc(100vh - 60px)", width: "100%" }}>
            <MapContainer
                center={[20, 0]}
                zoom={2}
                scrollWheelZoom={true}
                style={{ height: "100%", width: "100%" }}
            >
                <TileLayer
                    attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                    url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                />

                <MarkerClusterGroup chunkedLoading>
                    {photos.map((photo) => {
                        if (!photo.gps_lat || !photo.gps_lng) return null;
                        return (
                            <Marker
                                key={photo.photo_id}
                                position={[photo.gps_lat, photo.gps_lng]}
                            >
                                <Popup>
                                    <div style={{ textAlign: 'center' }}>
                                        <img
                                            src={photo.thumb_urls.thumb_256}
                                            alt={photo.filename}
                                            style={{
                                                width: '100px',
                                                height: '100px',
                                                objectFit: 'cover',
                                                borderRadius: '4px',
                                                marginBottom: '4px'
                                            }}
                                        />
                                        <div>{photo.location_name || "Unknown Location"}</div>
                                        <div style={{ fontSize: '0.8rem', color: '#666' }}>
                                            {new Date(photo.taken_at).toLocaleDateString()}
                                        </div>
                                    </div>
                                </Popup>
                            </Marker>
                        );
                    })}
                </MarkerClusterGroup>
            </MapContainer>
        </div>
    );
};

export default MapPage;
