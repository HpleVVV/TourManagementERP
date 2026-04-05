from odoo import fields, models


class TourBookingLine(models.Model):
    _name = "tour.booking.line"
    _description = "Tour Booking Group Line"
    _order = "id"

    group_id = fields.Many2one(
        "tour.booking.group",
        string="Booking Group",
        required=True,
        ondelete="cascade",
        index=True,
    )
    booking_id = fields.Many2one(
        "tour.booking",
        string="Booking",
        required=True,
        ondelete="cascade",
        index=True,
    )
    partner_id = fields.Many2one(
        "res.partner",
        string="Customer",
        related="booking_id.partner_id",
        store=True,
        readonly=True,
    )
    state = fields.Selection(
        related="booking_id.state",
        string="Booking Status",
        store=True,
        readonly=True,
    )
    travel_end_date = fields.Date(
        related="booking_id.travel_end_date",
        string="Travel End Date",
        store=True,
        readonly=True,
    )
    total_persons = fields.Integer(
        related="booking_id.total_persons",
        string="Total Persons",
        store=True,
        readonly=True,
    )
    price_total = fields.Monetary(
        related="booking_id.price_total",
        string="Total",
        currency_field="currency_id",
        store=True,
        readonly=True,
    )
    currency_id = fields.Many2one(
        related="booking_id.currency_id",
        string="Currency",
        store=True,
        readonly=True,
    )
    note = fields.Char(string="Note")

    _sql_constraints = [
        (
            "tour_booking_line_unique_group_booking",
            "unique(group_id, booking_id)",
            "A booking can appear only once in the same booking group.",
        )
    ]
