# Assets Directory

Static assets for the frontend application.

## Structure

```
assets/
├── icons/      # SVG icons, UI icons
├── images/     # Photos, screenshots, illustrations
└── logos/      # Application and brand logos
```

## Usage

### In React Components

```jsx
// Direct path
<img src="/assets/logos/logo.svg" alt="Logo" />

// With public folder
<img src={`${process.env.PUBLIC_URL}/assets/images/hero.jpg`} alt="Hero" />
```

### In CSS

```css
.header {
  background-image: url('/assets/images/background.jpg');
}
```

## File Organization

- **icons/**: Small SVG icons for UI elements (arrows, checkmarks, etc.)
- **images/**: Larger images, photos, screenshots
- **logos/**: Brand logos, application logos (SVG preferred for scalability)

## Template Variables

When generating environments, add application-specific assets:
- `{{APP_LOGO}}` - Main application logo
- `{{APP_FAVICON}}` - Browser favicon
- `{{GENERATED_ICONS}}` - Custom icon set
