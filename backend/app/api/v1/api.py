from fastapi import APIRouter

from app.api.v1.endpoints import (
    add_ons,
    auth,
    availability,
    bookings,
    cancellation_policies,
    feature_flags,
    google_auth,
    gst,
    inventory_buffers,
    organizations,
    ota_alerts,
    ota_gmail,
    ota_mappings,
    ota_metrics,
    ota_queue,
    ota_settings,
    owner_reports,
    packages,
    payments,
    pricing,
    properties,
    room_types,
    search,
    sessions,
    users,
    webhooks,
)

api_router = APIRouter()
api_router.include_router(
    organizations.router, prefix="/organizations", tags=["organizations"]
)
api_router.include_router(
    properties.router, prefix="/properties", tags=["properties"]
)
api_router.include_router(
    room_types.router, prefix="/room-types", tags=["room-types"]
)
api_router.include_router(
    packages.router, prefix="/packages", tags=["packages"]
)
api_router.include_router(
    cancellation_policies.router,
    prefix="/cancellation-policies",
    tags=["cancellation-policies"],
)
api_router.include_router(
    users.router, prefix="/users", tags=["users"]
)
api_router.include_router(
    auth.router, prefix="/auth", tags=["auth"]
)
api_router.include_router(sessions.router)
api_router.include_router(google_auth.router)
api_router.include_router(
    ota_gmail.router, prefix="/ota/gmail", tags=["ota-gmail"]
)
api_router.include_router(
    ota_mappings.router, prefix="/ota/mappings", tags=["ota-mappings"]
)
api_router.include_router(
    ota_queue.router, prefix="/ota/queue", tags=["ota-queue"]
)
api_router.include_router(
    ota_alerts.router, prefix="/ota/alerts", tags=["ota-alerts"]
)
api_router.include_router(
    ota_settings.router, prefix="/ota/settings", tags=["ota-settings"]
)
api_router.include_router(
    add_ons.router, prefix="/add-ons", tags=["add-ons"]
)
api_router.include_router(
    availability.router, prefix="/availability", tags=["availability"]
)
api_router.include_router(
    bookings.router, prefix="/bookings", tags=["bookings"]
)
api_router.include_router(
    payments.router, prefix="/payments", tags=["payments"]
)
api_router.include_router(
    webhooks.router, prefix="/webhooks", tags=["webhooks"]
)
api_router.include_router(
    pricing.router, prefix="/pricing", tags=["pricing"]
)
api_router.include_router(
    gst.router, prefix="/gst", tags=["gst"]
)
api_router.include_router(
    search.router, prefix="/search", tags=["search"]
)
api_router.include_router(
    inventory_buffers.router, prefix="/inventory-buffers", tags=["inventory-buffers"]
)
api_router.include_router(
    feature_flags.router, prefix="/feature-flags", tags=["feature-flags"]
)
api_router.include_router(
    ota_metrics.router, prefix="/ota/metrics", tags=["ota-metrics"]
)
api_router.include_router(
    owner_reports.router, prefix="/owner", tags=["owner-reports"]
)
