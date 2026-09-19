# Adversarial design contract — Solo + AI Berlin

Scope: public landing (`/`), legal pages (`/legal/impressum`, `/legal/privacy`, `/legal/terms`), application form, desktop 1440 and mobile 390. Intentionally no dark-mode inversion: the product is a paper-and-ink editorial object.

## Hierarchy and type

- Exactly one document `h1` on the landing: “Build your business with AI.”
- Display type is a serif (Georgia / Iowan / Palatino). Interface type is a system sans.
- Desktop measure for body copy stays under ~70 characters.
- Section eyebrows, ticket, and price number stay subordinate to the H1.

## Alignment, spacing, density

- 8px rhythm. Section padding 92 desktop / 60 mobile.
- Cards share one radius and one border colour.
- No orphaned 1px gaps between header, hero, and facts.

## Navigation and actions

- Sticky header with home brand, in-page links, and one primary Apply control.
- Primary CTA wording stays honest: apply and pay, place not confirmed.
- Mobile sticky apply bar is 44px+, does not cover the form once the form is on screen, and does not cover footer legal links (footer has extra padding).

## Legal and trust

- Footer always exposes Privacy, Pilot terms, Impressum, Contact.
- Impressum is German statutory text (`lang="de"`), matching DataTalks.Club / AI Shipping Labs operator details.
- Legal pages reuse the landing chrome; they are not draft yellow boxes.

## Interaction and accessibility

- Visible 3px focus ring on every control.
- Interactive targets ≥ 44px on viewports ≤ 780px (nav CTA, form buttons, FAQ summaries, footer links, checkboxes).
- One H1; skip link; reduced-motion disables smooth scroll and transforms.
- No horizontal overflow at 360, 390, 768, 1024, 1440.

## Content fidelity

- €59 total, 10 & 24 November 2026, 18:30–21:00 CET, Mitte / Prenzlauer Berg unconfirmed.
- Host name: Alexey Grigorev.
- Payment does not guarantee a place.
