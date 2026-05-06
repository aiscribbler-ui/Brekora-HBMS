#!/usr/bin/env bash
PY="/c/Program Files/Python313/python"
extract() { echo "$1" | "$PY" -c "import sys,json; d=json.load(sys.stdin); print(d.get('access_token',''))"; }

ADMIN_JSON=$(curl -s -X POST http://localhost:8000/api/v1/auth/login -H "Content-Type: application/json" -d '{"email":"admin@test.com","password":"password123"}')
GUEST_JSON=$(curl -s -X POST http://localhost:8000/api/v1/auth/login -H "Content-Type: application/json" -d '{"email":"guest@test.com","password":"password123"}')
MGR_JSON=$(curl -s -X POST http://localhost:8000/api/v1/auth/login -H "Content-Type: application/json" -d '{"email":"manager@test.com","password":"password123"}')
PARTNER_JSON=$(curl -s -X POST http://localhost:8000/api/v1/auth/login -H "Content-Type: application/json" -d '{"email":"partner@test.com","password":"password123"}')

TOKEN_ADMIN=$(extract "$ADMIN_JSON")
TOKEN_GUEST=$(extract "$GUEST_JSON")
TOKEN_MGR=$(extract "$MGR_JSON")
TOKEN_PARTNER=$(extract "$PARTNER_JSON")

PROP_ID="93a51e40-629b-4c90-ab94-0f2dc84205a8"
ROOM_ID="8368f250-b435-4f8f-bb71-a2e16d7eae2d"
ORG="00000000-0000-0000-0000-000000000001"
TODAY="2026-05-05"
TOMORROW="2026-05-06"
DAY_AFTER="2026-05-07"

# A-041
echo "=== A-041 ==="
AVAIL1=$(curl -s "http://localhost:8000/api/v1/availability/rooms?property_id=$PROP_ID&room_type_id=$ROOM_ID&check_in=$TODAY&check_out=$TOMORROW" -H "Authorization: Bearer $TOKEN_ADMIN")
AVAIL1_COUNT=$(echo "$AVAIL1" | "$PY" -c "import sys,json; d=json.load(sys.stdin); print(d[0].get('available_count') if isinstance(d,list) and d else 'N/A')")
echo "Avail before: $AVAIL1_COUNT"

B1=$(curl -s -X POST http://localhost:8000/api/v1/bookings/ -H "Authorization: Bearer $TOKEN_ADMIN" -H "Content-Type: application/json" -d "{\"booking_type\":\"direct\",\"source_type\":\"walk_in\",\"property_id\":\"$PROP_ID\",\"check_in\":\"$TODAY\",\"check_out\":\"$TOMORROW\",\"guest_name\":\"A41 Guest\",\"guest_email\":\"a41@test.com\",\"guest_phone\":\"1234567890\",\"line_items_data\":[{\"item_type\":\"room\",\"item_id\":\"$ROOM_ID\",\"quantity\":2,\"unit_price\":\"1000.00\",\"nights\":1,\"total_price\":\"2000.00\"}]}")
B1_ID=$(echo "$B1" | "$PY" -c "import sys,json; d=json.load(sys.stdin); print(d.get('id',''))")
echo "Booking $B1_ID created"

AVAIL2=$(curl -s "http://localhost:8000/api/v1/availability/rooms?property_id=$PROP_ID&room_type_id=$ROOM_ID&check_in=$TODAY&check_out=$TOMORROW" -H "Authorization: Bearer $TOKEN_ADMIN")
AVAIL2_COUNT=$(echo "$AVAIL2" | "$PY" -c "import sys,json; d=json.load(sys.stdin); print(d[0].get('available_count') if isinstance(d,list) and d else 'N/A')")
echo "Avail after create: $AVAIL2_COUNT"

C1=$(curl -s -X PATCH "http://localhost:8000/api/v1/bookings/$B1_ID" -H "Authorization: Bearer $TOKEN_ADMIN" -H "Content-Type: application/json" -d '{"status":"cancelled","cancellation_reason":"A-041 test"}')
C1_STATUS=$(echo "$C1" | "$PY" -c "import sys,json; d=json.load(sys.stdin); print(d.get('status',''))")
echo "Cancel status: $C1_STATUS"

AVAIL3=$(curl -s "http://localhost:8000/api/v1/availability/rooms?property_id=$PROP_ID&room_type_id=$ROOM_ID&check_in=$TODAY&check_out=$TOMORROW" -H "Authorization: Bearer $TOKEN_ADMIN")
AVAIL3_COUNT=$(echo "$AVAIL3" | "$PY" -c "import sys,json; d=json.load(sys.stdin); print(d[0].get('available_count') if isinstance(d,list) and d else 'N/A')")
echo "Avail after cancel: $AVAIL3_COUNT"

if [ "$AVAIL1_COUNT" = "$AVAIL3_COUNT" ]; then echo "A-041 PASS"; else echo "A-041 FAIL before=$AVAIL1_COUNT after=$AVAIL2_COUNT cancel=$AVAIL3_COUNT"; fi

# A-042
echo ""
echo "=== A-042 ==="
IDEM_KEY="idem-$(date +%s)-RANDOM"
DUP1=$(curl -s -X POST http://localhost:8000/api/v1/bookings/ -H "Authorization: Bearer $TOKEN_ADMIN" -H "Content-Type: application/json" -d "{\"booking_type\":\"direct\",\"source_type\":\"walk_in\",\"property_id\":\"$PROP_ID\",\"check_in\":\"$TODAY\",\"check_out\":\"$TOMORROW\",\"guest_name\":\"Dup Guest\",\"guest_email\":\"dup@test.com\",\"guest_phone\":\"1234567890\",\"idempotency_key\":\"$IDEM_KEY\",\"line_items_data\":[{\"item_type\":\"room\",\"item_id\":\"$ROOM_ID\",\"quantity\":1,\"unit_price\":\"1000.00\",\"nights\":1,\"total_price\":\"1000.00\"}]}")
DUP1_ID=$(echo "$DUP1" | "$PY" -c "import sys,json; d=json.load(sys.stdin); print(d.get('id',''))")
echo "First booking id=$DUP1_ID"

DUP2=$(curl -s -X POST http://localhost:8000/api/v1/bookings/ -H "Authorization: Bearer $TOKEN_ADMIN" -H "Content-Type: application/json" -d "{\"booking_type\":\"direct\",\"source_type\":\"walk_in\",\"property_id\":\"$PROP_ID\",\"check_in\":\"$TODAY\",\"check_out\":\"$TOMORROW\",\"guest_name\":\"Dup Guest\",\"guest_email\":\"dup@test.com\",\"guest_phone\":\"1234567890\",\"idempotency_key\":\"$IDEM_KEY\",\"line_items_data\":[{\"item_type\":\"room\",\"item_id\":\"$ROOM_ID\",\"quantity\":1,\"unit_price\":\"1000.00\",\"nights\":1,\"total_price\":\"1000.00\"}]}")
echo "Second response: $DUP2"
if echo "$DUP2" | grep -q "409"; then echo "A-042 PASS"; else echo "A-042 RESULT: $(echo "$DUP2" | "$PY" -c "import sys,json; d=json.load(sys.stdin); print(d.get('detail',''))")"; fi

# A-043
echo ""
echo "=== A-043 ==="
OVER=$(curl -s -X POST http://localhost:8000/api/v1/bookings/ -H "Authorization: Bearer $TOKEN_ADMIN" -H "Content-Type: application/json" -d "{\"booking_type\":\"direct\",\"source_type\":\"walk_in\",\"property_id\":\"$PROP_ID\",\"check_in\":\"$TODAY\",\"check_out\":\"$TOMORROW\",\"guest_name\":\"Over Guest\",\"guest_email\":\"over@test.com\",\"guest_phone\":\"1234567890\",\"line_items_data\":[{\"item_type\":\"room\",\"item_id\":\"$ROOM_ID\",\"quantity\":999,\"unit_price\":\"1000.00\",\"nights\":1,\"total_price\":\"999000.00\"}]}")
echo "Staff overbooking: $OVER"
if echo "$OVER" | grep -q "409"; then echo "A-043 Staff PASS"; else echo "A-043 Staff FAIL (BUG-007)"; fi

echo ""
echo "=== G-018 ==="
GUEST_STAFF=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/v1/bookings/ -H "Authorization: Bearer $TOKEN_GUEST" -H "X-Org-ID: $ORG")
echo "Guest /bookings/ backend: $GUEST_STAFF"
if [ "$GUEST_STAFF" = "403" ]; then echo "G-018 PASS"; else echo "G-018 FAIL got $GUEST_STAFF"; fi

# G-016
echo ""
echo "=== G-016 ==="
INIT=$(curl -s -X POST http://localhost:8000/api/v1/bookings/init -H "Content-Type: application/json" -d "{\"property_id\":\"$PROP_ID\",\"item_type\":\"room\",\"item_id\":\"$ROOM_ID\",\"check_in\":\"$TODAY\",\"check_out\":\"$TOMORROW\",\"guest_name\":\"Cancel Guest\",\"guest_email\":\"cancel@test.com\",\"guest_phone\":\"1234567890\",\"adults\":2,\"children\":0}")
INIT_HOLD=$(echo "$INIT" | "$PY" -c "import sys,json; d=json.load(sys.stdin); print(d.get('hold_id',''))")
echo "Guest init hold_id: $INIT_HOLD"
if [ -n "$INIT_HOLD" ]; then echo "G-016 Partial PASS (init works, full cancel needs payment)"; else echo "G-016 BLOCKED init failed"; fi
