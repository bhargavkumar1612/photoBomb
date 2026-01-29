
import React, { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import Masonry from 'react-masonry-css';
import { ChevronLeft, Hash } from "lucide-react";
import api from "../services/api";
import PhotoItem from "../components/PhotoItem";
import Lightbox from "../components/Lightbox";

const HashtagDetailPage = () => {
    const { tagId } = useParams();
    const navigate = useNavigate();
    const [tagName, setTagName] = useState("");
    const [photos, setPhotos] = useState([]);
    const [loading, setLoading] = useState(true);
    const [lightboxPhoto, setLightboxPhoto] = useState(null);

    useEffect(() => {
        fetchTagPhotos();
    }, [tagId]);

    const fetchTagPhotos = async () => {
        try {
            // First, get all hashtags to find the one with matching name
            const tagsRes = await api.get("/hashtags");
            const currentTag = tagsRes.data.find(t => t.name === tagId);

            if (!currentTag) {
                console.error("Tag not found");
                setLoading(false);
                return;
            }

            setTagName(currentTag.name);

            // Now fetch photos using the tag's UUID
            const response = await api.get(`/hashtags/${currentTag.tag_id}/photos`);
            setPhotos(response.data);
        } catch (error) {
            console.error("Failed to fetch hashtag photos", error);
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
            <button
                onClick={() => navigate("/hashtags")}
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
                Back to Hashtags
            </button>

            <div style={{ display: 'flex', alignItems: 'center', gap: '20px', marginBottom: '40px' }}>
                <div style={{
                    width: '64px',
                    height: '64px',
                    borderRadius: '12px',
                    backgroundColor: '#e5e7eb',
                    display: 'flex',
                    justifyContent: 'center',
                    alignItems: 'center',
                }}>
                    <Hash size={32} />
                </div>
                <div>
                    <h1 style={{ fontSize: '32px', fontWeight: 'bold', color: '#4f46e5' }}>#{tagName || "Hashtag"}</h1>
                    <p style={{ color: '#6b7280' }}>{photos.length} Photos</p>
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

            {
                lightboxPhoto && (
                    <Lightbox
                        photo={lightboxPhoto}
                        photos={photos}
                        onClose={() => setLightboxPhoto(null)}
                        onNavigate={setLightboxPhoto}
                    />
                )
            }
        </div >
    );
};

export default HashtagDetailPage;
