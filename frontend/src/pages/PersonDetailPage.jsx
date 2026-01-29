
import React, { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import api from "../services/api";

const PersonDetailPage = () => {
    const { id } = useParams();
    const navigate = useNavigate();
    const [person, setPerson] = useState(null);
    const [loading, setLoading] = useState(true);
    const [photos, setPhotos] = useState([]); // This needs an endpoint to fetch photos by person
    const [isEditing, setIsEditing] = useState(false);
    const [newName, setNewName] = useState("");

    useEffect(() => {
        fetchPersonDetails();
    }, [id]);

    const fetchPersonDetails = async () => {
        try {
            const response = await api.get(`/people/${id}`);
            setPerson(response.data);
            setNewName(response.data.name || "");

            // TODO: Fetch photos for this person
            // For now, we don't have an endpoint for photos by person explicitly, 
            // but we can query specific photos if we implemented search/filter.
            // Let's assume we add query param to /photos?person_id=...
            // Or a new endpoint /people/:id/photos

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
                            <h1 style={{ fontSize: '2rem', margin: 0 }}>{person.name || "Unknown"}</h1>
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
                <p style={{ fontStyle: 'italic', color: '#6b7280' }}>
                    Note: Photo list implementation requires /people/:id/photos endpoint.
                </p>
                {/* 
                  Grid of photos matching this person would go here.
                  Need backend support first.
                */}
            </div>
        </div>
    );
};

export default PersonDetailPage;
