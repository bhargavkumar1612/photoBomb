import React, { useState, useEffect } from "react";
import Masonry from 'react-masonry-css';
import api from "../services/api";
import PhotoItem from "../components/PhotoItem";
import Lightbox from "../components/Lightbox";

const CategoryPage = ({ category, title, description }) => {
    const [tags, setTags] = useState([]);
    const [selectedTag, setSelectedTag] = useState(null);
    const [photos, setPhotos] = useState([]);
    const [loading, setLoading] = useState(true);
    const [viewMode, setViewMode] = useState('loading'); // 'loading', 'tags', 'photos'
    const [lightboxPhoto, setLightboxPhoto] = useState(null);

    useEffect(() => {
        // Reset state on category change
        setTags([]);
        setSelectedTag(null);
        setPhotos([]);
        setViewMode('loading');
        fetchTags();
    }, [category]);

    const fetchTags = async () => {
        try {
            setLoading(true);
            const response = await api.get('/tags', { params: { category } });
            const fetchedTags = response.data || [];

            if (fetchedTags.length > 0) {
                setTags(fetchedTags);
                setViewMode('tags');
            } else {
                // Fallback to all photos if no tags found
                console.log(`No tags found for ${category}, fetching all photos`);
                await fetchPhotos(null); // Fetch all for category
            }
        } catch (error) {
            console.error(`Failed to fetch ${category} tags`, error);
            // Fallback
            await fetchPhotos(null);
        } finally {
            setLoading(false);
        }
    };

    const fetchPhotos = async (tagName) => {
        try {
            setLoading(true);
            setViewMode('photos');

            // If tagName is provided, filter by it.
            // If tagName is null ("All"), we fetch everything (pending category filter on list_photos)
            const params = tagName ? { tag: tagName } : {};

            const response = await api.get('/photos', { params });
            const allPhotos = response.data.photos || [];

            setPhotos(allPhotos);

        } catch (error) {
            console.error("Failed to fetch photos", error);
        } finally {
            setLoading(false);
        }
    };

    const handleTagClick = (tag) => {
        setSelectedTag(tag);
        fetchPhotos(tag.name);
    };

    const handleBackToTags = () => {
        setSelectedTag(null);
        setPhotos([]);
        setViewMode('tags');
    };

    const breakpointColumns = {
        default: 4,
        1400: 3,
        900: 2,
        600: 2
    };

    if (loading && viewMode === 'loading') {
        return (
            <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
                <div className="loader">Loading...</div>
            </div>
        );
    }

    return (
        <div style={{ padding: '20px' }}>
            <div style={{ marginBottom: '30px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                    <h1 style={{ fontSize: '2rem', marginBottom: '10px' }}>
                        {selectedTag ? `${title}: ${selectedTag.name}` : title}
                    </h1>
                    <p style={{ color: '#6b7280', fontSize: '1rem' }}>
                        {selectedTag ? `Photos tagged with ${selectedTag.name}` : description}
                    </p>
                </div>
                {viewMode === 'photos' && tags.length > 0 && (
                    <button
                        onClick={handleBackToTags}
                        style={{
                            padding: '8px 16px',
                            backgroundColor: '#e5e7eb',
                            border: 'none',
                            borderRadius: '20px',
                            cursor: 'pointer',
                            fontWeight: '500'
                        }}
                    >
                        ← Back to Categories
                    </button>
                )}
            </div>

            {viewMode === 'tags' && (
                <div style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fill, minmax(140px, 1fr))',
                    gap: '24px',
                    padding: '10px'
                }}>
                    {/* "All" Bubble */}
                    <div
                        onClick={() => handleTagClick({ name: null })}
                        style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', cursor: 'pointer' }}
                    >
                        <div style={{
                            width: '120px', height: '120px', borderRadius: '50%',
                            backgroundColor: '#f3f4f6', display: 'flex', justifyContent: 'center', alignItems: 'center',
                            marginBottom: '10px', boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)'
                        }}>
                            <span style={{ fontSize: '1.2rem', fontWeight: 'bold', color: '#4b5563' }}>All</span>
                        </div>
                        <span style={{ fontWeight: '500' }}>All Photos</span>
                    </div>

                    {tags.map(tag => (
                        <div
                            key={tag.tag_id}
                            onClick={() => handleTagClick(tag)}
                            style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', cursor: 'pointer' }}
                        >
                            <div style={{
                                width: '120px', height: '120px', borderRadius: '50%', overflow: 'hidden',
                                marginBottom: '10px', boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
                                backgroundColor: '#e5e7eb'
                            }}>
                                {tag.cover_photo_url ? (
                                    <img
                                        src={tag.cover_photo_url}
                                        alt={tag.name}
                                        style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                                    />
                                ) : (
                                    <div style={{ width: '100%', height: '100%', display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
                                        <span style={{ fontSize: '2rem' }}>#</span>
                                    </div>
                                )}
                            </div>
                            <div style={{ fontWeight: '500', textTransform: 'capitalize' }}>{tag.name}</div>
                            <div style={{ fontSize: '0.8rem', color: '#6b7280' }}>{tag.count} photos</div>
                        </div>
                    ))}
                </div>
            )}

            {viewMode === 'photos' && (
                <>
                    {photos.length === 0 && !loading ? (
                        <div style={{ textAlign: 'center', padding: '60px 20px', color: '#6b7280' }}>
                            <p style={{ fontSize: '1.1rem' }}>No photos found.</p>
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
                </>
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
export const NaturePage = () => (
    <CategoryPage
        category="nature"
        title="Nature & Places"
        description="Beaches, mountains, forests, cities, and scenic views"
    />
);
