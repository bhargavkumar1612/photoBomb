# Walkthrough - UI Polish: Horizontal Loader

We have replaced the shimmer effects and spinners with a custom horizontal SVG loader for a cleaner, lightweight loading experience.

## Improvements

### 1. New HorizontalLoader Component
- Created `HorizontalLoader.jsx`: A lightweight SVG animation (3 pulsing dots) that serves as the unified loading indicator.

### 2. Timeline Improvements
- **Photo Loading**: Implemented `PhotoItem` component to handle individual image loading states.
    - Before load: Shows `HorizontalLoader`.
    - After load: Smoothly fades in the image.
- **Initial Fetch**: Updated `PhotoCardSkeleton` to use `HorizontalLoader` instead of the "white tile" shimmer.

### 3. Lightbox Improvements
- Replaced the global spinner with the `HorizontalLoader` centered on the screen while the high-resolution image downloads.

## Visuals
- **Login/Grid**: You will now see the horizontal dots animation instead of blank white cards.
- **Image Click**: The same dots animation appears while the full image loads in Lightbox.
