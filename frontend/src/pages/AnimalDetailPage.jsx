
import React, { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import Masonry from 'react-masonry-css';
import { ChevronLeft, Edit2, Check, X } from "lucide-react";
import api from "../services/api";
import PhotoItem from "../components/PhotoItem";
import Lightbox from "../components/Lightbox";

const AnimalDetailPage = () => {
    const { id } = useParams();
    const navigate = useNavigate();
    const [animal, setAnimal] = useState(null);
    const [photos, setPhotos] = useState([]);
    const [loading, setLoading] = useState(true);
    const [isEditing, setIsEditing] = useState(false);
    const [newName, setNewName] = useState("");
    const [lightboxPhoto, setLightboxPhoto] = useState(null);

    useEffect(() => {
        fetchAnimalDetails();
        fetchAnimalPhotos();
    }, [id]);

    const fetchAnimalDetails = async () => {
        try {
            const response = await api.get(`/animals/${id}`);
            setAnimal(response.data);
            setNewName(response.data.name || "");
        } catch (error) {
            console.error("Failed to fetch animal details", error);
        }
    };

    const fetchAnimalPhotos = async () => {
        try {
            const response = await api.get(`/animals/${id}/photos`);
            setPhotos(response.data);
        } catch (error) {
            console.error("Failed to fetch animal photos", error);
        } finally {
            setLoading(false);
        }
    };

    const handleUpdateName = async () => {
        try {
            const response = await api.patch(`/animals/${id}`, { name: newName });
            setAnimal(response.data);
            setIsEditing(false);
        } catch (error) {
            console.error("Failed to update name", error);
        }
    };

    const breakpointColumns = {
        default: 4,
        1400: 3,
        900: 2,
        600: 2
    };

    if (loading) {
        return (
            <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
                <div className="loader">Loading...</div>
            </div>
        );
    }

    if (!animal) {
        return <div style={{ padding: '20px' }}>Animal not found.</div>;
    }

    return (
        <div style={{ padding: '20px' }}>
            <button
                onClick={() => navigate("/animals")}
                style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                    padding: '8px 0',
                    background: 'none',
                    border: 'none',
                    cursor: 'pointer',
                    color: '#4f46e5',
                    fontWeight: '500',
                    marginBottom: '20px'
                }}
            >
                <ChevronLeft size={20} />
                Back to Animals
            </button>

            <div style={{ display: 'flex', alignItems: 'center', gap: '24px', marginBottom: '40px' }}>
                <div style={{
                    width: '120px',
                    height: '120px',
                    borderRadius: '50%',
                    overflow: 'hidden',
                    backgroundColor: '#e5e7eb',
                    flexShrink: 0
                }}>
                    {animal.cover_photo_url ? (
                        <img
                            src={animal.cover_photo_url}
                            alt={animal.name}
                            style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                        />
                    ) : (
                        <div style={{ width: '100%', height: '100%', display: 'flex', justifyContent: 'center', alignItems: 'center', fontSize: '2rem' }}>
                            🐾
                        </div>
                    )}
                </div>

                <div style={{ flexGrow: 1 }}>
                    {isEditing ? (
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <input
                                type="text"
                                value={newName}
                                onChange={(e) => setNewName(e.target.value)}
                                style={{
                                    fontSize: '24px',
                                    fontWeight: 'bold',
                                    padding: '4px 8px',
                                    borderRadius: '4px',
                                    border: '1px solid #4f46e5',
                                    outline: 'none'
                                }}
                                autoFocus
                            />
                            <button onClick={handleUpdateName} style={{ color: '#059669', background: 'none', border: 'none', cursor: 'pointer' }}>
                                <Check size={24} />
                            </button>
                            <button onClick={() => setIsEditing(false)} style={{ color: '#dc2626', background: 'none', border: 'none', cursor: 'pointer' }}>
                                <X size={24} />
                            </button>
                        </div>
                    ) : (
                        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                            <h1 style={{ fontSize: '32px', fontWeight: 'bold' }}>{animal.name || "Unnamed Animal"}</h1>
                            <button
                                onClick={() => setIsEditing(true)}
                                style={{ color: '#6b7280', background: 'none', border: 'none', cursor: 'pointer' }}
                            >
                                <Edit2 size={20} />
                            </button>
                        </div>
                    )}
                    <p style={{ color: '#6b7280', marginTop: '4px' }}>{photos.length} Photos</p>
                </div>
            </div>

            <Masonry
                breakpointCols={breakpointColumns}
                className="my-masonry-grid"
                columnClassName="my-masonry-grid_column"
            >
                {photos.map(photo => (
                    <PhotoItem
                        key={photo.photo_id}
                        photo={photo}
                        onLightbox={setLightboxPhoto}
                    />
                ))}
            </Masonry>

            {lightboxPhoto && (
                <Lightbox
                    photo={lightboxPhoto}
                    photos={photos}
                    onClose={() => setLightboxPhoto(null)}
                    onNavigate={setLightboxPhoto}
                />
            )}
        </div>
    );
};

export default AnimalDetailPage;
