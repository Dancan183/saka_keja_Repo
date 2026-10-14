# Design System

**Saka Keja**

This document defines the visual design system, UI components and user experience of the Saka Keja web application. Every value in it is taken from the stylesheet and templates in the project, so it describes what the site looks like today.

Version 1.0 | October 2026 | Maintainer: [your name]

---

## 1. Design principles

| Principle | What it means | Where you see it |
|---|---|---|
| Mobile first and light | Most users are on a phone with limited data, so pages stay small and need no downloaded fonts | System font stack, server-rendered pages, lazy-loaded photos, layouts checked at 390 px wide |
| Trust through clarity | People are dealing with strangers and money, so the interface is honest and never claims more than is true | Messages say what really happened, a code is never reported as sent when it was not, private reviews are marked with a lock |
| One clear action per screen | The main thing to do is the green button; everything else is quieter | Green primary buttons, outline buttons for secondary actions, red only for danger |
| Calm and consistent | One green, one container width, the same corner radii everywhere | Shared base template, one set of colour tokens |
| Accessible by default | Text is readable, every field has a label, and nothing depends on colour alone | Contrast checked in section 2.4, status words beside colours, labelled star picker |
| Plain language | Short sentences in everyday English; Kiswahili is planned | Messages such as Enter your phone number first and Failed to send code. Please try again. |
| Always give feedback | Every action gets a visible response, and a locked control explains itself | Success and error banners, countdown on Resend code, a locked code field that unlocks only after an SMS is sent |

**Voice and tone**

- Speak to the person directly (Your review was posted), not about the system.
- Say what to do next, not only what went wrong.
- No jargon, no blame, no exclamation marks except to welcome someone or thank them.
- Prices read `KSh 12,000 / month`; dates read `12 Oct 2026`; phone numbers are stored as `+254712345678`.

---

## 2. Color palette

### 2.1 Brand colors

These are the CSS variables defined once in `base.html`.

| Token | Hex | Use |
|---|---|---|
| `--green` | `#1b7f4b` | Primary: buttons, links, badges, icons, focus and success accents |
| `--dark` | `#1f2933` | Body text, navigation bar, strong headings |
| `--forest` | `#0f3d2a` | Footer background and the dark end of the hero image gradient |
| `--grey` | `#f3f4f6` | Panels, search bar, empty photo slots, disabled fills |
| `--red` | `#c0392b` | Errors, delete buttons, form error text |
| `--star` | `#f5b301` | Rating stars only |
| `--container` | `1280px` | Maximum content width (a size, kept with the colours for convenience) |

### 2.2 Supporting colors

These are written directly in the CSS rather than as variables.

| Hex | Use |
|---|---|
| `#ffffff` | Page and card background |
| `#e5e7eb` | Card and divider borders |
| `#c4c9d0` | Input borders |
| `#6b7280` | Muted text: captions, help text, dates |
| `#4b5563` | Secondary text in the hero and testimonials |
| `#e3f6ec` / `#11522f` | Success and Vacant: background and text |
| `#fde8e6` / `#7a1f16` | Error and Occupied: background and text |
| `#f6fbf8` | Highlight for unread inquiries and hover on area cards |
| `#f3faf6` | Top of the hero background gradient |
| `#2f7d57` to `#0f3d2a` | Hero image placeholder gradient |
| `#6fcf97` | Icons on the dark footer |
| `#d1d5db` | Empty (unfilled) stars |
| `#ff7a8a` | The heart in the footer line |

### 2.3 Rules of use

- **Green means go or good:** the main action, a positive status, a verified state. Do not use it for decoration beside other greens.
- **Red is for trouble only:** errors, deleting, and the Occupied status.
- **Never rely on color alone:** Vacant and Occupied always carry the words, and errors always carry a message.
- **Yellow is for ratings only.**
- **Use the tokens.** A new screen should use the variables above; add a new color only when the palette cannot do the job, and record it here.

### 2.4 Contrast check

Ratios use the WCAG formula. Normal text needs at least 4.5:1; icons and large graphics need 3:1.

| Pair | Ratio | Result |
|---|---|---|
| Body text, `--dark` on white | 14.76:1 | Pass |
| White on `--dark` (navigation) | 14.76:1 | Pass |
| White on `--green` (buttons) | 5.02:1 | Pass |
| `--green` on white (links) | 5.02:1 | Pass |
| White on `--red` (delete button) | 5.44:1 | Pass |
| `--red` on white (error text) | 5.44:1 | Pass |
| Muted `#6b7280` on white | 4.83:1 | Pass |
| Muted `#6b7280` on `--grey` | 4.39:1 | Below 4.5:1 for small text. Use `#5f6672` for text on grey |
| Secondary `#4b5563` on white | 7.56:1 | Pass |
| Success text on success background | 8.21:1 | Pass |
| Error text on error background | 8.78:1 | Pass |
| Footer text (white at 72%) on `--forest` | 7.13:1 | Pass |
| White on `--forest` (footer headings) | 12.20:1 | Pass |
| `#6fcf97` icons on `--forest` | 6.42:1 | Pass |
| `--star` stars on white | 1.85:1 | Below 3:1. Show the number or a label beside the stars |

