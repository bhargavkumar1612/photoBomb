
import React, { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import api from "../services/api";
import Lightbox from "../components/Lightbox";

const PersonDetailPage = () => {
    const { id } = useParams();
    const navigate = useNavigate();
    const [person, setPerson] = useState(null);
    const [loading, setLoading] = useState(true);
    const [photos, setPhotos] = useState([]);
    const [isEditing, setIsEditing] = useState(false);
    const [newName, setNewName] = useState("");
    const [lightboxPhoto, setLightboxPhoto] = useState(null);

    useEffect(() => {
        fetchPersonDetails();
    }, [id]);

    const fetchPersonDetails = async () => {
        try {
            const response = await api.get(`/people/${id}`);
            setPerson(response.data);
            setNewName(response.data.name || "");

            const photosResponse = await api.get(`/people/${id}/photos`);
            setPhotos(photosResponse.data);

        } catch (error) {
            console.error("Failed to fetch person", error);
            if (error.response && error.response.status === 404) {
                navigate("/people");
            }
        } finally {
            setLoading(false);
        }
    };

    const handleSaveName = async () => {
        try {
            await api.patch(`/people/${id}`, { name: newName });
            setPerson(prev => ({ ...prev, name: newName }));
            setIsEditing(false);
        } catch (error) {
            console.error("Failed to update name", error);
        }
    };

    if (loading) {
        return (
            <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
                <div className="loader">Loading...</div>
            </div>
        );
    }

    if (!person) return null;

    return (
        <div style={{ padding: '20px' }}>
            <button
                onClick={() => navigate("/people")}
                style={{
                    border: 'none',
                    background: 'none',
                    cursor: 'pointer',
                    color: '#6b7280',
                    marginBottom: '20px',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '5px'
                }}
            >
                &uarr; Back to People
            </button>

            <div style={{ display: 'flex', alignItems: 'center', gap: '20px', marginBottom: '30px' }}>
                <div style={{
                    width: '100px',
                    height: '100px',
                    borderRadius: '50%',
                    overflow: 'hidden',
                    backgroundColor: '#e5e7eb'
                }}>
                    {person.cover_photo_url && (
                        <img
                            src={person.cover_photo_url}
                            alt={person.name}
                            style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                        />
                    )}
                </div>

                <div>
                    {isEditing ? (
                        <div style={{ display: 'flex', gap: '10px' }}>
                            <input
                                type="text"
                                value={newName}
                                onChange={(e) => setNewName(e.target.value)}
                                style={{ padding: '8px', borderRadius: '4px', border: '1px solid #d1d5db', fontSize: '1.2rem' }}
                            />
                            <button onClick={handleSaveName} style={{ padding: '8px 15px', backgroundColor: '#4f46e5', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}>Save</button>
                            <button onClick={() => setIsEditing(false)} style={{ padding: '8px 15px', backgroundColor: 'transparent', border: '1px solid #d1d5db', borderRadius: '4px', cursor: 'pointer' }}>Cancel</button>
                        </div>
                    ) : (
                        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                            <h1 style={{ fontSize: '2rem', margin: 0 }}>{formatName(person.name)}</h1>
                            <button
                                onClick={() => setIsEditing(true)}
                                style={{ border: 'none', background: 'none', cursor: 'pointer', color: '#6b7280' }}
                                title="Rename"
                            >
                                &#9998;
                            </button>
                        </div>
                    )}
                    <div style={{ color: '#6b7280' }}>
                        {person.face_count} photos
                    </div>
                </div>
            </div>

            <div style={{ borderTop: '1px solid #e5e7eb', paddingTop: '20px' }}>
                {photos.length === 0 ? (
                    <p style={{ fontStyle: 'italic', color: '#6b7280' }}>
                        No photos found for this person.
                    </p>
                ) : (
                    <div style={{
                        display: 'grid',
                        gridTemplateColumns: 'repeat(auto-fill, minmax(150px, 1fr))',
                        gap: '15px'
                    }}>
                        {photos.map(photo => (
                            <div key={photo.photo_id} style={{ aspectRatio: '1', overflow: 'hidden', borderRadius: '8px', cursor: 'pointer' }} onClick={() => setLightboxPhoto(photo)}>
                                <img
                                    src={photo.thumb_urls.thumb_256}
                                    alt={photo.caption || "Photo"}
                                    style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                                    loading="lazy"
                                />
                            </div>
                        ))}
                    </div>
                )}
            </div>

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

// Helper to clean up display name
const formatName = (name) => {
    if (!name) return "Unnamed Person";
    // Check if it matches the default pattern "Person [8-char-hex]"
    const defaultPattern = /^Person [0-9a-f]{8}$/i;
    if (defaultPattern.test(name)) {
        return "Unnamed Person";
    }
    return name;
};

export default PersonDetailPage;
