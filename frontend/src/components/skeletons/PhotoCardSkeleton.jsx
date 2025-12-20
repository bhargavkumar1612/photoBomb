import './Skeleton.css'

export default function PhotoCardSkeleton() {
    // Random height for masonry effect simulation
    const height = Math.floor(Math.random() * (350 - 200 + 1)) + 200

    return (
        <div className="photo-skeleton-card">
            <div
                className="photo-skeleton-image skeleton-shimmer"
                style={{ height: `${height}px` }}
            />
        </div>
    )
}
