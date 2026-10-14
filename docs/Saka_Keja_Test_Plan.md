# Test Plan and Test Cases

**Saka Keja** - house hunting made easier in Murang'a County

Records what needs testing, the steps to test it, expected results, and whether the software passes.

| | |
|---|---|
| **Version** | 1.0 |
| **Date** | October 2026 |
| **Tester** | [your name] |
| **Software version tested** | [Git commit or deployment link] |
| **Overall result** | 100 of 118 cases pass; 17 not run yet; 1 blocked. All 145 automated tests pass in the development environment. Live-site checks are still open. |

---

## 1. Test Plan

### 1.1 Purpose and scope

This plan defines how Saka Keja is checked before launch, what each check does, and how results are recorded. It covers the requirements in the SRS.

**In scope:** registration with phone and email verification, login and password reset, landlord listings and photos, search and the landing page, inquiries, reviews, the admin area, security basics and deployment.

**Out of scope:** rent payments and contracts (not built), the internal behaviour of Africa's Talking, Gmail, Vercel, Neon and Supabase, and large-scale load testing.

### 1.2 Test approach

| Level | What it is | How it is run |
|---|---|---|
| Automated tests | Django tests for rules, permissions, limits and pages; the SMS client is checked against a local copy of the provider's API | `python manage.py test` (or one app at a time) |
| Browser checks | A script drives the real pages in a browser: locked fields, buttons, the star picker, layouts at 1280 px and 390 px | Run in the development environment |
| Manual checks on the live site | Things only the real services can show: SMS and email delivery, photo storage, admin, secure settings | Follow the steps in section 3 and record the result |
| Security checks | Permissions, CSRF, script injection, rate limits, secrets | Mostly automated; the rest in the NFR cases |

### 1.3 Environments

| Environment | Setup | Used for |
|---|---|---|
| Development | Local or sandbox machine, SQLite, email and SMS printed or kept in memory, files on disk | Automated tests and browser checks |
| Live | Vercel, Neon PostgreSQL, Supabase Storage, Gmail SMTP, Africa's Talking (sandbox until a live app exists) | Manual checks and final acceptance |

Use an Android phone (Chrome) and a desktop browser for manual checks.

### 1.4 Test data

- One tenant, two landlords and one administrator account; a second tenant for privacy checks.
- Kenyan numbers in each accepted format, plus invalid ones.
- Houses in two locations with different rent, bedrooms, bathrooms and types, some occupied.
- A 2 MB photo, a 6 MB photo and a text file.
- A real inbox on Gmail, Yahoo and Outlook, and a phone that can receive SMS.

### 1.5 Entry and exit criteria

**Start testing when:** the build is deployed, migrations have run, environment variables are set, and the test accounts exist.

**Release when:** all automated tests pass; every case in section 3 is Pass, or the project owner has accepted the exception in writing; no Critical or High defect is open (section 4.2); and the cases marked Manual (live) have been run and recorded.

### 1.6 Status values and severity

| Status | Meaning |
|---|---|
| Pass | Ran and matched the expected result |
| Fail | Ran and did not match; a defect is logged |
| Blocked | Cannot run until something else is fixed or set up |
| Not run | Not run yet |

| Severity | Meaning |
|---|---|
| Critical | Data loss, security hole, or the site cannot be used |
| High | A main feature does not work, no workaround |
| Medium | A feature is hard to use, or a workaround exists |
| Low | Cosmetic or minor |

### 1.7 Roles

The tester runs the cases and records results. The developer fixes defects and re-runs the affected tests. The project owner signs off the release.

### 1.8 Risks and gaps in testing

- Automated and browser results come from a development environment, not from the owner's machine or the live site. Re-run them locally before relying on them.
- SMS delivery to a real phone cannot be tested until a live Africa's Talking app exists.
- No automated test covers the admin screens, the real mail services or the production photo storage.
- Load and long-running behaviour have not been tested.

---

## 2. Results summary

