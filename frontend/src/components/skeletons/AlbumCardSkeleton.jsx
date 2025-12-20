import './Skeleton.css'

export default function AlbumCardSkeleton() {
    return (
        <div className="album-skeleton-card">
            <div className="album-skeleton-cover skeleton-shimmer" />
            <div className="album-skeleton-info">
                <div className="album-skeleton-line skeleton-shimmer" />
                <div className="album-skeleton-line short skeleton-shimmer" />
            </div>
        </div>
    )
}
