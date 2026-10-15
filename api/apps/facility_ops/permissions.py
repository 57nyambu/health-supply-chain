from apps.access.catalogue import PermissionDef as P

PERMISSIONS = [
    P("operations.stats.read", "View facility operations statistics (footfall, beds, attendance)"),
    P("operations.stats.submit", "Submit daily facility statistics"),
    P("operations.alert.read", "View facility operations alerts"),
]