| Area | Cases | Pass | Not run | Blocked |
|---|---|---|---|---|
| Registration and phone verification | 23 | 22 | 0 | 1 |
| Email code and account creation | 16 | 15 | 1 | 0 |
| Login, logout and password reset | 8 | 7 | 1 | 0 |
| Property listings (landlord) | 14 | 12 | 2 | 0 |
| Search, house pages and landing page | 13 | 12 | 1 | 0 |
| Inquiries | 13 | 12 | 1 | 0 |
| Reviews | 21 | 19 | 2 | 0 |
| Administration | 3 | 0 | 3 | 0 |
| Security, performance and deployment | 7 | 1 | 6 | 0 |
| **Total** | **118** | **100** | **17** | **1** |

**Automated test suite:** 145 tests, all passing in the development environment: accounts 68, properties 24, inquiries 12, reviews 41.

---

## 3. Test cases

Each row gives the steps and the expected result. Fill in the Status column when you run a case that says Not run. For automated cases the class name under 'How tested' shows where the test lives.

### REG. Registration and phone verification

| ID | Test case | Steps | Expected result | How tested | Status |
|---|---|---|---|---|---|
| REG-01 | Register page starts locked | Open the register page | Code field and Verify Code button have the disabled attribute; Register button is disabled; Confirm Phone Number is enabled | Browser (dev); Auto: RegistrationRequiresVerifiedPhone | Pass |
| REG-02 | Locked code field ignores typing | Click the code field and type 123456 | The field stays empty | Browser (dev) | Pass |
| REG-03 | Layout on desktop and phone | Open the page at 1280 px and 390 px wide | Confirm button sits right of the phone box on desktop and below it on a phone; code field is under the phone row; no sideways scrolling | Browser (dev) | Pass |
| REG-04 | Empty phone number | Press Confirm Phone Number with the box empty | Message: Enter your phone number first. Code field stays locked | Browser (dev); Auto: PhoneVerificationAPI | Pass |
| REG-05 | Invalid phone number | Enter 12345 and press Confirm | Valid Kenyan number error; no SMS sent; code field stays locked | Browser (dev); Auto: PhoneVerificationAPI | Pass |
| REG-06 | Accepted number formats | Try 0712345678, 712345678, +254712345678, 254712345678, 0712 345 678, 0112345678, then 0612345678, +255712345678, 07123456789 | The first six are stored as +254...; the last three are rejected | Auto: PhoneNumberFormats | Pass |
| REG-07 | Send a code | Enter a valid number and press Confirm | Verification code sent successfully; code field and Verify Code unlock; Confirm button shows a resend countdown | Browser (dev); Auto | Pass |
| REG-08 | Code is never exposed | Request a code and inspect the response, the page HTML and the database | The code appears in none of them; the database holds a 64-character hash only | Auto: PhoneVerificationAPI | Pass |
| REG-09 | Correct code | Type the SMS code and press Verify Code | Verified message and badge shown; Register enabled; code field locks | Browser (dev) | Pass |
| REG-10 | Wrong code | Type a wrong code | That code is not correct, with attempts left (4, 3, 2, 1, 0) | Auto | Pass |
| REG-11 | Lockout after 5 wrong codes | Enter 5 wrong codes, then the right one | Too many wrong attempts; a new code is needed | Auto | Pass |
| REG-12 | Code expires | Wait more than 5 minutes, then enter the code | That code has expired | Auto | Pass |
| REG-13 | Send limits | Press Confirm twice within 60 s; request 6 codes for one number in an hour; request 11 from one IP address in an hour | Each is refused with a wait or limit message | Auto: PhoneVerificationAPI | Pass |
| REG-14 | Edit the number after sending | Send a code, then change the number | Code cleared and locked, Register disabled, and the server refuses the old code | Browser (dev); Auto | Pass |
| REG-15 | Edit the number after verifying | Verify, then change the number | Badge hides, Register disabled, verification revoked | Browser (dev) | Pass |
| REG-16 | Server refuses an unverified number | Submit the form without verifying, or force the Register button on with browser tools | Error asking to verify the number first; nothing is created | Browser (dev); Auto | Pass |
| REG-17 | Different number than the verified one | Verify number A, submit with number B | Refused | Auto | Pass |
| REG-18 | Verification used from another browser | Verify in browser 1, submit in browser 2 | Refused | Auto | Pass |
| REG-19 | SMS provider problems | Make the provider fail, or remove the credentials in production | Failed to send code. Please try again.; reason logged without secrets; an immediate retry is allowed | Auto | Pass |
| REG-20 | Provider request format | Compare the SMS request with Africa's Talking's documented format | apiKey header; username, to and message fields; status codes 100 to 102 accepted; key and code never logged | Auto: AfricasTalkingBackend | Pass |
| REG-21 | JSON endpoints are protected | Send GET, or POST without a CSRF token | 405 and 403; no SMS sent | Auto | Pass |
| REG-22 | SMS accepted by the provider (sandbox) | Send a code from the live site and open the sandbox dashboard | The messages are counted in Bulk SMS and appear in the simulator | Manual (live) | Pass |
| REG-23 | SMS reaches a real phone | Send a code to your own number | SMS arrives within a minute | Manual (live) | Blocked (sandbox never reaches real phones) |

