import { useState, useEffect } from 'react'
import { getImageUrl, revokeImageUrl } from '../services/imageService'

export default function AuthImage({ photoId, type = 'thumbnail', size = 512, alt, className, onClick, style, fallbackSrc }) {
    const [imageUrl, setImageUrl] = useState(null)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState(false)

    useEffect(() => {
        let isMounted = true
        
        const loadImage = async () => {
            setLoading(true)
            setError(false)
            
            try {
                const url = await getImageUrl(photoId, type, size)
                if (isMounted && url) {
                    setImageUrl(url)
                } else if (isMounted) {
                    setError(true)
                }
            } catch (err) {
                if (isMounted) setError(true)
            } finally {
                if (isMounted) setLoading(false)
            }
        }

        loadImage()

        return () => {
            isMounted = false
            // Don't revoke here - we're caching
        }
    }, [photoId, type, size])

    if (loading) {
        return <div className={`${className} loading-placeholder`} style={style}>Loading...</div>
    }

    if (error && fallbackSrc) {
        return <img src={fallbackSrc} alt={alt} className={className} onClick={onClick} style={style} />
    }

    if (error || !imageUrl) {
        return <div className={`${className} error-placeholder`} style={style}>Image unavailable</div>
    }

    return (
        <img 
            src={imageUrl} 
            alt={alt} 
            className={className} 
            onClick={onClick}
            style={style}
            loading="lazy"
        />
    )
}
