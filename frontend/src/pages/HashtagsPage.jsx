
import React, { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import Masonry from 'react-masonry-css';
import api from "../services/api";
import { Hash } from "lucide-react";

const HashtagsPage = () => {
    const [tags, setTags] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetchHashtags();
    }, []);

    const fetchHashtags = async () => {
        try {
            const response = await api.get("/hashtags");
            setTags(response.data);
        } catch (error) {
            console.error("Failed to fetch document tags", error);
        } finally {
            setLoading(false);
        }
    };

    const breakpointColumns = {
        default: 4,
        1400: 3,
        900: 2,
        600: 1
    };

    // Helper to get a semi-random but consistent vibrant color based on string
    const getVibrantColor = (str) => {
        const colors = [
            'linear-gradient(135deg, #667eea 0%, #764ba2 100%)', // Indigo/Purple
            'linear-gradient(135deg, #ff9a9e 0%, #fad0c4 100%)', // Pink
            'linear-gradient(135deg, #a1c4fd 0%, #c2e9fb 100%)', // Blue
            'linear-gradient(135deg, #84fab0 0%, #8fd3f4 100%)', // Green/Teal
            'linear-gradient(135deg, #fccb90 0%, #d57eeb 100%)', // Orange/Purple
            'linear-gradient(135deg, #e0c3fc 0%, #8ec5fc 100%)', // Lavender
            'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)', // Pink/Red
            'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)', // Cyan
        ];
        let hash = 0;
        for (let i = 0; i < str.length; i++) {
            hash = str.charCodeAt(i) + ((hash << 5) - hash);
        }
        return colors[Math.abs(hash) % colors.length];
    };

    if (loading) {
        return (
            <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh', background: '#f8fafc' }}>
                <div className="loader" style={{ fontSize: '1.2rem', color: '#64748b' }}>Discovering hashtags...</div>
            </div>
        );
    }

    return (
        <div style={{ padding: '30px', background: '#f8fafc', minHeight: '100vh' }}>
            <div style={{ marginBottom: '40px' }}>
                <h1 style={{
                    fontSize: '42px',
                    fontWeight: '900',
                    letterSpacing: '-1.5px',
                    color: '#0f172a',
                    marginBottom: '8px'
                }}>Hashtags</h1>
                <p style={{ color: '#64748b', fontSize: '1.1rem', fontWeight: '500' }}>
                    Visual intelligence at work. Your world, categorized by hashtag.
                </p>
            </div>

            {tags.length === 0 ? (
                <div style={{
                    textAlign: 'center',
                    padding: '100px 40px',
                    background: 'white',
                    borderRadius: '24px',
                    boxShadow: '0 10px 25px -5px rgba(0,0,0,0.05)'
                }}>
                    <Hash size={64} color="#e2e8f0" style={{ marginBottom: '20px' }} />
                    <p style={{ fontSize: '1.2rem', color: '#64748b', fontWeight: '600' }}>No hashtags found yet.</p>
                    <p style={{ color: '#94a3b8' }}>Upload photos, identities, or animals to begin.</p>
                </div>
            ) : (
                <Masonry
                    breakpointCols={breakpointColumns}
                    className="my-masonry-grid"
                    columnClassName="my-masonry-grid_column"
                >
                    {tags.map((tag) => (
                        <Link
                            key={tag.tag_id}
                            to={`/hashtags/tag/${tag.tag_id}`}
                            style={{ textDecoration: 'none', color: 'inherit', display: 'block', marginBottom: '24px' }}
                        >
                            <div style={{
                                position: 'relative',
                                background: getVibrantColor(tag.name),
                                borderRadius: '24px',
                                padding: '30px',
                                minHeight: '180px',
                                display: 'flex',
                                flexDirection: 'column',
                                justifyContent: 'space-between',
                                boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)',
                                transition: 'all 0.4s cubic-bezier(0.4, 0, 0.2, 1)',
                                cursor: 'pointer',
                                overflow: 'hidden'
                            }}
                                onMouseOver={(e) => {
                                    e.currentTarget.style.transform = 'translateY(-8px) scale(1.02)';
                                    e.currentTarget.style.boxShadow = '0 30px 40px -10px rgba(0, 0, 0, 0.2)';
                                }}
                                onMouseOut={(e) => {
                                    e.currentTarget.style.transform = 'translateY(0) scale(1)';
                                    e.currentTarget.style.boxShadow = '0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)';
                                }}
                            >
                                {/* Decorative Background Pattern */}
                                <div style={{
                                    position: 'absolute',
                                    top: '-20px',
                                    right: '-20px',
                                    fontSize: '120px',
                                    opacity: '0.1',
                                    fontWeight: '900',
                                    color: 'white',
                                    pointerEvents: 'none',
                                    userSelect: 'none'
                                }}>
                                    #
                                </div>

                                <div style={{ position: 'relative', zIndex: 1 }}>
                                    <div style={{
                                        backgroundColor: 'rgba(255,255,255,0.2)',
                                        width: '48px',
                                        height: '48px',
                                        borderRadius: '14px',
                                        display: 'flex',
                                        justifyContent: 'center',
                                        alignItems: 'center',
                                        marginBottom: '20px',
                                        backdropFilter: 'blur(10px)',
                                        border: '1px solid rgba(255,255,255,0.3)'
                                    }}>
                                        <Hash color="white" size={24} />
                                    </div>
                                    <h2 style={{
                                        fontSize: '28px',
                                        fontWeight: '800',
                                        color: 'white',
                                        margin: 0,
                                        wordBreak: 'break-all',
                                        lineHeight: '1.1'
                                    }}>
                                        #{tag.name}
                                    </h2>
                                </div>

                                <div style={{
                                    display: 'flex',
                                    justifyContent: 'space-between',
                                    alignItems: 'flex-end',
                                    position: 'relative',
                                    zIndex: 1
                                }}>
                                    <span style={{
                                        backgroundColor: 'rgba(255,255,255,0.2)',
                                        color: 'white',
                                        padding: '6px 14px',
                                        borderRadius: '20px',
                                        fontSize: '0.85rem',
                                        fontWeight: '700',
                                        backdropFilter: 'blur(5px)',
                                        border: '1px solid rgba(255,255,255,0.2)'
                                    }}>
                                        {tag.count} items
                                    </span>

                                    {tag.cover_photo_url && (
                                        <div style={{
                                            width: '60px',
                                            height: '60px',
                                            borderRadius: '12px',
                                            border: '3px solid white',
                                            overflow: 'hidden',
                                            boxShadow: '0 4px 10px rgba(0,0,0,0.1)'
                                        }}>
                                            <img src={tag.cover_photo_url} alt="" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                                        </div>
                                    )}
                                </div>
                            </div>
                        </Link>
                    ))}
                </Masonry>
            )}

            <style>{`
                .my-masonry-grid {
                    display: -webkit-box;
                    display: -ms-flexbox;
                    display: flex;
                    margin-left: -24px;
                    width: auto;
                }
                .my-masonry-grid_column {
                    padding-left: 24px;
                    background-clip: padding-box;
                }
            `}</style>
        </div>
    );
};

export default HashtagsPage;
