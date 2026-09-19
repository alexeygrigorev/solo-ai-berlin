# Solo + AI Berlin

**Build your business with AI. Not alone.**

Project archive from Alexey's planning conversation, saved 19 September 2026. Public-facing copy is in English; planning notes and deployment instructions are in Russian.

## Current working plan

A small, application-based, member-funded peer group in Berlin for solopreneurs and indie hackers using AI to build and run independent businesses. This is a participatory group, not a course, lecture series, or passive networking audience.

| Item | Current draft |
| --- | --- |
| First pilot | 10 and 24 November 2026, both Tuesdays |
| Time | 18:30–21:00, Europe/Berlin (CET) |
| Area | Mitte / Prenzlauer Berg; exact venue not booked |
| Size | 10–12 paying participants, plus the host |
| Launch threshold | At least 10 approved and paid participants |
| Price | €59 total for two sessions and the pilot group chat |
| Payment | One-time upfront payment with the application; no automatic renewal |
| Application/payment deadline | 1 November 2026, 23:59 CET |
| Group and venue confirmation | 3 November 2026, 18:00 CET |
| Refunds | Full refund if declined, no place is available, the threshold is not reached, or the organiser cancels/cannot confirm the venue |
| Participant cancellation | Draft additionally proposes a full refund until 3 November, 18:00 CET |

The user chose a November launch and Monday/Tuesday evenings. The exact dates, €59 price, deadlines, cancellation window and refund processing commitments are working choices introduced in the draft; they should be deliberately adopted before sales open. Do not describe the venue, sales or membership as already confirmed.

## Read in this order

1. [Messaging, selection criteria and decisions](messaging-and-decisions.md) — the latest positioning and upfront-payment model.
2. [Venue, economics, operations and outreach research](research.md) — archived research, contact shortlist and caveats; not a fresh verification of availability, jobs or prices.
3. [Landing source and deployment instructions](landing/README_RU.md) — the English site, application flow, optional Python/SQLite server and Stripe webhook handling.
4. [Original English launch kit](archive/launch-kit-v1.md) — retained as historical copy, NOT the current application/payment policy.
5. [Artifact inventory](artifact-manifest.json) — original-file checksums and archive coverage.

## Important version distinction

The original English launch kit asks whether applicants would pay and says payment comes after selection. That policy was superseded. The current flow is:

**Read criteria → complete application → pay €59 upfront → manual review → confirmed place or full refund.**

Payment is not an application-review fee and does not guarantee acceptance. Relevant participation means a concrete business project, hands-on AI experiments, and willingness to share and give feedback. Profitability, a registered company, a large audience and advanced AI expertise are not required.

## Implementation status

The supplied landing is a design/interaction preview, not a deployed payment-taking site. The HTML works locally. The optional server and tests are development artifacts, not evidence of a live Stripe integration. Reviews, acceptance emails, venue booking and refunds are manual. Legal pages are incomplete templates. No applicant data, real payment credentials or `.env` file belong in this public repository.

Before launch: confirm the operator's public name spelling (the original HTML says `Alexey Grigoryev`, whereas the GitHub account uses `Alexey Grigorev`), complete operator details and legal pages, select hosting and durable private storage, configure Stripe in test mode, test the end-to-end flow, reserve an appropriate room, and only then enable live applications/payments.

For a local preview, see [the deployment guide](landing/README_RU.md). Saving this folder does not deploy a website or enable GitHub Pages.

## Archive coverage

The repository archive retains the text documents and source files. Original PNG screenshots and the original distribution ZIP are inventoried by checksum but are not embedded in this repository copy. The browser-check script is retained for regenerating previews. The original ZIP and preview images were supplied as downloadable conversation attachments.

Research sources are retained where they appeared in the conversation. Facts about third parties, prices and legal/payment rules are archived claims, not a new endorsement or current verification. Contact suggestions are not confirmed members or endorsements.
