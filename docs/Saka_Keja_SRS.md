# Software Requirements Specification (SRS)

**Saka Keja** - house hunting made easier in Murang'a County

| | |
|---|---|
| **Version** | 1.0 |
| **Date** | October 2026 |
| **Author** | [your name] |
| **Status** | Draft. MVP is built and tested, and email works; live SMS and the legal pages are still to be connected |
| **Target Launch** | [to be decided; see "Launch blockers" in section 5] |

---

## 1. Product Overview

Saka Keja ("find a house") is a mobile-friendly web platform that connects people looking for a rental home in Murang'a County with landlords who have houses to let. Tenants search vacant houses by area, price and size, see real photos, and message the landlord directly. Landlords list their houses for free and manage everything from their phone.

**How it works**

1. A landlord registers (phone number and email both verified), adds a house with photos, rent and location, and marks it vacant or occupied.
2. A tenant searches by area, price range, property type, bedrooms and bathrooms. No account is needed to browse.
3. The tenant sends an inquiry. The landlord reads it in an inbox and replies by call, WhatsApp or email.
4. After they have been in touch, each can leave a review of the other.

**Where it starts:** Murang'a Town, Mjini, Mukuyu Market and Area 4 near the small gate.

**Platform:** a responsive web application (works on any phone browser), built with Django and hosted on Vercel.

**Not in the MVP:** rent payments, tenancy agreements, in-app chat, maps, native mobile apps.

---

## 2. Problem Statement

People in Murang'a have no single, trustworthy, up-to-date place to find or advertise rental houses. These are the starting assumptions behind the product. They should be confirmed with 10 to 20 short interviews with tenants and landlords before launch.

| Who | Problem today | Effect |
|---|---|---|
| Tenants | Vacant houses are found by word of mouth, by walking around, or through brokers who may charge a fee. Price, photos and condition are unknown until a visit. | Wasted time and transport money, and houses that do not fit the budget |
| Landlords | Vacant houses are advertised with signs and word of mouth, and the calls that come are not filtered by budget or size. | Houses stay empty and rent is lost, and time is spent on unsuitable callers |
| Both | There is no way to tell whether the other side is genuine or reliable, and listings can be fake or out of date. | Low trust and scams |

**Problem statement:** Tenants and landlords in Murang'a lose time and money because finding or advertising a rental house is slow, informal and hard to trust.

---

## 3. Goals

### 3.1 Product goals

| # | Goal |
|---|---|
| G1 | A tenant can find a suitable vacant house in minutes from a phone, using area, price and size filters. |
| G2 | A landlord can list a house with photos in under 10 minutes and keep its status current. |
| G3 | Build trust: every account's email verified (and every landlord's phone too, since SMS costs money), and reviews tied to real contact. |
| G4 | Keep running costs close to zero until the product has traffic. |
| G5 | Protect users' data: no unverified accounts, hashed secrets, private tenant reviews. |

### 3.2 Success metrics

These are proposed targets for the first three months after launch. Agree or adjust them before using them.

| Metric | Proposed target |
|---|---|
| Vacant listings live | 50 |
| Registered landlords | 25 |
| Registered tenants | 300 |
| Inquiries sent per month | 100 |
| Listings whose status was updated in the last 30 days | 70% |
| Inquiries marked as read by the landlord within 24 hours | 60% |
| Review reports looked at within 2 days | 100% |

### 3.3 Non-goals for the MVP

Collecting rent, managing tenancies, verifying title deeds, and serving areas outside Murang'a County.

---

## 4. Target Users

These profiles are assumptions to check during the interviews in section 2.

| User | Who they are | What they need | Main frustration |
|---|---|---|---|
| **Tenant** (primary) | Workers, students and families renting in or around Murang'a town; a smartphone and mobile money are common | Filter by budget and area, see photos, contact the landlord directly, use little mobile data | Wasted trips to houses that do not fit |
| **Landlord, caretaker or agent** (primary) | Owns or manages houses, bedsitters or apartments | List quickly and free, reach tenants, get all inquiries in one place, mark houses as taken | Empty houses and unfiltered phone calls |
| **Administrator** (internal) | The site owner or team | Manage users, listings and locations; hide abusive reviews; recover access | Abuse, fake listings, support requests |
| **Visitor** | Anyone browsing without an account | Search and view houses without signing up | Being forced to register just to look |

---

## 5. Core Features (MVP)

| # | Feature | What it does | Priority | Status |
|---|---|---|---|---|
| F1 | Account sign-up with verification | Tenants confirm their email by a code. Landlords confirm their phone number by an SMS code and their email by a code. The account is created only after verification succeeds. | Must | Built |
| F2 | Login, logout and password reset | Username and password login, role-based landing page, reset link by email | Must | Built |
| F3 | House listings | Landlord adds, edits and deletes houses: title, area, rent, bedrooms, bathrooms, type, description | Must | Built |
| F4 | Photos | Landlord uploads and deletes photos for each house (stored in cloud storage) | Must | Built, but large phone photos fail until browser resizing is added |
| F5 | Vacant / occupied status | One click to mark a house taken or available again; only vacant houses appear in search | Must | Built |
| F6 | Search and filters | Area, property type, price range, bedrooms and bathrooms, with paged results | Must | Built |
| F7 | House details and contact | All photos, facts, landlord name, tap-to-call and the landlord's rating | Must | Built |
| F8 | Inquiries and landlord inbox | Tenant sends a message; landlord sees new ones highlighted with an unread count, plus call, WhatsApp and email buttons | Must | Built |
| F9 | Reviews | Tenants and landlords review each other after an inquiry; landlord reviews are public, tenant reviews are private; reports and admin hiding | Should | Built |
| F10 | Landing page | Search panel, browse by area, latest houses, how it works, footer and contact bar | Must | Built |
| F11 | Admin area | Manage users, locations, houses, photos, inquiries, reviews and reports | Must | Built |

### Launch blockers

These must be finished before the target launch date is set.

1. Switch SMS from the Africa's Talking sandbox to a live app with airtime.
2. Write and publish the Terms and Conditions and the Privacy Policy, and review Kenya's Data Protection Act, 2019.
3. Resize photos in the browser so phone photos fit the 4.5 MB upload limit.
4. Replace the sample testimonials, the "10,000+ clients" line and the placeholder contact details with real ones.
5. Move to a paid hosting plan before charging anyone (the free plan is for non-commercial use).

**Email:** verification emails now reach inboxes through a Gmail account. Gmail allows only about 500 messages a day, so move to a dedicated email service and a sender address on the project's own domain before real traffic.

### After the MVP

- Notify landlords by SMS or email when an inquiry or review arrives.
- Report a listing, a verified-landlord badge and login rate limiting.
- Saved houses and a WhatsApp button on house pages.
- Sign in with Google and Facebook.
- Maps, an admin dashboard with counts, and paid featured listings through M-Pesa.