### EML. Email code and account creation

| ID | Test case | Steps | Expected result | How tested | Status |
|---|---|---|---|---|---|
| EML-01 | No user until verified | Verify the phone, then submit the form | A pending record and an email exist; the user table is still empty | Auto | Pass |
| EML-02 | Secrets are hashed | Inspect the pending record | Password and code are stored only as hashes | Auto | Pass |
| EML-03 | Correct email code | Enter the emailed code | Active user created with a +254 phone, logged in; tenants go to search, landlords to Add a house | Auto | Pass |
| EML-04 | Wrong code lockout | Enter 5 wrong codes, then the right one | Too many wrong attempts | Auto | Pass |
| EML-05 | Expiry | Wait over 10 minutes; wait over 30 minutes for the whole sign-up | Code expired; sign-up expired and is removed | Auto | Pass |
| EML-06 | Resend | Press Send a new code inside 60 s, then after | Blocked first; then a new code replaces the old one | Auto | Pass |
| EML-07 | Sign-up bound to the browser | Another browser enters the code | Refused; nothing created | Auto | Pass |
| EML-08 | Overwrite protection | Register the same email again within 60 s, then after the wait | Refused; later the first person's browser can no longer finish the replaced sign-up | Auto | Pass |
| EML-09 | Duplicate email or username | Use an existing email; take the username while waiting | Rejected up front; clean restart | Auto | Pass |
| EML-10 | Password rules | Use 12345678; use mismatched passwords | Rejected; nothing created; no email sent | Auto | Pass |
| EML-11 | Phone verification is single use | After an account is created, register again with the same verification | Refused | Auto | Pass |
| EML-12 | Phone check repeated at creation | Let the phone verification expire, or clear its proof, before the email step | Account not created; the user is asked to register again | Auto | Pass |
| EML-13 | Honest failure when email cannot be sent | Make SMTP fail, or leave EMAIL_HOST unset in production | An error is shown, never a false sent message; no account | Auto | Pass |
| EML-14 | Masked address | Open the verify page | Shows a masked address such as d***@example.com | Auto | Pass |
| EML-15 | Verification email reaches an inbox | Register with a real address on the live site | Code arrives from Saka Keja within a minute | Manual (live) | Pass (owner received the email) |
| EML-16 | Other mail providers | Try Gmail, Yahoo and Outlook addresses | Arrives and is not in spam | Manual (live) | Not run |

### AUTH. Login, logout and password reset

| ID | Test case | Steps | Expected result | How tested | Status |
|---|---|---|---|---|---|
| AUTH-01 | Role-based landing page | Log in as a landlord, then as a tenant | My houses; search page | Auto: LoginAndLogout | Pass |
| AUTH-02 | Return to the page you came from | Open Send inquiry while logged out, then log in | You return to that page | Auto | Pass |
| AUTH-03 | Bad credentials | Wrong password; unknown user | Error shown; not logged in | Auto | Pass |
| AUTH-04 | Logged-in visitors | Open the login or register page while logged in | Redirected away | Auto | Pass |
| AUTH-05 | Logout | Open the logout address; then press Logout | GET is refused (405); POST ends the session | Auto | Pass |
| AUTH-06 | Password reset | Request a reset, open the link, set a new password, log in; reopen the old link | Works; the old link is invalid | Auto: PasswordReset | Pass |
| AUTH-07 | Reset for an unknown email | Request a reset for an address with no account | Same confirmation page; no email sent | Auto | Pass |
| AUTH-08 | Reset email reaches an inbox | Request a reset on the live site | Link arrives and works | Manual (live) | Not run |

