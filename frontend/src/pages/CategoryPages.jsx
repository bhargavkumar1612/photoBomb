import React, { useState, useEffect } from "react";
import Masonry from 'react-masonry-css';
import api from "../services/api";
import PhotoItem from "../components/PhotoItem";
import Lightbox from "../components/Lightbox";

const CategoryPage = ({ category, title, description }) => {
    const [photos, setPhotos] = useState([]);
    const [loading, setLoading] = useState(true);
    const [lightboxPhoto, setLightboxPhoto] = useState(null);

    useEffect(() => {
        fetchPhotos();
    }, [category]);

    const fetchPhotos = async () => {
        try {
            setLoading(true);
            // For now, we'll fetch all photos and filter client-side
            // TODO: Update API to support tag filtering
            const response = await api.get('/photos');

            // Filter photos that have tags matching the category
            // This is a placeholder - actual filtering should happen on backend
            setPhotos(response.data.photos || []);
        } catch (error) {
            console.error(`Failed to fetch ${category} photos`, error);
        } finally {
            setLoading(false);
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

    return (
        <div style={{ padding: '20px' }}>
            <div style={{ marginBottom: '30px' }}>
                <h1 style={{ fontSize: '2rem', marginBottom: '10px' }}>{title}</h1>
                <p style={{ color: '#6b7280', fontSize: '1rem' }}>{description}</p>
            </div>

            {photos.length === 0 ? (
                <div style={{
                    textAlign: 'center',
                    padding: '60px 20px',
                    color: '#6b7280'
                }}>
                    <p style={{ fontSize: '1.1rem', marginBottom: '10px' }}>
                        No {category} photos found
                    </p>
                    <p style={{ fontSize: '0.9rem' }}>
                        Upload photos and they will be automatically categorized
                    </p>
                </div>
            ) : (
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
            )}

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

// Export specific category pages
export const AnimalsPage = () => (
    <CategoryPage
        category="animals"
        title="Animals"
        description="Photos containing animals, pets, and wildlife"
    />
);

export const DocumentsPage = () => (
    <CategoryPage
        category="documents"
        title="Documents"
        description="Receipts, invoices, ID cards, and other documents"
    />
);

export const NaturePage = () => (
    <CategoryPage
        category="nature"
        title="Nature & Places"
        description="Beaches, mountains, forests, cities, and scenic views"
    />
);
