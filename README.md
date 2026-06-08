# wbadawi.info

Personal executive platform for **Waleed Albadawi** — Enterprise Technology Executive, Head of Integration at Saudi Investment Bank.

A premium, restrained, board-ready brand site for CIO / CTO / Group Technology Executive positioning across Saudi banking and GCC enterprise.

## Design

- **Theme:** light, executive (paper + deep navy + steel gray, minimal antique gold accent)
- **Display:** `Fraunces` (italic display serif accents only)
- **Heading:** `Inter Tight`
- **Body:** `Inter`
- **Layout:** generous whitespace, subtle fades, no gimmicks
- **Inspiration:** McKinsey / Microsoft Executive Bio / Fortune 500 CIO profile

## Stack

- **Pure HTML/CSS/JS** — no build tools, no dependencies
- **GitHub Pages** — deployed via GitHub Actions
- **Google Fonts** — Fraunces + Inter Tight + Inter
- **Inline SVG icons**

## Structure

```
├── index.html          # Home (hero, pillars, impact, philosophy, boardroom capabilities, perspective teaser)
├── about.html          # Profile (executive identity, philosophy, trajectory)
├── experience.html     # Experience (executive-language progression)
├── projects.html       # Strategic Initiatives (case studies)
├── expertise.html      # Boardroom Capabilities (8 disciplines + domain depth)
├── perspective.html    # CIO Perspective (5 executive articles)
├── resume.html         # Executive Brief (credentials, downloadable PDF)
├── contact.html        # Contact (premium executive layout)
├── blog.html           # Insights (working notes)
├── technical.html      # Engineering Lab
├── 404.html            # Custom 404 page
├── CNAME               # Custom domain
├── robots.txt          # Search engine directives
├── sitemap.xml         # XML sitemap
├── assets/
│   ├── css/style.css   # Design system — navy/white/steel/gold
│   ├── js/main.js      # Header, mobile menu, reveal animations
│   └── img/favicon.svg # Executive monogram
└── .github/workflows/  # GitHub Actions deployment
```

## Editing

All content lives in plain HTML files. Update the relevant `.html` file, commit, push. GitHub Actions deploys within ~60 seconds.

### Key files to personalize

- **`index.html`** — hero, pillars, impact metrics, capabilities grid
- **`about.html`** — profile narrative, leadership philosophy, trajectory
- **`experience.html`** — career timeline (executive language)
- **`expertise.html`** — boardroom capabilities + domain depth
- **`projects.html`** — strategic initiatives + institutional significance
- **`perspective.html`** — CIO Perspective articles
- **`resume.html`** — executive brief + downloadable PDF (uses `window.print()`)
- **`contact.html`** — direct contact + areas of engagement

### Design tokens (`assets/css/style.css`)

- **Palette:** `--navy-900`, `--paper`, `--steel-*`, `--gold-500`, `--accent`
- **Fonts:** `--font-display` (Fraunces), `--font-heading` (Inter Tight), `--font-body` (Inter)
- **Spacing:** `--space-xs` through `--space-2xl`
- **Sections:** `.section--alt`, `.section--soft`, `.section--dark`

## Custom Domain

Configured for `wbadawi.info` via `CNAME`. DNS must point to GitHub Pages IPs.

## Future Additions

- Executive portrait photo (replace the monogram in `hero__portrait`)
- Downloadable PDF brief generated from `resume.html` print stylesheet
- Speaking / panel section populated as engagements happen
- Recommendations populated as collected (LinkedIn export)
- Multilingual surface (Arabic) for GCC executive audiences
- Press / media kit page
- Long-form CIO Perspective articles on individual pages with deeper SEO

## License

MIT
