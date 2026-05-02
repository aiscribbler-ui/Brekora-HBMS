# Agent Task Index

## Agent B — Booking Engine

| Task | Status | Priority | Blocked By | Notes |
|------|--------|----------|------------|-------|
| B-001 Transactional Inventory Write Service | DONE | P0 | None | Full implementation with commit, release, add-ons, concurrent load tests |
| B-002 Availability Query Engine (Rooms) | DONE | P0 | A-006, A-014 | Endpoint + caching implemented, tests created |
| B-003 Availability Query Engine (Add-ons) | DONE | P0 | A-011, B-001 | Slot/day capacity queries |
| B-004 Hold Expiry Background Cleaner | DONE | P0 | B-001 | ARQ scheduled task, calls release_inventory per expired hold |
| B-005 Public Search API | PENDING | P0 | B-002, B-003 | Direct booking site search |
| B-006 Booking Initialization + 10-Minute Hold | PENDING | P0 | B-001, B-005 | First step of direct booking flow |
| B-007 Razorpay Integration | DONE | P0 | B-006 | Test-mode payments |
| B-008 Payment Confirmation + Inventory Commit | PENDING | P0 | B-007 | Webhook success handler |
| B-009 Payment Failure / Abandonment Handling | PENDING | P0 | B-007 | Failure webhook + timeout handling |
| B-010 Guest Retry Payment Flow | PENDING | P0 | B-009 | Retry endpoint |
| B-011 GST Calculation Service | PENDING | P0 | B-006 | 12% default, admin-overridable |
| B-012 Concurrent Booking Conflict Resolution | DONE | P0 | B-006 | 409 Conflict + alternatives |
| B-013 Pricing Engine | DONE | P1 | A-006, A-010, A-011 | Rate plans, seasonal, promo codes |
| B-014 ChannelSource Abstraction | PENDING | P0 | A-012 | Gmail/ical adapters |
| B-015 Owner P&L + Payout Calculation | PENDING | P0 | B-008, B-011 | Monthly statements |
| B-016 Booking Modification Service | PENDING | P0 | B-008 | PATCH bookings |
| B-017 Rate Limiting Middleware | DONE | P0 | A-001 | Redis-based rate limits |

## Agent C — OTA Ingestion

| Task | Status | Priority | Blocked By | Notes |
|------|--------|----------|------------|-------|
| C-001 Gmail API OAuth Connection | DONE | P0 | A-001, A-020 | OAuth flow, token refresh, health check |
| C-002 Background Gmail Polling Job | DONE | P0 | C-001, A-020 | ARQ cron every 5 min, stores raw emails, applies BMS_PROCESSED label |
| C-003 Airbnb Email Parser | DONE | P0 | C-002 | Extract booking fields from Airbnb confirmations |
| C-004 MakeMyTrip Email Parser | DONE | P0 | C-002 | Extract booking fields from MMT vouchers |
| C-005 Goibibo Email Parser | DONE | P0 | C-002 | Extract booking fields from Goibibo confirmations |
| C-006 Parsed Booking Review Queue API | DONE | P0 | C-003, C-004, C-005, B-014 | Manager-facing confirm/edit/reject flow |
| C-007 Auto-Confirm Toggle Per OTA | PENDING | P1 | C-006 | High-confidence auto-confirm settings |
| C-008 Failed Parse Alert System | PENDING | P0 | C-002 | Dashboard alerts for parser failures |
| C-009 OTA Listing-to-Room-Type Mapping | DONE | P0 | A-006 | OTAMapping CRUD and parser integration |
| C-010 iCal Import Fallback | PENDING | P1 | C-002, B-014 | Poll iCal feeds as booking fallback |
| C-011 Parser Accuracy Telemetry | PENDING | P2 | C-003, C-004, C-005 | Daily accuracy metrics per OTA |

## Agent E — DevOps & Integration

| Task | Status | Priority | Blocked By | Notes |
|------|--------|----------|------------|-------|
| E-001 Docker Compose Production-Like Stack | DONE | P0 | A-001, A-020 | Full local stack with health checks, startup order, JSON logging |
| E-002 CI Pipeline | DONE | P1 | E-001 | GitHub Actions for lint, type-check, test |
| E-003 E2E — Direct Booking Flow | PENDING | P0 | B-008, D-008 | Playwright-based guest booking flow |
| E-004 E2E — Manual Booking Flow | PENDING | P0 | E-003, D-006 | Manager walk-in booking flow |
| E-005 E2E — OTA Parse + Confirm | PENDING | P0 | E-003, C-006, D-010 | Email ingestion to queue confirmation |
| E-006 E2E — Owner P&L | PENDING | P0 | E-004, B-015, D-011 | Owner report validation |
| E-007 E2E — Cancellation + Audit | PENDING | P0 | E-003, D-007 | Cancellation, refund, audit trail |
| E-008 E2E — Payment Failure Recovery | PENDING | P0 | E-003, B-009, B-010 | Retry flow validation |
| E-009 E2E — Concurrent Conflict | PENDING | P0 | E-003, B-012 | Double-booking prevention |
| E-010 Performance Benchmarks | PENDING | P2 | E-003 | Locust/wrk load tests |
| E-011 Security Audit Checklist | PENDING | P2 | E-003 | Bandit, npm audit, RBAC verification |
| E-012 AWS IaC Skeleton | DONE | P2 | None | Terraform skeleton for ap-south-1 |
| E-013 Migration Wizard Validation | PENDING | P2 | A-018 | CSV import dry-run and reconciliation |
| E-014 Documentation & Runbook | PENDING | P2 | E-012 | README, ARCHITECTURE, DEPLOYMENT, TESTING, TROUBLESHOOTING |

## Agent D — Frontend

| Task | Status | Priority | Blocked By | Notes |
|------|--------|----------|------------|-------|
| FE-001 | React Project Scaffold | DONE | P0 | None |
| FE-002 | Manager Login Page | DONE | P0 | D-001 | JWT auth, form validation, tests pass |
| FE-003 | Manager Dashboard — Today View | DONE | P0 | D-002 | Widgets, auto-refresh, responsive grid, tests pass |
| FE-004 | Property & Room Type Management UI | DONE | P0 | D-002 | CRUD interface |
| FE-005 | Package Catalog Builder UI | DONE | P0 | D-004 | Visual composition builder |
| FE-006 | Manual Booking Creation Form | DONE | P0 | D-002 | Multi-step form |
| FE-007 | Calendar Grid View | DONE | P1 | D-003 | Visual calendar |
| FE-008 | Booking Detail / Edit / Cancel / Refund UI | PENDING | P0 | D-006 | Full booking management |
| FE-009 | OTA Queue Review UI | PENDING | P0 | D-003 | Parsed booking review |
| FE-010 | Owner Reporting Dashboard | PENDING | P1 | D-003 | Financial dashboard |
| FE-011 | Partner Dashboard (v1.1) | PENDING | P3 | D-011 | Pipeline, tier, commission |
| FE-012 | Direct Booking Site (Public) | DONE | P0 | D-001 | Public booking engine |
| FE-013 | Guest Account Portal | PENDING | P1 | D-008 | Guest-facing account page |
| FE-014 | Admin System Config Panel | PENDING | P1 | D-002 | Admin configuration |
| FE-015 | WCAG 2.1 AA Accessibility Compliance | PENDING | P1 | D-008 | Accessibility audit |
| GUEST-001 | Guest Sign-up/Login Page | DONE | P1 | None | Guest login, signup, dashboard stubs; tests created |

---

*Last updated: 2026-05-01*
