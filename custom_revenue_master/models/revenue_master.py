from odoo import models, fields, api
from datetime import date
import calendar

class MonthlyCRMRevenue(models.Model):
    _name = 'monthly.crm.revenue'
    _description = 'Monthly CRM Revenue'

    name = fields.Selection([
                    ('01', 'January'),
                    ('02', 'February'),
                    ('03', 'March'),
                    ('04', 'April'),
                    ('05', 'May'),
                    ('06', 'June'),
                    ('07', 'July'),
                    ('08', 'August'),
                    ('09', 'September'),
                    ('10', 'October'),
                    ('11', 'November'),
                    ('12', 'December'),
                ],
        string="Month",
        required=True
    )
    year = fields.Selection(
        [(str(y), str(y)) for y in range(2020, 2035)],
        string="Year",
        required=True,
        default=lambda self: str(fields.Date.today().year)
    )
    revenue_line_ids = fields.One2many('monthly.crm.revenue.line', 'revenue_id', string="Revenue Lines")

    @api.model
    def create(self, vals):
        record = super().create(vals)

        # Fetch all CRM Tags
        crm_tags = self.env['crm.tag'].search([])

        # Create revenue lines for each tag
        for tag in crm_tags:
            self.env['monthly.crm.revenue.line'].create({
                'revenue_id': record.id,
                'tag_id': tag.id,
                'revenue_target': 0.0,
                'revenue_achieved': 0.0,
            })
        return record



class MonthlyCRMRevenueLine(models.Model):
    _name = 'monthly.crm.revenue.line'
    _description = 'Monthly CRM Revenue Line'

    revenue_id = fields.Many2one('monthly.crm.revenue', string="Month", ondelete='cascade')
    tag_id = fields.Many2one('crm.tag', string="CRM Tag", required=True)
    revenue_target = fields.Float(string="Revenue Target", required=True)
    revenue_achieved = fields.Float(
        string="Revenue Achieved",
        compute="_compute_revenue_achieved",
        store=True,
        readonly=False
    )
    achieved_percentage = fields.Float(string="Achieved %", compute="_compute_achieved_percentage", store=True)

    @api.depends('tag_id', 'revenue_id.name', 'revenue_id.year')
    def _compute_revenue_achieved(self):
        for line in self:
            if not line.tag_id or not line.revenue_id or not line.revenue_id.name or not line.revenue_id.year:
                line.revenue_achieved = 0.0
                continue

            try:
                year = int(line.revenue_id.year)
                month = int(line.revenue_id.name)
                start_dt = date(year, month, 1)
                last_day = calendar.monthrange(year, month)[1]
                end_dt = date(year, month, last_day)
            except Exception:
                line.revenue_achieved = 0.0
                continue

            # 1. Sum expected revenue from CRM Leads in Won or Partial Order Released stages with this tag_id in the date range
            lead_domain = [
                ('tag_ids', 'in', [line.tag_id.id]),
                ('stage_id.name', 'in', ['Won', 'Partial Order Released']),
                '|',
                '&', ('date_open', '>=', start_dt), ('date_open', '<=', end_dt),
                '&', ('create_date', '>=', start_dt), ('create_date', '<=', end_dt)
            ]
            leads = self.env['crm.lead'].search(lead_domain)
            lead_total = sum(leads.mapped('expected_revenue') or [0.0])

            # 2. Sum amount_total from confirmed Sale Orders linked to leads with this tag_id in the date range
            so_domain = [
                ('opportunity_id.tag_ids', 'in', [line.tag_id.id]),
                ('state', 'in', ['sale', 'done']),
                ('date_order', '>=', start_dt),
                ('date_order', '<=', end_dt)
            ]
            sale_orders = self.env['sale.order'].search(so_domain)
            so_total = sum(sale_orders.mapped('amount_total') or [0.0])

            line.revenue_achieved = max(lead_total, so_total)

    @api.depends('revenue_target', 'revenue_achieved')
    def _compute_achieved_percentage(self):
        for line in self:
            if line.revenue_target:
                line.achieved_percentage = (line.revenue_achieved / line.revenue_target) * 100
            else:
                line.achieved_percentage = 0.0