### LST. Property listings (landlord)

| ID | Test case | Steps | Expected result | How tested | Status |
|---|---|---|---|---|---|
| LST-01 | Landlord pages need login and the right role | Open My houses and Add a house logged out, then as a tenant | Sent to login; tenants refused (403) | Auto: LandlordListings | Pass |
| LST-02 | Create a house | Submit the Add a house form | Saved with the landlord as owner; photo page opens | Auto | Pass |
| LST-03 | Invalid house details | Rent 0 or text, blank title, unknown location or type | Not saved | Auto | Pass |
| LST-04 | My houses shows only my own | Log in as a landlord with another landlord's houses present | Only own houses listed | Auto | Pass |
| LST-05 | Another landlord's house | Try to edit, delete, switch status or add photos to it | 404; nothing changes | Auto | Pass |
| LST-06 | Edit a house | Change the title and rent | Saved | Auto | Pass |
| LST-07 | Vacant and occupied switch | Press Mark occupied, then Mark vacant | Status flips each time | Auto | Pass |
| LST-08 | Delete and switch need POST | Open the delete and status addresses directly | 405; the house is kept | Auto | Pass |
| LST-09 | Delete a house | Press Delete and confirm | House removed | Auto | Pass |
| LST-10 | Location in use is protected | Delete a location that has houses | Refused | Auto | Pass |
| LST-11 | Photo upload and delete | Upload an image; delete it; try deleting as another landlord | Saved and removed; other landlord gets 404 | Auto | Pass |
| LST-12 | Non-image upload | Upload a text file as a photo | Rejected | Auto | Pass |
| LST-13 | Photo upload on the live site | Upload a 2 MB photo | Saved and shown from the storage bucket | Manual (live) | Not run |
| LST-14 | Large photo on the live site | Upload a 6 MB photo | Expected to fail (host limit about 4.5 MB) until browser resizing is built | Manual (live) | Not run (known limitation) |

### SRC. Search, house pages and landing page

| ID | Test case | Steps | Expected result | How tested | Status |
|---|---|---|---|---|---|
| SRC-01 | Only vacant houses appear | Search with occupied and vacant houses present | Occupied houses are missing from results | Auto: LandingAndSearch | Pass |
| SRC-02 | Price range | Choose each landing page price range | Results fall inside it | Auto | Pass |
| SRC-03 | Range fills the rent boxes | Search from the landing page with a price range | The results page shows the matching min and max rent | Auto | Pass |
| SRC-04 | Type, bedrooms, bathrooms, location | Filter by each | Type exact; bedrooms exact; bathrooms at least; location exact | Auto | Pass |
| SRC-05 | Combined filters | Use all filters together | Only the matching house | Auto | Pass |
| SRC-06 | Typed rent beats the range | Send both a range and typed min and max | Typed values win | Auto | Pass |
| SRC-07 | Min above max | Enter min 9000 and max 1000 | A clear error, no crash | Auto | Pass |
| SRC-08 | Paging | Search with 17 results | 12 on page one, 5 on page two | Auto | Pass |
| SRC-09 | Landing page content | Open the home page | All sections present; contact bar, then navigation, then hero; 3 testimonials; footer | Auto | Pass |
| SRC-10 | Landing page with no houses | Open it with an empty database | Sample card shown, no error | Auto | Pass |
| SRC-11 | Top bar and footer on every page | Open other pages | Both appear | Auto | Pass |
| SRC-12 | Landing page layout | View at 1920 px and 390 px wide | Contact bar, navigation, hero and search panel line up and nothing is cut off | Manual (dev) (screenshots) | Pass |
| SRC-13 | Search on a real phone | Use the filters on an Android phone on the live site | Usable and quick on mobile data | Manual (live) | Not run |

### INQ. Inquiries

