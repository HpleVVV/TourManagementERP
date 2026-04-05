{
    "name": "Tour Booking Management",
    "version": "18.0.1.0.0",
    "summary": "Manage tour bookings with workflow and group customers",
    "category": "Services",
    "license": "LGPL-3",
    "depends": ["base", "contacts", "mail", "tour_agency"],
    "data": [
        "security/ir.model.access.csv",
        "data/tour_booking_group_sync_data.xml",
        "views/tour_booking_views.xml",
        "views/tour_booking_menu.xml",
    ],
    "installable": True,
    "application": True,
}
