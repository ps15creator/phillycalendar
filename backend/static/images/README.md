# Philly Calendar — Static images

Use this folder to add Philadelphia team logos and landmark photos so the site feels grounded in Philly. The site already uses **inline SVG icons** for landmarks (Liberty Bell, LOVE Park, Art Museum, City Hall) and **initials** for teams (E, P, 76, F, U, 🔔); adding real images here will make it even more recognizable.

---

## Where to get better images

- **Landmark photos (skyline, Liberty Bell, LOVE Park, Art Museum, City Hall):**  
  Search **Unsplash**, **Pexels**, or **Pixabay** for:  
  `Philadelphia skyline`, `Liberty Bell Philadelphia`, `LOVE Park Philadelphia`, `Philadelphia Museum of Art`, `Rocky steps Philadelphia`, `Philadelphia City Hall`.  
  Use high‑resolution, rights‑cleared images and credit the photographer if required by the license.

- **Team logos (Eagles, Phillies, 76ers, Flyers, Union):**  
  Use **official team / league brand resources** (NFL, MLB, NBA, NHL, MLS or each team’s press/brand page). Follow their trademark and usage guidelines.

---

## Header logo (optional)

- **File:** `eagles-logo.png`
- **Used in:** Header, left of “Philly Events Calendar”
- **Suggested size:** ~80×80 px (displayed at 40px height)
- **Usage:** Official Philadelphia Eagles / NFL brand assets per their guidelines.

---

## Hero background (optional)

- **File:** e.g. `hero-philly.jpg` — Philadelphia skyline, Art Museum steps, or Rocky silhouette at sunset.
- **Used in:** Hero banner as a subtle background.
- **How to enable:** In `styles.css`, add to `.hero-bg-image`:
  ```css
  background-image: url(/static/images/hero-philly.jpg);
  ```
- **Suggested:** Use a strong skyline or landmark shot from Unsplash/Pexels (search “Philadelphia skyline” or “Philadelphia sunset”).

---

## Footer “Philly pride” logos (optional)

The footer shows **E** (Eagles), **P** (Phillies), **76** (76ers), **F** (Flyers), **U** (Union), and 🔔 (Liberty Bell). To use real logos:

- Add files such as: `eagles-logo.png`, `phillies-logo.png`, `76ers-logo.png`, `flyers-logo.png`, `union-logo.png`, `liberty-bell.png`.
- In `index.html`, inside each `.footer-pride-item` link, add an `<img src="/static/images/…" alt="…">` and keep the letter/emoji as fallback (or hide it when the image loads).
- Use official team/brand assets per their guidelines.

---

## Landmarks strip

The strip below the hero uses **inline SVG icons** (Liberty Bell, LOVE, Art Museum, City Hall) so no images are required. If you prefer photos instead, you can replace those with `<img>` tags pointing to files in this folder (e.g. `liberty-bell.jpg`, `love-park.jpg`, `art-museum.jpg`, `city-hall.jpg`) and adjust the markup/CSS as needed.

---

*Last updated: 2026-02. See WORK_SPLIT.md for frontend/backend ownership.*
