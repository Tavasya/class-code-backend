# Stripe Subscription Integration

## Overview

This document describes the Stripe subscription integration for teacher accounts. Teachers can subscribe to plans that provide credits (in hours) for their students to use the platform's analysis features.

## Architecture

### Credit Calculation Formula

```
Total Credits (hours) = (plan_minutes × student_count) / 60
```

**Examples:**
- 30-min plan × 25 students = `(30 × 25) / 60 = 12.5 hours`
- 60-min plan × 100 students = `(60 × 100) / 60 = 100 hours`

### Plans & Pricing

**Per-Student Pricing:**
- Each teacher pays per student
- Total cost = `price × student_count`
- Stripe automatically multiplies by quantity

**Available Plans:**

| Plan | Billing Cycle | Price per Student | Stripe Price ID |
|------|--------------|-------------------|-----------------|
| 30-min | Monthly | $3.00/month | `price_1SL6QGHBRGAB5YB1dGJoQrd5` |
| 30-min | Quarterly | $8.10/quarter (10% off) | `price_1SL6RoHBRGAB5YB1iUynXNt4` |
| 60-min | Monthly | $6.00/month | `price_1SL6SbHBRGAB5YB1VsmCbfCA` |
| 60-min | Quarterly | $16.20/quarter (10% off) | `price_1SL6SrHBRGAB5YB1uXLPe0on` |

---

## Database Schema

### `teacher_subscriptions` Table

```sql
CREATE TABLE teacher_subscriptions (
  id UUID PRIMARY KEY,
  teacher_id UUID UNIQUE REFERENCES users(id),

  -- Stripe IDs
  stripe_customer_id TEXT UNIQUE NOT NULL,
  stripe_subscription_id TEXT UNIQUE NOT NULL,
  stripe_price_id TEXT NOT NULL,

  -- Plan details
  plan_type TEXT CHECK (plan_type IN ('30min', '60min')),
  billing_cycle TEXT CHECK (billing_cycle IN ('monthly', 'quarterly')),
  student_count INTEGER CHECK (student_count > 0),

  -- Status
  status TEXT DEFAULT 'active',

  -- Billing period
  current_period_start TIMESTAMPTZ,
  current_period_end TIMESTAMPTZ,

  -- Timestamps
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  canceled_at TIMESTAMPTZ
);
```

### `users` Table (Existing)

Credits are stored in the existing `users.credits` field (type: `real`/`float`).

---

## API Endpoints

### Base URL
`https://your-backend-url.com/api/v1/stripe`

### 1. Create Checkout Session

**Endpoint:** `POST /create-checkout`

**Description:** Create a Stripe checkout session for subscription purchase.

**Request Body:**
```json
{
  "plan_type": "30min",
  "billing_cycle": "monthly",
  "student_count": 25,
  "teacher_id": "uuid-here",
  "success_url": "https://your-frontend.com/success?session_id={CHECKOUT_SESSION_ID}",
  "cancel_url": "https://your-frontend.com/cancel"
}
```

**Response:**
```json
{
  "checkout_url": "https://checkout.stripe.com/...",
  "session_id": "cs_test_..."
}
```

**Usage:**
```javascript
const response = await fetch('/api/v1/stripe/create-checkout', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    plan_type: '30min',
    billing_cycle: 'monthly',
    student_count: 25,
    teacher_id: teacherId
  })
});

const { checkout_url } = await response.json();
window.location.href = checkout_url; // Redirect to Stripe
```

---

### 2. Get Subscription Info

**Endpoint:** `GET /subscription/{teacher_id}`

**Response:**
```json
{
  "teacher_id": "uuid",
  "plan_type": "30min",
  "billing_cycle": "monthly",
  "student_count": 25,
  "credits": 12.5,
  "status": "active",
  "current_period_start": "2025-01-15T00:00:00Z",
  "current_period_end": "2025-02-15T00:00:00Z",
  "stripe_customer_id": "cus_...",
  "stripe_subscription_id": "sub_...",
  "created_at": "2025-01-15T00:00:00Z"
}
```

---

### 3. Update Student Count

**Endpoint:** `POST /update-quantity`

**Request Body:**
```json
{
  "teacher_id": "uuid",
  "new_student_count": 50
}
```

**Response:**
```json
{
  "success": true,
  "message": "Successfully updated student count to 50",
  "new_credits": 25.0
}
```

**Note:** Stripe automatically prorates the charges.

---

### 4. Cancel Subscription

**Endpoint:** `POST /cancel`

**Request Body:**
```json
{
  "teacher_id": "uuid",
  "cancel_at_period_end": true
}
```

**Response:**
```json
{
  "success": true,
  "message": "Subscription will be canceled at the end of the current billing period",
  "canceled_at": null
}
```

---

### 5. Customer Portal

**Endpoint:** `POST /customer-portal`

**Description:** Get URL to Stripe customer portal where teachers can manage their subscription.

**Request Body:**
```json
{
  "teacher_id": "uuid",
  "return_url": "https://your-frontend.com/subscription"
}
```

**Response:**
```json
{
  "portal_url": "https://billing.stripe.com/session/..."
}
```

---

## Webhook Events

### Webhook Endpoint

**URL:** `https://your-backend-url.com/api/v1/stripe/webhook`

**Configure in Stripe Dashboard:**
1. Go to Developers → Webhooks
2. Add endpoint: `https://your-backend-url.com/api/v1/stripe/webhook`
3. Select events:
   - `checkout.session.completed`
   - `invoice.payment_succeeded`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
   - `invoice.payment_failed`

### Event Handlers

#### 1. `checkout.session.completed`
**Trigger:** Teacher completes payment

**Actions:**
- Create `teacher_subscriptions` record
- Calculate credits: `(plan_minutes × student_count) / 60`
- Update `users.credits` field

