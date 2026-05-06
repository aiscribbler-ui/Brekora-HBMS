import subprocess, json, time, sys, os

def curl(method, url, headers=None, data=None):
    cmd = ["curl", "-s", "-w", "\n__HTTP_CODE__%{http_code}", "-X", method, url]
    if headers:
        for k,v in headers.items():
            cmd.extend(["-H", f"{k}: {v}"])
    if data:
        cmd.extend(["-d", json.dumps(data)])
    result = subprocess.run(cmd, capture_output=True, text=True)
    out = result.stdout.strip()
    if "__HTTP_CODE__" in out:
        body, code = out.rsplit("__HTTP_CODE__", 1)
        return body, int(code)
    return out, 0

def login(email, password):
    body, code = curl("POST", "http://localhost:8000/api/v1/auth/login",
                      headers={"Content-Type": "application/json"},
                      data={"email": email, "password": password})
    if code == 200:
        return json.loads(body).get("access_token", "")
    print(f"Login failed for {email}: {body}")
    return ""

def main():
    # Login all roles
    admin_token = login("admin@test.com", "password123")
    guest_token = login("guest@test.com", "password123")
    mgr_token = login("manager@test.com", "password123")
    partner_token = login("partner@test.com", "password123")

    if not admin_token:
        print("Admin token missing, aborting")
        return

    PROP = "93a51e40-629b-4c90-ab94-0f2dc84205a8"
    ROOM = "8368f250-b435-4f8f-bb71-a2e16d7eae2d"
    ORG = "00000000-0000-0000-0000-000000000001"
    TODAY = "2026-05-05"
    TOMORROW = "2026-05-06"
    DAY_AFTER = "2026-05-07"

    def api(method, path, data=None, token=admin_token, extra_headers=None):
        h = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        if extra_headers:
            h.update(extra_headers)
        body, code = curl(method, f"http://localhost:8000/api/v1{path}", headers=h, data=data)
        try:
            j = json.loads(body)
        except:
            j = body
        return j, code

    # A-041: Booking Cancellation Restores Inventory
    print("=== A-041 ===")
    avail1, _ = api("GET", f"/availability/rooms?property_id={PROP}&room_type_id={ROOM}&check_in={TODAY}&check_out={TOMORROW}")
    avail1_count = avail1[0].get("available_count") if isinstance(avail1, list) and avail1 else "N/A"
    print(f"Avail before: {avail1_count}")

    b1, _ = api("POST", "/bookings/", data={
        "booking_type": "direct", "source_type": "walk_in", "property_id": PROP,
        "check_in": TODAY, "check_out": TOMORROW, "guest_name": "A41 Guest",
        "guest_email": "a41@test.com", "guest_phone": "1234567890",
        "line_items_data": [{"item_type": "room", "item_id": ROOM, "quantity": 2, "unit_price": "1000.00", "nights": 1, "total_price": "2000.00"}]
    })
    b1_id = b1.get("id", "")
    print(f"Booking {b1_id} created")

    avail2, _ = api("GET", f"/availability/rooms?property_id={PROP}&room_type_id={ROOM}&check_in={TODAY}&check_out={TOMORROW}")
    avail2_count = avail2[0].get("available_count") if isinstance(avail2, list) and avail2 else "N/A"
    print(f"Avail after create: {avail2_count}")

    c1, _ = api("PATCH", f"/bookings/{b1_id}", data={"status": "cancelled", "cancellation_reason": "A-041 test"})
    print(f"Cancel response: {c1}")

    avail3, _ = api("GET", f"/availability/rooms?property_id={PROP}&room_type_id={ROOM}&check_in={TODAY}&check_out={TOMORROW}")
    avail3_count = avail3[0].get("available_count") if isinstance(avail3, list) and avail3 else "N/A"
    print(f"Avail after cancel: {avail3_count}")

    if str(avail1_count) == str(avail3_count):
        print("A-041 PASS")
    else:
        print(f"A-041 FAIL (before={avail1_count} after_create={avail2_count} after_cancel={avail3_count})")

    # A-042: Duplicate Booking Prevention
    print("\n=== A-042 ===")
    idem_key = f"idem-{int(time.time())}"
    dup1, _ = api("POST", "/bookings/", data={
        "booking_type": "direct", "source_type": "walk_in", "property_id": PROP,
        "check_in": TODAY, "check_out": TOMORROW, "guest_name": "Dup Guest",
        "guest_email": "dup@test.com", "guest_phone": "1234567890",
        "idempotency_key": idem_key,
        "line_items_data": [{"item_type": "room", "item_id": ROOM, "quantity": 1, "unit_price": "1000.00", "nights": 1, "total_price": "1000.00"}]
    })
    dup1_id = dup1.get("id", "")
    print(f"First booking id={dup1_id}")

    dup2, dup2_code = api("POST", "/bookings/", data={
        "booking_type": "direct", "source_type": "walk_in", "property_id": PROP,
        "check_in": TODAY, "check_out": TOMORROW, "guest_name": "Dup Guest",
        "guest_email": "dup@test.com", "guest_phone": "1234567890",
        "idempotency_key": idem_key,
        "line_items_data": [{"item_type": "room", "item_id": ROOM, "quantity": 1, "unit_price": "1000.00", "nights": 1, "total_price": "1000.00"}]
    })
    print(f"Second response code={dup2_code}: {dup2}")
    if dup2_code == 409:
        print("A-042 PASS")
    else:
        print(f"A-042 FAIL (expected 409, got {dup2_code})")

    # A-043: Overbooking Prevention
    print("\n=== A-043 ===")
    over, over_code = api("POST", "/bookings/", data={
        "booking_type": "direct", "source_type": "walk_in", "property_id": PROP,
        "check_in": TODAY, "check_out": TOMORROW, "guest_name": "Over Guest",
        "guest_email": "over@test.com", "guest_phone": "1234567890",
        "line_items_data": [{"item_type": "room", "item_id": ROOM, "quantity": 999, "unit_price": "1000.00", "nights": 1, "total_price": "999000.00"}]
    })
    print(f"Staff overbooking code={over_code}: {over}")
    if over_code == 409:
        print("A-043 Staff PASS")
    else:
        print("A-043 Staff FAIL (BUG-007 confirmed - staff endpoint allows overbooking)")

    # Test guest init overbooking
    print("\nTest guest init overbooking...")
    # Fill all rooms for tomorrow first
    fill, _ = api("POST", "/bookings/", data={
        "booking_type": "direct", "source_type": "walk_in", "property_id": PROP,
        "check_in": TOMORROW, "check_out": DAY_AFTER, "guest_name": "Fill Guest",
        "guest_email": "fill@test.com", "guest_phone": "1234567890",
        "line_items_data": [{"item_type": "room", "item_id": ROOM, "quantity": 5, "unit_price": "1000.00", "nights": 1, "total_price": "5000.00"}]
    })
    print(f"Fill booking: {fill.get('id','')}")

    init_over, init_code = api("POST", "/bookings/init", data={
        "property_id": PROP, "item_type": "room", "item_id": ROOM,
        "check_in": TOMORROW, "check_out": DAY_AFTER,
        "guest_name": "Init Over", "guest_email": "initover@test.com",
        "guest_phone": "1234567890", "adults": 2, "children": 0
    }, token=None)
    print(f"Guest init overbooking code={init_code}: {init_over}")
    if init_code == 409:
        print("A-043 Guest init PASS")
    else:
        print(f"A-043 Guest init FAIL (expected 409, got {init_code})")

    # G-018
    print("\n=== G-018 ===")
    g18, g18_code = api("GET", "/bookings/", token=guest_token, extra_headers={"X-Org-ID": ORG})
    print(f"Guest /bookings/ code={g18_code}")
    if g18_code == 403:
        print("G-018 PASS")
    else:
        print(f"G-018 FAIL (expected 403, got {g18_code})")

    # G-016
    print("\n=== G-016 ===")
    init, init_code = api("POST", "/bookings/init", data={
        "property_id": PROP, "item_type": "room", "item_id": ROOM,
        "check_in": TODAY, "check_out": TOMORROW,
        "guest_name": "Cancel Guest", "guest_email": "cancel@test.com",
        "guest_phone": "1234567890", "adults": 2, "children": 0
    }, token=None)
    hold_id = init.get("hold_id", "")
    print(f"Guest init hold_id={hold_id}")
    if hold_id:
        print("G-016 Partial PASS (init works, full cancel needs payment completion)")
    else:
        print(f"G-016 BLOCKED (init failed: {init})")

if __name__ == "__main__":
    main()
