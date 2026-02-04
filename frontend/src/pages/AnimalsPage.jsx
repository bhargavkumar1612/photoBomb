
import React, { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import api from "../services/api";

const AnimalsPage = () => {
    const [animals, setAnimals] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetchAnimals();
    }, []);

    const fetchAnimals = async () => {
        try {
            const response = await api.get("/animals");
            setAnimals(response.data);
        } catch (error) {
            console.error("Failed to fetch animals", error);
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
                <h1 style={{ fontSize: '24px', fontWeight: 'bold' }}>Animals</h1>
            </div>

            <p style={{ color: '#666', marginBottom: '30px' }}>
                Photos containing pets and other animals, grouped automatically.
            </p>

            {animals.length === 0 ? (
                <div style={{ textAlign: 'center', padding: '40px', color: '#666' }}>
                    <p>No animals identified yet.</p>
                    <p>Upload photos with animals to see them here.</p>
                </div>
            ) : (
                <div style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fill, minmax(150px, 1fr))',
                    gap: '20px'
                }}>
                    {animals.map((animal) => (
                        <Link
                            key={animal.animal_id}
                            to={`/animals/${animal.animal_id}`}
                            style={{ textDecoration: 'none', color: 'inherit' }}
                        >
                            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                                <div style={{
                                    width: '120px',
                                    height: '120px',
                                    borderRadius: '50%',
                                    overflow: 'hidden',
                                    marginBottom: '10px',
                                    backgroundColor: '#e5e7eb',
                                    boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)'
                                }}>
                                    {animal.cover_photo_url ? (
                                        <img
                                            src={animal.cover_photo_url}
                                            alt={animal.name || "Unknown"}
                                            style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                                        />
                                    ) : (
                                        <div style={{ width: '100%', height: '100%', display: 'flex', justifyContent: 'center', alignItems: 'center', color: '#9ca3af' }}>
                                            🐾
                                        </div>
                                    )}
                                </div>
                                <div style={{ fontWeight: '500', textAlign: 'center' }}>
                                    {animal.name || "Unnamed Animal"}
                                </div>
                                <div style={{ fontSize: '0.8rem', color: '#6b7280' }}>
                                    {animal.count} photos
                                </div>
                            </div>
                        </Link>
                    ))}
                </div>
            )}
        </div>
    );
};

export default AnimalsPage;