| ID | Test case | Steps | Expected result | How tested | Status |
|---|---|---|---|---|---|
| INQ-01 | Send an inquiry | As a tenant, send a message about a vacant house | Saved; you see My inquiries | Auto: InquiryTests | Pass |
| INQ-02 | Phone prefilled | Open the inquiry form | Your phone number is filled in | Auto | Pass |
| INQ-03 | Short message | Send 'hi' | Rejected | Auto | Pass |
| INQ-04 | Landlords cannot send | Try as a landlord | Refused; nothing saved | Auto | Pass |
| INQ-05 | Occupied house | Send about an occupied house | Refused | Auto | Pass |
| INQ-06 | Visitors must log in | Send while logged out | Sent to login; nothing saved | Auto | Pass |
| INQ-07 | Tenant sees own inquiries only | Open My inquiries | Only your messages | Auto | Pass |
| INQ-08 | Inbox shows own houses only | Open the inbox as a landlord | Only inquiries about your houses | Auto | Pass |
| INQ-09 | Tenants cannot open the inbox | Open the inbox as a tenant | 403 | Auto | Pass |
| INQ-10 | Mark as read | Mark a message read as its landlord, as another landlord, and by opening the address | Works for the owner by POST only; others get 404 or 405 | Auto | Pass |
| INQ-11 | Unread count | Check the count for each role and after reading | Landlords only; drops when read | Auto | Pass |
| INQ-12 | Contact numbers for the buttons | Check call and WhatsApp numbers | WhatsApp number in 254 format; falls back to the profile number | Auto | Pass |
| INQ-13 | Call and WhatsApp buttons on a phone | Tap each in the inbox | Opens the dialler and the WhatsApp chat | Manual (live) | Not run |

### REV. Reviews

| ID | Test case | Steps | Expected result | How tested | Status |
|---|---|---|---|---|---|
| REV-01 | Who may review whom | Try each pair of users with and without an inquiry | Only a tenant and landlord who have an inquiry between them; never self or same role | Auto: Eligibility | Pass |
| REV-02 | Visitors and strangers refused | Open the review form logged out, and as an ineligible user | Sent to login; refused; nothing saved | Auto | Pass |
| REV-03 | Post a review | Write a review | Appears on the landlord's page; the house is recorded for context | Auto: WritingReviews | Pass |
| REV-04 | Edit instead of duplicate | Post twice | One review, updated | Auto | Pass |
| REV-05 | Rating validation | Submit 0, 6, blank, abc and 4.5 | None saved | Auto | Pass |
| REV-06 | Comment rules | Blank comment; 500 and 501 characters | Blank allowed; 500 saved; 501 refused | Auto | Pass |
| REV-07 | Script injection | Post a comment containing script and bold tags | Shown as plain text | Auto | Pass |
| REV-08 | Landlord reviews a tenant | Review a tenant who inquired | Saved on the private page | Auto | Pass |
| REV-09 | Database rules | Create a review with rating 6, 0, of oneself, or a second one for a pair | The database refuses each | Auto | Pass |
| REV-10 | Public landlord page and numbers | Open a landlord page logged out | Average, count, breakdown and houses shown | Auto: Profiles | Pass |
| REV-11 | Hidden reviews excluded | Hide a review | Gone from the page and the average | Auto | Pass |
| REV-12 | Tenant reviews are private | Open a tenant page as other tenants, other landlords, the tenant, a contacted landlord and staff | Only the last three groups can see it | Auto | Pass |
| REV-13 | Delete a review | Delete as author, as others, and by opening the address | Author only; POST only | Auto: DeletingAndReporting | Pass |
| REV-14 | Report a review | Report once, twice, own, private, hidden, logged out | One report each; not your own; private rule respected; the review stays visible | Auto | Pass |
| REV-15 | My reviews page | Open My reviews | People waiting for a review, reviews about me, reviews I wrote, hidden note | Auto: MyReviewsAndIntegration | Pass |
| REV-16 | Links from other pages | Open the house, inquiries, inbox and navigation | Review links and the rating summary appear | Auto | Pass |
| REV-17 | Star picker | Click stars, submit with none, submit with four | Five radio buttons; four stars gold, one grey; error when empty; review posted | Browser (dev) | Pass |
| REV-18 | Report and edit in the browser | Report another person's review; edit your own | Acknowledged and the review stays; form is prefilled | Browser (dev) | Pass |
| REV-19 | Landlord profile on a phone | Open a landlord profile at 390 px wide | No sideways scrolling | Browser (dev) | Pass |
| REV-20 | Star picker by keyboard | Tab to the stars and use the arrow keys | A star is selected and focus is visible | Manual (dev) | Not run |
| REV-21 | Hide a review as an administrator | Admin: choose a review, then Hide selected reviews | It disappears from the profile and the average | Manual (live) | Not run |