**Example:** Teacher buys 30-min monthly plan for 25 students
- Credits set to: `(30 × 25) / 60 = 12.5 hours`

---

#### 2. `invoice.payment_succeeded`
**Trigger:** Monthly/quarterly renewal payment succeeds

**Actions:**
- **Reset** credits to plan amount (not add, reset!)
- Update `current_period_start` and `current_period_end`
- Set `status = 'active'`

**Example:** Renewal occurs
- Credits reset to: `(30 × 25) / 60 = 12.5 hours` (not added)

---

#### 3. `customer.subscription.updated`
**Trigger:** Subscription details change (quantity, plan, etc.)

**Actions:**
- Update `student_count` in database
- Recalculate and update credits
- Update `status` if changed

**Example:** Teacher updates from 25 to 50 students
- New credits: `(30 × 50) / 60 = 25 hours`

---

#### 4. `customer.subscription.deleted`
**Trigger:** Subscription is canceled

**Actions:**
- Delete `teacher_subscriptions` record
- Reset credits to free tier: `40.0 hours`

---

#### 5. `invoice.payment_failed`
**Trigger:** Payment fails (expired card, insufficient funds)

**Actions:**
- Update `status = 'past_due'`
- Log warning
- (Teacher keeps access during grace period)

---

## Testing

### Test Mode

All credentials in `.env` use Stripe test mode (`sk_test_...`, `pk_test_...`).

### Test Cards

Use Stripe test cards:
- **Success:** `4242 4242 4242 4242`
- **Decline:** `4000 0000 0000 0002`
- **Requires auth:** `4000 0025 0000 3155`

Any future expiry date (e.g., 12/34), any CVC (e.g., 123).

### Testing Webhooks Locally

**Option 1: Stripe CLI**
```bash
# Install Stripe CLI
brew install stripe/stripe-cli/stripe

# Login
stripe login

# Forward webhooks to local server
stripe listen --forward-to localhost:8080/api/v1/stripe/webhook

# Trigger test events
stripe trigger checkout.session.completed
stripe trigger invoice.payment_succeeded
```

**Option 2: ngrok**
```bash
# Expose local server
ngrok http 8080

# Use ngrok URL in Stripe Dashboard webhook settings
# Example: https://abc123.ngrok.io/api/v1/stripe/webhook
```

---

## Environment Variables

Add to `.env`:

```bash
# Stripe Configuration
STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...

# Stripe Price IDs
STRIPE_PRICE_30MIN_MONTHLY=price_...
STRIPE_PRICE_30MIN_QUARTERLY=price_...
STRIPE_PRICE_60MIN_MONTHLY=price_...
STRIPE_PRICE_60MIN_QUARTERLY=price_...
```

---

## Frontend Integration Example

### Purchase Flow

```javascript
// 1. Teacher selects plan
const handleSubscribe = async () => {
  const response = await fetch('/api/v1/stripe/create-checkout', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      plan_type: selectedPlan,        // "30min" or "60min"
      billing_cycle: selectedCycle,    // "monthly" or "quarterly"
      student_count: studentCount,     // Number input
      teacher_id: currentUser.id
    })
  });

  const { checkout_url } = await response.json();
  window.location.href = checkout_url;
};
```

### Display Current Subscription

```javascript
// Fetch subscription info
const response = await fetch(`/api/v1/stripe/subscription/${teacherId}`);
const subscription = await response.json();

// Display
console.log(`Plan: ${subscription.plan_type}`);
console.log(`Credits: ${subscription.credits} hours`);
console.log(`Students: ${subscription.student_count}`);
console.log(`Next billing: ${subscription.current_period_end}`);
```

### Update Student Count

```javascript
const updateStudents = async (newCount) => {
  const response = await fetch('/api/v1/stripe/update-quantity', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      teacher_id: currentUser.id,
      new_student_count: newCount
    })
  });

  const result = await response.json();
  console.log(`New credits: ${result.new_credits} hours`);
};
```

---

## Security Considerations

✅ **Webhook Signature Verification**
- All webhooks verify Stripe signature using `stripe.Webhook.construct_event()`
- Invalid signatures return 400 error

✅ **Idempotency**
- Webhook handlers are idempotent
- Safe to retry on failure

✅ **Secret Keys**
- Never expose `STRIPE_SECRET_KEY` to frontend
- Only `STRIPE_PUBLISHABLE_KEY` goes to frontend (if needed)

✅ **Teacher Authentication**
- All API endpoints should verify teacher authentication
- (Add your auth middleware as needed)

---

## Troubleshooting

### Webhook not receiving events
1. Check webhook URL is publicly accessible
2. Verify webhook secret matches Stripe Dashboard
3. Check logs for signature verification errors
4. Use Stripe CLI to test locally

### Credits not updating
1. Check logs for database errors
2. Verify teacher_id exists in users table
3. Check webhook event contains correct metadata

### Checkout session creation fails
1. Verify all price IDs are correct
2. Check Stripe API key is valid
3. Ensure student_count > 0

---

## Production Checklist

Before going live:

- [ ] Replace test Stripe keys with live keys
- [ ] Update webhook endpoint URL in Stripe Dashboard
- [ ] Test all webhook events in production
- [ ] Add proper error handling and user notifications
- [ ] Set up monitoring for failed webhooks
- [ ] Configure customer portal branding in Stripe
- [ ] Add email notifications for payment failures
- [ ] Implement grace period for past_due subscriptions
- [ ] Add analytics tracking for subscription events

---

## Support

For issues or questions:
- Stripe Documentation: https://stripe.com/docs
- Stripe Dashboard: https://dashboard.stripe.com
- Webhook Logs: https://dashboard.stripe.com/webhooks
