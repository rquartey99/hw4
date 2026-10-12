# Design Log — Problem 10

**Goal:** make Campus Customs look cooler and more Yale-themed, so visitors enjoy the site and stay longer.

## What I asked for

| Request | What changed | Why it should keep people around |
|---|---|---|
| **More Yale-themed, "cooler" look** | Yale-blue navbar, hero and footer with a gold trim line, serif headings (Libre Baskerville), a gold "Boola Boola! · For God, for Country, and for Yale" motto, and a Yale-blue stripe when you hover over a product card. | Feels like a real Yale shop rather than a generic template. People trust a store that looks polished and "for them," and a design they recognize invites them to keep browsing. |
| **Handsome Dan sprites where feasible** | An original cartoon bulldog in four moods (happy, wink, thinking, sleepy). He appears as: the logo in the navbar and the browser-tab icon; a big bobbing Dan with a speech bubble in the hero; the "Dan's picks" heading; the **chat assistant** (button, header, reply avatars, and a thinking face while typing); the Log in, Create Account and Account cards; and sleepy or thinking Dan on the 404, "no results" and loading screens. The chatbot now introduces itself as Handsome Dan. | A mascot gives the site personality and makes it memorable. Chatting with "Dan" feels friendlier than a faceless assistant, so more people try it. Dan on the dead ends (404, no matches, loading) turns a moment where people usually leave into a light one that points them back to shopping. |
| **Residential college / professional school logos in the background** | A faint repeating pattern of shields labeled with all 14 residential colleges (BF, BK, BR, DC, ES, GH, JE, MC, PC, PM, SY, SM, TD, TC) and 12 professional schools (SOM, LAW, MED, ART, DIV, MUS, NUR, SPH, ARC, ENG, ENV, DRA), plus paw prints. It's navy on light pages and white on the navy bars, kept at 7–9% opacity so text stays easy to read. | Students, alumni and families spot *their* college or school, which creates a personal connection and a reason to linger. It also reinforces the college and school merchandise the shop sells. |

## Notes
- **Original artwork, not official logos:** Handsome Dan's official artwork and the colleges' real shields are Yale trademarks, so the bulldog and the shields are original designs *inspired by* them. The footer says so.
- **Where the files are:**
  - `frontend/src/components/Dan.tsx` (the sprite)
  - `frontend/scripts/make_crests.py`, which generates `public/crests.svg` and `public/crests-light.svg`
  - the "Yale theme" section at the end of `frontend/src/index.css`
- **Accessibility:** Dan's bobbing stops for visitors who turn on reduced motion. The decorative sprites are hidden from screen readers.
