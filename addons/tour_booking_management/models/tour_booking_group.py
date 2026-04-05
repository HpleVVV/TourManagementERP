from odoo import _, api, fields, models


class TourBookingGroup(models.Model):
    _name = "tour.booking.group"
    _description = "Tour Booking Group"
    _order = "travel_start_date desc, package_id"

    name = fields.Char(string="Group Name", compute="_compute_name", store=True)
    package_id = fields.Many2one(
        "tour.package",
        string="Tour Package",
        required=True,
        ondelete="restrict",
        index=True,
    )
    travel_start_date = fields.Date(string="Travel Start Date", required=True, index=True)
    travel_end_date = fields.Date(string="Travel End Date", compute="_compute_group_stats", store=True)
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
    currency_id = fields.Many2one(
        "res.currency",
        related="company_id.currency_id",
        string="Currency",
        store=True,
        readonly=True,
    )
    line_ids = fields.One2many(
        "tour.booking.line",
        "group_id",
        string="Bookings",
        copy=False,
    )
    booking_count = fields.Integer(string="Bookings", compute="_compute_group_stats", store=True)
    customer_count = fields.Integer(string="Customers", compute="_compute_group_stats", store=True)
    total_persons = fields.Integer(string="Total Persons", compute="_compute_group_stats", store=True)
    total_amount = fields.Monetary(
        string="Total Amount",
        compute="_compute_group_stats",
        store=True,
        currency_field="currency_id",
    )

    _sql_constraints = [
        (
            "tour_booking_group_unique_key",
            "unique(package_id, travel_start_date, company_id)",
            "A group already exists for this package, start date, and company.",
        )
    ]

    @api.depends("package_id", "travel_start_date")
    def _compute_name(self):
        for group in self:
            if group.package_id and group.travel_start_date:
                group.name = _("%s - %s") % (
                    group.package_id.display_name,
                    group.travel_start_date,
                )
            else:
                group.name = _("New Group")

    @api.depends(
        "line_ids",
        "line_ids.booking_id.partner_id",
        "line_ids.booking_id.total_persons",
        "line_ids.booking_id.price_total",
        "line_ids.booking_id.travel_end_date",
    )
    def _compute_group_stats(self):
        for group in self:
            bookings = group.line_ids.mapped("booking_id")
            group.booking_count = len(bookings)
            group.customer_count = len(set(bookings.mapped("partner_id").ids))
            group.total_persons = sum(bookings.mapped("total_persons"))
            group.total_amount = sum(bookings.mapped("price_total"))
            group.travel_end_date = max(bookings.mapped("travel_end_date"), default=False)

    def action_refresh_group(self):
        for group in self:
            key = {(group.package_id.id, group.travel_start_date, group.company_id.id)}
            self.env["tour.booking"]._tbm_sync_groups_for_keys(key)
        return True

    def action_view_bookings(self):
        self.ensure_one()
        booking_ids = self.line_ids.mapped("booking_id").ids
        return {
            "type": "ir.actions.act_window",
            "name": _("Bookings"),
            "res_model": "tour.booking",
            "view_mode": "list,form",
            "domain": [("id", "in", booking_ids)],
            "context": {
                "default_package_id": self.package_id.id,
                "default_travel_start_date": self.travel_start_date,
            },
        }