### ADM. Administration

| ID | Test case | Steps | Expected result | How tested | Status |
|---|---|---|---|---|---|
| ADM-01 | Admin sign-in and styling | Open /admin/ and log in | Dashboard loads with its normal styling | Manual (live) | Not run |
| ADM-02 | Manage data | Edit a user's role and phone; add a location and a house | Saved | Manual (live) | Not run |
| ADM-03 | First admin from variables | Set ADMIN_* variables and redeploy | Build log says admin created; the login works | Manual (live) | Not run |

### NFR. Security, performance and deployment

| ID | Test case | Steps | Expected result | How tested | Status |
|---|---|---|---|---|---|
| NFR-01 | HTTPS and secure cookies | Open the live site over http and https; inspect cookies | Redirect to https; cookies marked secure | Manual (live) | Not run |
| NFR-02 | Debug mode is off | Trigger an error on the live site | A plain error page, no settings or code shown | Manual (live) | Not run |
| NFR-03 | No secrets in the repository | Search the code and Git history for keys, .env and db.sqlite3 | None found | Manual (dev) | Not run (known risk: the first commit held db.sqlite3 and the old SECRET_KEY) |
| NFR-04 | Page speed on mobile | Load the home page with network throttling at 3G | Main content within about 2 seconds | Manual (dev) | Not run |
| NFR-05 | IP limits work on the host | Request SMS codes with changing forwarded addresses | The limit counts the real visitor address | Manual (live) | Not run |
| NFR-06 | Build applies migrations | Push a change and read the build log | Migrations are listed as applied | Manual (live) | Pass (seen in the first deployment's build log) |
| NFR-07 | Standard locations exist after a deploy | Open Locations in the admin | The four standard areas are present | Manual (live) | Not run |

---

## 4. Defects

### 4.1 Found and fixed during testing

| Problem | Severity | How it was found | Status |
|---|---|---|---|
| A wrong phone code was not counted, because a database rollback undid the counter, which would have allowed unlimited guesses | Critical | Automated test | Fixed |
| The verified badge showed before anything was verified, because styling overrode its hidden state | Medium | Browser check | Fixed |
| The star picker's radio buttons lacked the class that hides them and lights the stars | High | Browser check | Fixed |
| The site said a code was sent when no email service was configured in production | High | Review of live behaviour | Fixed |

### 4.2 Open issues

| ID | Issue | Severity | Next step |
|---|---|---|---|
| KI-01 | SMS runs on the sandbox, so codes never reach real phones | High for launch | Switch to a live Africa's Talking app with airtime, then run REG-23 |
| KI-02 | Photos over about 4.5 MB fail on the host | Medium | Resize photos in the browser, then run LST-13 |
| KI-03 | The first Git commit contained db.sqlite3 and the old SECRET_KEY | High | Use new secrets, make the repository private, consider cleaning the history, then run NFR-03 |
| KI-04 | Gmail allows about 500 messages a day | Low for testing | Move to a dedicated email service before real traffic |
| KI-05 | Terms and Privacy pages do not exist | High for launch | Write and publish them |

---

## 5. How to run the tests

```
python manage.py test            # everything
python manage.py test accounts    # one app
python manage.py test reviews
```

Run the whole suite before every deployment. After a failure, fix the cause and re-run the affected app, then the whole suite. For the manual cases, work through section 3 on the live site and write the result in the Status column.

**Priority for the first live run:** REG-22, REG-23, EML-15, EML-16, AUTH-08, LST-12, ADM-01, ADM-03, NFR-01, NFR-02 and NFR-03.

---

## 6. Sign-off

| Role | Name | Date | Decision |
|---|---|---|---|
| Tester | | | |
| Developer | | | |
| Project owner | | | Approve / Reject |
