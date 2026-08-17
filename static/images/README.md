# Images

Replace SVG placeholders with optimized product and project photos.

## Current placeholders

SVG files are temporary brand-styled stand-ins so the site works offline.

## Production checklist

- Export WebP or compressed JPEG/PNG
- Provide width/height attributes (already in templates)
- Keep `loading="lazy"` on below-the-fold images
- Keep descriptive `alt` text
- Hero poster: prefer a real showroom photo named `hero-poster.jpg` and update `index.html` paths

Suggested naming:

```
product-{slug}.webp
gallery-{n}.webp
collection-{slug}.webp
hero-poster.webp
```
