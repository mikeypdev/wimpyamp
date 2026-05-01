# WimPyAmp Website

This directory contains the WimPyAmp product website source files.

## Quick Start

```bash
# Preview locally
make website-serve

# Then open http://localhost:8000
```

## File Structure

```
website/
├── index.html          # Main product page
├── styles.css          # All styling
├── images/             # Screenshots and assets
│   ├── hero-screenshot.png   # Main hero screenshot
│   ├── skin-1.png            # Gallery skin 1
│   └── skin-2.png            # Gallery skin 2
└── README.md           # This file
```

## Updating Content

### Version Numbers
Edit `index.html` and update the version in the Download section:
```html
<p class="download-version">Version 1.0.0</p>
```

### Download Links
Update the GitHub Releases links in the Download section:
```html
<a href="https://github.com/mikeypdev/wimpyamp/releases/download/v1.0.0/WimPyAmp-macOS.zip">
```

### Screenshots
1. Capture new screenshots from the app
2. Save to `images/` directory
3. Update references in `index.html`

### Adding New Skins to Gallery
Copy the `.gallery-item` block and update:
```html
<div class="gallery-item">
    <img src="images/skin-4.png" alt="Your skin name">
    <span class="gallery-caption">Skin Name</span>
</div>
```

## Deployment

The website deploys automatically when you push to `main`:

```bash
git add website/
git commit -m "Update website"
git push
```

GitHub Actions will deploy to the `gh-pages` branch automatically.

## GitHub Pages Setup

1. Go to repository Settings → Pages
2. Under "Source", select: **Deploy from a branch**
3. Branch: **gh-pages** → Folder: **/** (root)
4. Click Save

Your site will be live at: `https://mikeypdev.github.io/wimpyamp`

## Custom Domain (Optional)

To use a custom domain:

1. Add a `CNAME` file in this directory with your domain:
   ```
   wimpyamp.com
   ```

2. Configure DNS with your domain provider:
   - CNAME: `www` → `mikeypdev.github.io`
   - A records: (GitHub's IPs from their docs)

3. In GitHub Settings → Pages → Custom domain, enter your domain

## Styling

Colors are defined as CSS variables in `styles.css`:

```css
:root {
    --bg-dark: #1a1a1a;
    --accent-green: #00ff00;
    --accent-orange: #ff9900;
    --accent-blue: #00ccff;
}
```

## Local Development

```bash
# Start local server
make website-serve

# Or manually:
cd website
python3 -m http.server 8000

# Edit files and refresh browser
```

## Troubleshooting

**Images not showing?**
- Check file paths are relative: `images/filename.png`
- Verify files exist in `website/images/`

**Styles not loading?**
- Check `styles.css` is in `website/` directory
- Clear browser cache

**Deploy not working?**
- Check GitHub Actions tab for errors
- Verify GitHub Pages is enabled in Settings
