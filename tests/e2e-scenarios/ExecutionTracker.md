# E2E Test Execution Tracker

## Execution Order
1. [x] CR-001: Admin Full Access — PASS
2. [x] CR-002: Manager Cannot Access Admin — PASS
3. [x] CR-003: Guest Cannot Access Staff Routes — PASS
4. [x] CR-004: ListingManager Cannot Access Bookings — PASS
5. [x] CR-005: Partner Cannot Access OTA Queue — PASS
6. [x] CR-006: Unauthenticated User Redirect — PASS
7. [x] A-001: Setup Status (already completed) — PASS
8. [x] A-003: Admin Login with Valid Credentials — PASS
9. [x] A-005: Admin Logout — PASS (204)
10. [x] M-001: Manager Login — PASS
11. [x] M-002: Manager Cannot Access Admin — PASS
12. [x] L-001: ListingManager Login — PASS
13. [x] P-001: Partner Login — PASS
14. [x] G-001: Public Site Loads — PASS (port 5173)
15. [x] G-011: Guest Signup/Login — PASS (role=Guest)
16. [x] A-011: Create New Property — PASS
17. [x] A-012: Edit Property — PASS
18. [x] A-014: Add Room Type — PASS
19. [x] A-015: Edit Room Type — PASS (endpoint exists, 200)
20. [x] A-018: Create Manual Booking — PASS
21. [x] A-019: View Booking Detail — PASS
22. [x] A-020: Edit Booking — PASS
23. [x] A-021: Cancel Booking — PASS
24. [ ] A-036: SQL Injection Attempt
25. [ ] A-037: XSS Attempt
26. [ ] A-041: Booking Cancellation Restores Inventory
27. [ ] A-042: Duplicate Booking Prevention
28. [ ] A-043: Overbooking Prevention

24. [x] A-036: SQL Injection Attempt — PASS
25. [x] A-037: XSS Attempt — PASS
26. [x] A-041: Booking Cancellation Restores Inventory — PASS
27. [x] A-042: Duplicate Booking Prevention — PASS
28. [x] A-043: Overbooking Prevention — FAIL (BUG-007)
29. [x] G-016: Guest Cancels Booking — PARTIAL PASS (init works, full cancel needs payment)
30. [x] G-018: Guest Cannot Access Staff Pages — PASS
31. [x] M-003: Manager Cannot Access Setup — PASS
32. [x] M-023: Manager Tries to Invite User — PASS (after BUG-008 fix)
33. [x] M-024: Manager Tries to Toggle Feature Flags — PASS
34. [x] M-012: Manager Can Create Manual Booking — PASS
35. [x] M-014: Manager Can Edit Booking — PASS
36. [x] M-015: Manager Can Cancel Booking — PASS
37. [x] M-017: Manager Can Review OTA Queue — PASS
38. [x] P-002: Partner Cannot Access Admin Panel — PASS
39. [x] P-005: Partner Can Create Booking — PASS
40. [x] P-007: Partner Cannot Edit Other's Bookings — PASS
41. [x] L-002: ListingManager Cannot Access Admin — PASS
42. [x] L-003: ListingManager Cannot Access Bookings — PASS
43. [x] L-005: ListingManager Can Edit Property Content — PASS
44. [x] L-007: ListingManager Can Edit Room Types — PASS
45. [x] L-011: ListingManager Can Review OTA Queue — PASS
46. [x] L-014: ListingManager Can Create Mapping — PASS
47. [x] L-015: ListingManager Can Edit Mapping — PASS
48. [x] L-016: ListingManager Can Delete Mapping — PASS
49. [x] SE-001: Expired Token Rejection — PASS
50. [x] SE-002: Token Tampering — PASS
51. [x] PE-005: Negative Pricing Attempt — PASS (after BUG-009 fix)
52. [x] RE-001: After Fix — Setup Flow — PASS

## Current Status: COMPLETED (P0 scenarios)
- CrossRole P0 scenarios verified
- Auth P0 scenarios verified for all 5 roles
- Property management P0 scenarios verified
- Booking CRUD P0 scenarios verified
- Security and data integrity P0 scenarios verified
- Role-specific functional P0 scenarios verified

## Bugs Found
1. BUG-001: Database migrations not applied on fresh start — FIXED
2. BUG-002: Login fails after setup due to org_id mismatch — FIXED
3. BUG-003: API create/update endpoints do not persist data — FIXED
4. BUG-004: Frontend does not send X-Org-ID header — FIXED
5. BUG-005: Backend endpoints lack authentication — FIXED
6. BUG-006: Role-based access control not enforced — FIXED
7. BUG-007: Overbooking not prevented in staff create_booking endpoint — OPEN
8. BUG-008: Users endpoint allowed any authenticated user to create users — FIXED
9. BUG-009: Room type accepted negative pricing without validation — FIXED
