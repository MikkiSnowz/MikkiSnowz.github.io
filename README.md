# mikkisnowz.github.io

Personal portfolio for **Sahatpat Anankatham (Mikki)**, built with [Astro](https://astro.build) on Node.js.

## Sections

Hero · About · Projects · Leadership · Education · Skills · Contact

All content lives in [`src/data/resume.ts`](src/data/resume.ts). Edit that file to update the site.

## Animations

- Staggered hero entrance, floating gradient blobs, a typing role line and a waving hand
- Scroll-triggered reveals (fade, blur, slide and scale) on every section
- Count-up stats, a timeline rail that fills as you scroll, an infinite skills marquee
- Cursor-following spotlight on cards, 3D tilt on project cards, a scroll progress bar
- The nav highlights the section you're viewing
- Respects `prefers-reduced-motion`

## Development

Requires Node.js 22.12+.

```sh
npm install
npm run dev       # http://localhost:4321
npm run build     # outputs static site to dist/
npm run preview   # serve the built site
```

## Deploying to mikkisnowz.github.io

The site is hosted for free on GitHub Pages. The workflow in
`.github/workflows/deploy.yml` builds and deploys it on every push to `main`.

1. Name the repository `MikkiSnowz.github.io` (**Settings → General → Repository name**).
2. Make sure a `main` branch exists and is the default branch.
3. Go to **Settings → Pages** and set **Source** to **GitHub Actions**.
4. Push to `main` (or run the workflow from the **Actions** tab). The site goes live at
   https://mikkisnowz.github.io.

### Using a custom domain later

1. Buy a domain and set `site` in `astro.config.mjs` to it.
2. Add a `public/CNAME` file containing the domain.
3. Enter the domain in **Settings → Pages → Custom domain** and add the DNS records GitHub shows.
