# Brekora HBMS — End-to-End Test Scenarios

## Overview
This document defines end-to-end test scenarios for all 5 login types in Brekora BMS.
Each scenario follows this structure:
- **ID**: Unique identifier
- **Role**: Which login type
- **Precondition**: What must be true before starting
- **Steps**: Exact actions to perform
- **Expected Result**: What should happen
- **Actual Result**: (Filled during testing)
- **Status**: PASS / FAIL / BLOCKED
- **Bug ID**: (If failed)

## Roles Under Test
1. **Admin** — Full system access
2. **Manager** (Property Manager) — Day-to-day operations
3. **Guest** — Public booking user
4. **Partner** — Commission-based external agent
5. **ListingManager** — Cross-property OTA content manager

## Test Environment
- Frontend: `http://localhost`
- Backend API: `http://localhost:8000/api/v1`
- Database: Fresh or seeded with known data
- Browser: Chrome/Firefox latest

## Global Preconditions for Each Session
- Docker containers are running (`docker compose up`)
- Backend is healthy (`/api/v1/health` returns 200)
- Frontend loads without console errors
- Redis is connected

## Severity Levels
- **P0 (Critical)**: Blocks core workflow (login, booking, payment)
- **P1 (High)**: Major feature broken, workaround exists
- **P2 (Medium)**: Minor feature issue, cosmetic
- **P3 (Low)**: Enhancement, edge case

---

## Scenario Count Summary

| Role | P0 | P1 | P2 | P3 | Total |
|------|----|----|----|----|-------|
| Admin | 15 | 25 | 20 | 10 | 70 |
| Manager | 20 | 30 | 25 | 15 | 90 |
| Guest | 20 | 25 | 20 | 15 | 80 |
| Partner | 15 | 20 | 15 | 10 | 60 |
| ListingManager | 15 | 20 | 15 | 10 | 60 |
| Cross-Role | 20 | 30 | 25 | 15 | 90 |
| **Total** | **105** | **150** | **120** | **75** | **450** |

*Note: The remaining 50 scenarios are regression/edge-case scenarios documented in individual role files.*

---

## Cross-Role Test Matrix

| Feature | Admin | Manager | Guest | Partner | ListingManager |
|---------|-------|---------|-------|---------|---------------|
| /setup first-time | Yes | No | No | No | No |
| /login staff | Yes | Yes | No | Yes | Yes |
| /guest/login | No | No | Yes | No | No |
| /dashboard | Yes | Yes | No | Yes | Yes |
| /properties CRUD | Yes | Read/Edit | No | View | Read/Edit |
| /calendar | Yes | Yes | No | View | Yes |
| /packages | Yes | Yes | No | No | No |
| /ota/queue | Yes | Yes | No | No | Yes |
| /ota/mappings | Yes | No | No | No | Yes |
| /bookings/manual | Yes | Yes | No | Yes | No |
| /bookings/:id | Yes | Yes | Own only | Yes | No |
| /owner | Yes | Yes | No | No | No |
| /admin | Yes | No | No | No | No |
| /messages | Yes | Yes | No | No | No |
| /book public site | No | No | Yes | No | No |

---

## Critical Bug Logging Format

When a test fails, log:
```
BUG-{ID}: {Short description}
- Role: {Role}
- Scenario: {Scenario ID}
- Severity: {P0/P1/P2/P3}
- Steps to Reproduce: {steps}
- Expected: {expected}
- Actual: {actual}
- Root Cause: {analysis}
- Fix: {file changes}
- Status: OPEN / FIXED / VERIFIED
```

---

## Testing Order
1. Fresh install → /setup flow (Admin creation)
2. Admin scenarios (creates other users)
3. Manager scenarios
4. ListingManager scenarios
5. Partner scenarios
6. Guest scenarios
7. Cross-role permission tests
8. Regression on fixed bugs