The WhatsApp button used to be white on `#25d366` (1.98:1). It now uses the standard green button with the WhatsApp icon, so it passes. Disabled text is exempt from the contrast rule.

---

## 3. Typography

### 3.1 Typeface

```
font-family: system-ui, sans-serif;
```

The site uses the phone's or computer's own interface font (for example Roboto on Android, Segoe UI on Windows, San Francisco on Apple devices). Nothing is downloaded, so text appears immediately even on slow mobile data. Icons come from Font Awesome 6.5.1, loaded from a CDN; every icon sits beside a text label or has an `aria-label`, so the page still works if icons fail to load.

### 3.2 Type scale

| Role | Size | Weight | Line height | Example |
|---|---|---|---|---|
| Hero heading | 2rem to 3.6rem, scales with screen width | 700 | 1.1 | Find Your Dream Home |
| Page title (h1) | 2rem (browser default) | 700 | 1.5 | Create an account |
| Profile title | 1.5rem | 700 | 1.5 | A landlord's name |
| Section heading (h2) | 1.5rem (browser default) | 700 | 1.5 | Latest vacant houses |
| Logo | 1.15rem in the bar, 1.3rem in the footer | 700 | 1.5 | Saka Keja |
| Card title | 1.05rem | 700 | 1.5 | A house title |
| Price | 1.1rem | 700 | 1.5 | KSh 12,000 / month |
| Body text | 1rem (16px) | 400 | 1.5 | Descriptions, messages |
| Field label | 1rem | 600 | 1.5 | Phone number |
| Small text | 0.85rem to 0.9rem | 400 | 1.5 | Captions, dates, help text |
| Top bar and footer fine print | 0.8rem to 0.85rem | 400 | 1.5 | Contact bar, copyright |
| Badge | 0.75rem | 400 | 1.5 | New |

### 3.3 Rules

- Use two weights for emphasis: 600 for labels and names, 700 for headings, prices and the logo.
- Keep body text at 16 px or larger; never go below 12 px (0.75rem), which is used only for badges.
- Left-align text. Center only short blocks such as empty states and the section heading of testimonials.
- Use sentence case for headings and buttons (Send inquiry, not SEND INQUIRY).
- Keep lines of reading text to about 70 characters: forms are capped at 420 px wide.

---

## 4. UI components

### 4.1 Component list

| Component | Purpose | Key specification |
|---|---|---|
| Top contact bar | Email, phone, address and social links | White, 0.8rem text, 1px bottom border; the address hides below 700 px |
| Navigation bar | Site-wide links and the logged-in menu | `--dark` background, white 16px links, logo at the left, links wrap on small screens |
| Hero | Headline, buttons, search | Pale green gradient, two columns on desktop, image first on phones |
| Search panel | Find houses by area, type, price, bedrooms, bathrooms | White card, 16px radius, 5 fields and a button; stacks to 2 and then 1 column |
| House card | One listing in a grid | 1px border, 8px radius, 180px photo, title, area, rent, facts |
| Footer | Brand, links and contact | `--forest` background, 5 columns on desktop, down to 1 on phones |
| Buttons | Actions | See 4.2 |
| Form fields | Data entry | See 4.3 |
| Messages | Feedback after an action | See 4.4 |
| Badges and status pills | Counts and states | See 4.5 |
| Cards for inquiries, reviews and steps | Grouped content | 1px border, 8px to 14px radius, 0.8rem to 1.4rem padding |
| Rating stars | Show and collect ratings | See 4.6 |
| Avatar | A person's initial or photo | Round, `--green` fill, white initial, photo covers it when present |
| Phone verification block | Prove a phone number on sign-up | See 4.7 |
| Pagination | Move between result pages | Previous and Next links with Page X of Y |
| Empty state | Nothing to show yet | Short sentence and the next action as a link or button |

### 4.2 Buttons

| Variant | Look | Use |
|---|---|---|
| Primary | `--green` fill, white text, 6px radius, padding 0.5rem 1rem (about 40 px tall) | The main action: Search, Register, Send inquiry |
| Outline | White fill, green text and 1px green border | A secondary action beside a primary one: Send a new code, Mark as read, How It Works |
| Danger | `--red` fill, white text | Delete |
| Text link | Green or red underlined text | Edit, Delete on a review, Report |
| Disabled | 55% opacity and a `not-allowed` cursor (set in the phone verification block) | A step that is not ready, such as Verify Code before a code is sent |

A page has one primary button. Destructive buttons ask for confirmation and are sent by POST.

### 4.3 Form fields

