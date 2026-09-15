# Sign-in codes over WhatsApp

`OTP_PROVIDER=whatsapp` delivers the sign-in code as a WhatsApp message instead
of an SMS, through Meta's WhatsApp Cloud API. The adapter is
`backend/app/auth/otp/whatsapp.py`; this file is the operational half — how the
account is set up, what must exist before the provider works, and the order the
switch has to happen in.

## Why this rather than SMS

Twilio's own signup verification does not reach Lebanese numbers — the code it
claims to send never arrives — so the SMS path is closed for this project until
another gateway is found. WhatsApp Cloud API is not closed: its signup runs
through a Facebook account rather than an SMS to the operator, and a sender
number can be verified by voice call. It is also cheaper per message, in a
country where nearly everyone already has WhatsApp.

If an SMS gateway ever becomes available, nothing here has to be undone. The
three providers sit behind one protocol (`app/auth/otp/base.py`) and the choice
is one variable.

## What the account needs, and what it does not

**Business verification is optional.** Meta's own setup wizard says so. It is
worth starting because it takes 2–10 business days and unlocks things you want,
but it blocks nothing:

| Unverified | Verified adds |
|---|---|
| recipients see the sender's phone number | the display name in chats instead |
| lower message cap per number | a higher cap |
| one or two numbers | up to twenty |

An individual with no registered company can therefore run this. Do not
assemble company documents that do not exist; create the business portfolio as
yourself and leave verification until the business is actually registered.

**A payment method is required for real recipients**, and a personal card is
acceptable. Billing is per message with no subscription: read the current
per-country rate at <https://developers.facebook.com/docs/whatsapp/pricing>
rather than trusting a number written here, because Meta has changed the
pricing model more than once.

## The free stage: a test number

Adding the WhatsApp product to a Meta app creates a WhatsApp Business Account
and a **test number owned by Meta**. It costs nothing, needs no card and no
documents, and messages up to five recipient numbers that you whitelist. It is
enough to prove the whole path end to end before anything is paid for.

From the app's **WhatsApp → API Setup** page, take:

- the **Phone number ID** — an identifier, not the number itself
- an **access token** — the one shown there expires in 24 hours

For anything beyond a demonstration, generate a permanent token instead:
Business Settings → Users → **System users** → a token with
`whatsapp_business_messaging` and `whatsapp_business_management`. Set it
straight in Railway; it never needs to pass through a conversation or a file.

## The template is not optional

The code is delivered as an **authentication template** — wording that is
registered with Meta, reviewed, and then referenced by name. The API sends only
the code, substituted into the approved body.

The consequence is in `AGENTS.md`: **`auth.sms.body` is not what a WhatsApp
recipient reads.** Their message comes from Meta's approved template, so
registering an Arabic one is part of configuring this provider rather than a
nicety. It is the only user-facing string in this project that deliberately
does not live in a locale catalog, because it is not ours to ship.

Create it in WhatsApp Manager (<https://business.facebook.com/wa/manage/message-templates/>)
with category **Authentication** and language **Arabic**, or with one request:

```bash
curl -X POST "https://graph.facebook.com/v21.0/<WABA_ID>/message_templates" \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "janoubona_code",
    "language": "ar",
    "category": "AUTHENTICATION",
    "components": [
      { "type": "BODY", "add_security_recommendation": true },
      { "type": "FOOTER", "code_expiration_minutes": 5 },
      { "type": "BUTTONS", "buttons": [ { "type": "OTP", "otp_type": "COPY_CODE" } ] }
    ]
  }'
```

`code_expiration_minutes` should match `OTP_TTL_SECONDS` (300 by default), or
the message promises a lifetime the server does not honour.

## Variables

| Variable | Notes |
|---|---|
| `WHATSAPP_PHONE_NUMBER_ID` | from API Setup; not the phone number |
| `WHATSAPP_ACCESS_TOKEN` | a System user token for anything but a demo |
| `WHATSAPP_TEMPLATE_NAME` | the approved template's `name` |
| `WHATSAPP_TEMPLATE_LOCALE` | `ar` |
| `WHATSAPP_TEMPLATE_HAS_BUTTON` | `true` unless the template has no OTP button |

## Order of operations

**Never set `OTP_PROVIDER=whatsapp` on a service before the provider code is
deployed to it.** `otp_provider` is a typed field; a build that predates this
adapter rejects the value while parsing settings, which happens at import, so
the container exits instead of serving. The credential variables above are safe
to set at any time — `Settings` uses `extra="ignore"`, so a build that does not
know them does not read them.

`enforce_production_safety()` refuses to boot a staging or production build
whose WhatsApp configuration is incomplete, so a missing template name fails
loudly rather than at the first sign-in attempt.

1. Deploy the provider code to the target service's branch.
2. Set the credential variables, template name included.
3. Set `OTP_PROVIDER=whatsapp` and let the service redeploy.
4. Sign in with a whitelisted number and confirm the code arrives.

Production additionally needs `APP_ENV=production`, which is what stops the
fixed development code being accepted — see "Going to production" in
`RAILWAY.md`.

## When a code does not arrive

Meta answers a rejected send with a JSON body naming the reason, and the
adapter logs it as `provider_error` on a `WhatsApp OTP delivery rejected`
record. Read that in the Railway logs before guessing; it distinguishes an
expired token from an unapproved template from a recipient outside the test
allow-list, which otherwise all look like silence. The access token travels in
a request header and never appears in a response body, so nothing sensitive is
in that log line.
