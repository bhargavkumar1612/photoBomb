
import React, { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import api from "../services/api";

const PeoplePage = () => {
    const [people, setPeople] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetchPeople();
    }, []);

    const fetchPeople = async () => {
        try {
            const response = await api.get("/people");
            setPeople(response.data);
        } catch (error) {
            console.error("Failed to fetch people", error);
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
        <div style={{ padding: '20px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
                <h1 style={{ fontSize: '24px', fontWeight: 'bold' }}>People</h1>
            </div>

            {people.length === 0 ? (
                <div style={{ textAlign: 'center', padding: '40px', color: '#666' }}>
                    <p>No people found yet.</p>
                    <p>Upload photos with faces to see them here.</p>
                </div>
            ) : (
                <div style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fill, minmax(150px, 1fr))',
                    gap: '20px'
                }}>
                    {people.map((person) => (
                        <Link
                            key={person.person_id}
                            to={`/people/${person.person_id}`}
                            style={{ textDecoration: 'none', color: 'inherit' }}
                        >
                            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                                <div style={{
                                    width: '120px',
                                    height: '120px',
                                    borderRadius: '50%',
                                    overflow: 'hidden',
                                    marginBottom: '10px',
                                    backgroundColor: '#e5e7eb'
                                }}>
                                    {person.cover_photo_url ? (
                                        <img
                                            src={person.cover_photo_url}
                                            alt={person.name || "Unknown"}
                                            style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                                        />
                                    ) : (
                                        <div style={{ width: '100%', height: '100%', display: 'flex', justifyContent: 'center', alignItems: 'center', color: '#9ca3af' }}>
                                            No Image
                                        </div>
                                    )}
                                </div>
                                <div style={{ fontWeight: '500', textAlign: 'center' }}>
                                    {formatName(person.name)}
                                </div>
                                <div style={{ fontSize: '0.8rem', color: '#6b7280' }}>
                                    {person.face_count} photos
                                </div>
                            </div>
                        </Link>
                    ))}
                </div>
            )}
        </div>
    );
};

// Helper to clean up display name
const formatName = (name) => {
    if (!name) return "Unnamed Person";
    const defaultPattern = /^Person [0-9a-f]{8}$/i;
    if (defaultPattern.test(name)) {
        return "Unnamed Person";
    }
    return name;
};

export default PeoplePage;
