# sahatpat.anankatham.com

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

## Deploying to sahatpat.anankatham.com

The site is static, so any static host works. A GitHub Pages workflow is included
(`.github/workflows/deploy.yml`) and runs on every push to `main`.

1. Buy the domain `anankatham.com` from a registrar (Cloudflare, Namecheap, Porkbun, etc.).
2. In the GitHub repo, go to **Settings → Pages** and set **Source** to **GitHub Actions**.
3. `public/CNAME` already contains `sahatpat.anankatham.com`. In **Settings → Pages → Custom domain**, enter the same address.
4. At your registrar, add one DNS record:
   - Type `CNAME`, name `sahatpat`, value `mikkisnowz.github.io`
5. Once DNS has propagated, tick **Enforce HTTPS**.

Prefer Cloudflare Pages, Vercel or Netlify? Connect the repo, use build command
`npm run build` and output directory `dist`, then add the custom domain in their dashboard.
