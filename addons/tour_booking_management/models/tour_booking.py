from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class TourBooking(models.Model):
    _inherit = "tour.booking"

    duration_days = fields.Integer(
        string="Duration (Days)",
        compute="_compute_duration_days",
        store=True,
        readonly=True,
    )
    state = fields.Selection(
        selection_add=[("done", "Done"), ("cancelled", "Cancelled")],
        ondelete={"done": "set default", "cancelled": "set default"},
    )
    booking_line_ids = fields.One2many(
        "tour.booking.line",
        "booking_id",
        string="Group Lines",
        readonly=True,
    )

    @api.depends("travel_start_date", "travel_end_date")
    def _compute_duration_days(self):
        for booking in self:
            if (
                booking.travel_start_date
                and booking.travel_end_date
                and booking.travel_end_date >= booking.travel_start_date
            ):
                booking.duration_days = (
                    booking.travel_end_date - booking.travel_start_date
                ).days + 1
            else:
                booking.duration_days = 0

    @api.constrains("travel_start_date", "travel_end_date")
    def _check_travel_dates(self):
        for booking in self:
            if (
                booking.travel_start_date
                and booking.travel_end_date
                and booking.travel_end_date < booking.travel_start_date
            ):
                raise ValidationError(
                    _("Travel End Date must be greater than or equal to Travel Start Date.")
                )

    @api.model
    def _tbm_collect_group_keys_from_records(self, records):
        keys = set()
        for booking in records:
            if booking.package_id and booking.travel_start_date:
                company_id = booking.company_id.id or self.env.company.id
                keys.add((booking.package_id.id, booking.travel_start_date, company_id))
        return keys

    @api.model
    def _tbm_group_tables_ready(self):
        self.env.cr.execute(
            "SELECT to_regclass('public.tour_booking_group'), to_regclass('public.tour_booking_line')"
        )
        group_table, line_table = self.env.cr.fetchone()
        return bool(group_table and line_table)

    @api.model
    def _tbm_sync_groups_for_keys(self, keys):
        if not keys or not self._tbm_group_tables_ready():
            return

        Booking = self.sudo()
        Group = self.env["tour.booking.group"].sudo()
        Line = self.env["tour.booking.line"].sudo()

        for package_id, travel_start_date, company_id in keys:
            if not package_id or not travel_start_date:
                continue

            domain = [
                ("package_id", "=", package_id),
                ("travel_start_date", "=", travel_start_date),
                ("company_id", "=", company_id),
            ]
            bookings = Booking.search(domain, order="id")
            groups = Group.search(domain, order="id")

            if not bookings:
                groups.unlink()
                continue

            if groups:
                group = groups[0]
                if len(groups) > 1:
                    existing_booking_ids = set(group.line_ids.mapped("booking_id").ids)
                    for duplicate_group in groups[1:]:
                        for duplicate_line in duplicate_group.line_ids:
                            booking_id = duplicate_line.booking_id.id
                            if booking_id in existing_booking_ids:
                                duplicate_line.unlink()
                            else:
                                duplicate_line.group_id = group.id
                                existing_booking_ids.add(booking_id)
                    groups[1:].unlink()
            else:
                group = Group.create(
                    {
                        "package_id": package_id,
                        "travel_start_date": travel_start_date,
                        "company_id": company_id,
                    }
                )

            booking_ids = set(bookings.ids)
            existing_line_ids = set(group.line_ids.mapped("booking_id").ids)
            missing_booking_ids = sorted(booking_ids - existing_line_ids)
            if missing_booking_ids:
                Line.create(
                    [
                        {"group_id": group.id, "booking_id": booking_id}
                        for booking_id in missing_booking_ids
                    ]
                )

            stale_lines = group.line_ids.filtered(
                lambda line: line.booking_id.id not in booking_ids
            )
            if stale_lines:
                stale_lines.unlink()

    @api.model
    def _tbm_sync_existing_groups(self):
        if not self._tbm_group_tables_ready():
            return True

        bookings = self.sudo().search(
            [("package_id", "!=", False), ("travel_start_date", "!=", False)]
        )
        keys = self._tbm_collect_group_keys_from_records(bookings)
        self._tbm_sync_groups_for_keys(keys)

        Group = self.env["tour.booking.group"].sudo()
        for group in Group.search([]):
            has_booking = self.sudo().search(
                [
                    ("package_id", "=", group.package_id.id),
                    ("travel_start_date", "=", group.travel_start_date),
                    ("company_id", "=", group.company_id.id),
                ],
                limit=1,
            )
            if not has_booking:
                group.unlink()
        return True

    @api.model_create_multi
    def create(self, vals_list):
        bookings = super().create(vals_list)
        keys = self._tbm_collect_group_keys_from_records(bookings)
        self._tbm_sync_groups_for_keys(keys)
        return bookings

    def write(self, vals):
        keys_to_sync = set()
        tracked_keys = {"package_id", "travel_start_date", "company_id"}
        if tracked_keys.intersection(vals):
            keys_to_sync |= self._tbm_collect_group_keys_from_records(self)

        result = super().write(vals)

        if tracked_keys.intersection(vals):
            keys_to_sync |= self._tbm_collect_group_keys_from_records(self)
            self._tbm_sync_groups_for_keys(keys_to_sync)
        return result

    def unlink(self):
        keys = self._tbm_collect_group_keys_from_records(self)
        result = super().unlink()
        self._tbm_sync_groups_for_keys(keys)
        return result

    def action_confirm(self):
        result = super().action_confirm()
        self.write({"state": "confirmed"})
        return result

    def action_done(self):
        if hasattr(self, "action_complete"):
            self.action_complete()
        self.write({"state": "done"})
        return True

    def action_cancel(self):
        result = super().action_cancel()
        self.write({"state": "cancelled"})
        return result
