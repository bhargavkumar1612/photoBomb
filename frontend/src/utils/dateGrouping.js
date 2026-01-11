export const groupPhotosByDate = (photos) => {
    if (!photos || photos.length === 0) return [];

    // Day/Relative grouping (default)
    const groups = {};
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);
    const sevenDaysAgo = new Date(today);
    sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7);
    const startOfMonth = new Date(today.getFullYear(), today.getMonth(), 1);

    photos.forEach(photo => {
        const date = new Date(photo.taken_at || photo.uploaded_at);
        const dateStr = date.toDateString(); // "Fri Jan 11 2026"

        let label = '';
        if (dateStr === today.toDateString()) {
            label = 'Today';
        } else if (dateStr === yesterday.toDateString()) {
            label = 'Yesterday';
        } else {
            // "January 14, 2025"
            label = date.toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' });
        }

        if (!groups[label]) groups[label] = [];
        groups[label].push(photo);
    });

    const priorityLabels = ['Today', 'Yesterday', 'This Week', 'This Month'];
    const groupList = Object.keys(groups).map(label => ({ label, photos: groups[label] }));

    groupList.sort((a, b) => {
        const idxA = priorityLabels.indexOf(a.label);
        const idxB = priorityLabels.indexOf(b.label);
        if (idxA !== -1 && idxB !== -1) return idxA - idxB;
        if (idxA !== -1) return -1;
        if (idxB !== -1) return 1;

        // Parse date from long string format "Friday, January 10, 2025"
        const dateA = new Date(a.photos[0].taken_at || a.photos[0].uploaded_at);
        const dateB = new Date(b.photos[0].taken_at || b.photos[0].uploaded_at);
        return dateB - dateA;
    });

    return groupList;
};

export const groupPhotosByMonth = (photos) => {
    if (!photos || photos.length === 0) return [];

    const groups = {};
    photos.forEach(photo => {
        const date = new Date(photo.taken_at || photo.uploaded_at);
        const label = date.toLocaleDateString('en-US', { month: 'long', year: 'numeric' });
        if (!groups[label]) groups[label] = [];
        groups[label].push(photo);
    });

    return Object.keys(groups)
        .map(label => ({ label, photos: groups[label] }))
        .sort((a, b) => new Date(b.label) - new Date(a.label));
};

export const groupPhotosByYear = (photos) => {
    if (!photos || photos.length === 0) return [];

    const groups = {};
    photos.forEach(photo => {
        const date = new Date(photo.taken_at || photo.uploaded_at);
        const label = date.getFullYear().toString();
        if (!groups[label]) groups[label] = [];
        groups[label].push(photo);
    });

    return Object.keys(groups)
        .map(label => ({ label, photos: groups[label] }))
        .sort((a, b) => parseInt(b.label) - parseInt(a.label));
};