| Part | Specification |
|---|---|
| Label | Above the field, 600 weight, always present |
| Input, select, textarea | Full width up to 420 px, 0.5rem padding, 1px `#c4c9d0` border, 6px radius |
| Help text | 0.9rem muted text under the field |
| Error | `--red` text under the field, one clear sentence |
| Disabled | `#f3f4f6` fill, `#9ca3af` text, `not-allowed` cursor |
| Spacing | 0.9rem between fields |

### 4.4 Messages

| Type | Look | Example |
|---|---|---|
| Success | `#e3f6ec` background, `#11522f` text, 6px radius | Your review was posted. |
| Error | `#fde8e6` background, `#7a1f16` text | We could not send the email just now. |
| Neutral note | `--grey` background | Only tenants who sent this landlord an inquiry can leave a review. |

Messages sit at the top of the page, above the page title, and say what happened and what to do next.

### 4.5 Badges and status pills

| Name | Look | Use |
|---|---|---|
| Badge | `--green` fill, white 0.75rem text, fully rounded | New, unread counts |
| Vacant | `#e3f6ec` fill, `#11522f` text, fully rounded | An available house |
| Occupied | `#fde8e6` fill, `#7a1f16` text, fully rounded | A taken house |
| Verified badge | Light green pill with a tick | A confirmed phone number |

### 4.6 Rating stars

| Version | Specification |
|---|---|
| Display | Five Font Awesome stars in `--star`; empty stars `#d1d5db`; rounded to the nearest half; the text alternative reads, for example, 4.5 out of 5 stars |
| Summary | Stars, the average in bold and the number of reviews, with a link to the profile |
| Input | Five radio buttons shown as 2rem stars, highest on the right; hover and selection fill all stars up to the chosen one; keyboard focus shows a green outline; works without JavaScript |

### 4.7 Phone verification block

1. Phone field with the green Confirm Phone Number button beside it (below it on phones).
2. Verification code field and Verify Code button underneath, both **disabled and greyed out** until the server confirms an SMS was sent.
3. A status line (green for success, red for problems) under the code field.
4. A green Verified badge appears after a correct code; editing the phone number removes it and locks the code field again.

---

## 5. Layout, spacing and responsive behavior

| Item | Value |
|---|---|
| Content width | 1280px maximum, centered, with 1rem side padding; the top bar, navigation, hero, content and footer all share it so their edges line up |
| Spacing steps | 0.2, 0.3, 0.5, 0.6, 0.8, 1, 1.5, 2 and 3 rem |
| Corner radius | 6px inputs, buttons and messages; 8px cards and panels; 12px to 14px profile, call-to-action and testimonial cards; 16px search panel; 24px hero image; fully rounded for pills and avatars |
| Shadows | Only on things that float or group content: the search panel, the property card on the hero image, and, very lightly, inquiry cards and the inquiry form panels. Everything else is flat |
| Breakpoints | 420, 480, 600, 640, 700, 800, 900 and 1000 px |
| Grids | House cards fill automatically with a 250px minimum; footer is 5 columns, then 3, 2 and 1; search panel is 5 fields and a button, then 2 columns, then 1 |
| Smallest supported width | 390 px, with no sideways scrolling |

---

## 6. User experience patterns and accessibility

### 6.1 Patterns

| Pattern | How it works here |
|---|---|
| Progressive unlocking | A control stays locked until the step before it succeeds, and the page says why (the code field, the Register button) |
| Honest feedback | Success and failure messages match what really happened; sending failures are shown, never hidden |
| Confirm before deleting | Delete asks for confirmation and uses POST so a link cannot delete anything |
| Helpful empty states | A short sentence and a button for the next step, for example Add your first house |
| Quick contact | Phone numbers are tap-to-call links; inbox rows have Call, WhatsApp and Email buttons |
| Privacy cues | Private pages carry a lock icon and a sentence saying who can see them |
| Safe defaults | Landlords see a clear note when they cannot send an inquiry; tenants cannot open landlord pages |

### 6.2 Accessibility checklist

| Item | Status |
|---|---|
| Every field has a visible label | Done |
| Photos have text alternatives; icons beside text are hidden from screen readers | Done |
| Ratings have a spoken text alternative | Done |
| Star picker works with a keyboard and shows focus | Built, still to be tested by hand |
| Body text and buttons meet 4.5:1 contrast | Done (section 2.4) |
| Status is never shown by color alone | Done |
| Pages work at 390 px with no sideways scrolling | Checked on the registration page and a landlord profile; the landing page was viewed in screenshots; other pages not yet checked |
| Touch targets at least 44 px | Not yet: buttons are about 40 px tall |

### 6.3 Known gaps and next steps

1. Muted text on a grey background is 4.39:1; use `#5f6672` for text on grey.
2. Stars alone are below 3:1; keep the number or a label beside them.
3. Raise button padding so touch targets reach 44 px.
4. Add a visible focus style for every button and link, not just the star picker.
5. Move repeated colors such as `#e5e7eb`, `#6b7280` and `#e3f6ec` into variables.
6. Move the CSS from the base template into a static file once it grows further.
7. There is no dark mode and no reduced-motion setting yet.
