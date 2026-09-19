# Verification report — 19 September 2026

## Interface

Rendered with Chromium using Playwright at viewport widths 360, 390, 768, 1024 and 1440 pixels. The supplied HTML was loaded with `set_content` because this environment blocks browser navigation to local files and localhost. This verifies rendered layout and interface behaviour; it is not a public-hosting test.

Passed: no page-level JavaScript errors; no horizontal overflow at those widths; one main heading; required fields block advancing; three-step form navigation; previous answers preserved when going back; preview submit opens an honest no-payment/no-submission dialog; native FAQ disclosure; desktop and mobile screenshots inspected.

No fonts, external images or tracking resources are requested by the supplied frontend. The local preview does not persist form data in localStorage/sessionStorage or send it over the network.

## Backend

11 synthetic Python unit tests passed:

1. Application saved before checkout URL is returned.
2. Same-key retries return the same reference.
3. Missing acknowledgements rejected.
4. Cross-origin submissions rejected.
5. Preview and expired-deadline submissions blocked.
6. Correctly signed synthetic payment recorded; duplicate delivery ignored.
7. Invalid and expired signatures rejected.
8. Wrong payment amount flagged instead of marked paid.
9. Delayed unpaid event cannot overwrite recorded paid status.
10. Unrelated Payment Link ignored.
11. Private files are not served.

The backend uses Python standard library only. The test data is synthetic and kept in a temporary database, not included in the package.

## Not performed

No deployment, domain configuration, real/test Stripe API transaction, webhook delivery from an actual Stripe account, email delivery, refund, venue reservation, production security audit, full accessibility audit or legal review. A maintained production WSGI server has not been installed or exercised in this environment. The project must pass an account-specific Stripe test and hosting check before live use.
