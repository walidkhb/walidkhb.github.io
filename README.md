# wbadawi.info

Personal website for Waleed Albadawi — enterprise technology leader, integration architect, and digital transformation specialist.

## Stack

- **Pure HTML/CSS/JS** — no build tools, no dependencies
- **GitHub Pages** — hosted and deployed automatically via GitHub Actions
- **Google Fonts** — Playfair Display (headings) + Inter (body)
- **SVG icons** — inline, no external icon libraries

## Structure

```
├── index.html          # Home — hero, capabilities, featured work, CTA
├── about.html          # About — background, philosophy, values
├── experience.html     # Experience — career timeline, domain expertise
├── projects.html       # Initiatives — strategic programs & open source
├── expertise.html      # Expertise — skills, technologies, methodologies
├── resume.html         # Resume/CV — printable, comprehensive
├── contact.html        # Contact — details, areas of interest
├── blog.html           # Insights — thought leadership perspectives
├── 404.html            # Custom 404 page
├── CNAME               # Custom domain configuration
├── robots.txt          # Search engine directives
├── sitemap.xml         # XML sitemap for SEO
├── assets/
│   ├── css/style.css   # Complete design system & styles
│   ├── js/main.js      # Navigation, scroll effects, animations
│   └── img/favicon.svg # SVG favicon
└── .github/
    └── workflows/
        └── pages.yml   # GitHub Actions deployment workflow
```

## Setup

1. **Fork or clone** this repository
2. **Enable GitHub Pages**: Settings > Pages > Source: GitHub Actions
3. **Custom domain** (optional): Update `CNAME` with your domain, then configure DNS:
   - `A` record → `185.199.108.153` (and .109, .110, .111)
   - `CNAME` record for `www` → `walidkhb.github.io`

## Updating Content

All content is in plain HTML files. To update:

1. Edit the relevant `.html` file
2. Commit and push to `master`
3. GitHub Actions deploys automatically (typically under 60 seconds)

### Key files to personalize:
- **`index.html`** — Hero text, capability cards, featured initiatives
- **`about.html`** — Background story, philosophy, values
- **`experience.html`** — Career timeline entries
- **`expertise.html`** — Skill tags and categories
- **`resume.html`** — CV content (also supports Print/PDF)
- **`contact.html`** — Contact details and social links

### Design tokens (in `assets/css/style.css`):
- Colors: `--color-primary`, `--color-accent`, etc.
- Fonts: `--font-heading`, `--font-body`
- Spacing: `--space-xs` through `--space-2xl`

## Custom Domain

The site is configured for `wbadawi.info` via the `CNAME` file. DNS must point to GitHub Pages IPs. See [GitHub's custom domain docs](https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site) for details.

## Future Enhancements

- Add a profile photo to the hero and about sections
- Expand blog/insights with full article pages
- Add dark mode toggle
- Add LinkedIn and other social media links
- Add project screenshots and case study detail pages
- Implement a contact form via Formspree or similar
- Add structured data (JSON-LD) for enhanced search results
- Add Open Graph images for social sharing previews

## License

MIT
