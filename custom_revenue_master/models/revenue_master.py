from odoo import models, fields, api
import calendar
from datetime import date

class MonthlyCRMRevenue(models.Model):
    _name = 'monthly.crm.revenue'
    _description = 'Monthly CRM Revenue'
    _inherit = ['mail.thread', 'mail.activity.mixin']

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
        required=True,
        tracking=True
    )
    year = fields.Selection(
        [(str(y), str(y)) for y in range(2025, 2036)],
        string="Year",
        required=True,
        default=lambda self: str(fields.Date.today().year),
        tracking=True
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
            })
        return record


class MonthlyCRMRevenueLine(models.Model):
    _name = 'monthly.crm.revenue.line'
    _description = 'Monthly CRM Revenue Line'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    revenue_id = fields.Many2one('monthly.crm.revenue', string="Month", ondelete='cascade', tracking=True)
    tag_id = fields.Many2one('crm.tag', string="CRM Tag", required=True, tracking=True)
    revenue_target = fields.Float(string="Revenue Target", required=True, tracking=True)
    revenue_achieved = fields.Float(string="Revenue Achieved", compute="_compute_revenue_achieved", store=True, tracking=True)
    achieved_percentage = fields.Float(string="Achieved %", compute="_compute_achieved_percentage", store=True)
    invoice_ids = fields.Many2many('account.move', compute='_compute_achieved_invoices', string="Achieved Customer Invoices")

    @api.depends('revenue_id.name', 'revenue_id.year', 'tag_id')
    def _compute_achieved_invoices(self):
        month_map_nums = {
            'january': 1, 'february': 2, 'march': 3, 'april': 4,
            'may': 5, 'june': 6, 'july': 7, 'august': 8,
            'september': 9, 'october': 10, 'november': 11, 'december': 12,
            '01': 1, '02': 2, '03': 3, '04': 4, '05': 5, '06': 6,
            '07': 7, '08': 8, '09': 9, '10': 10, '11': 11, '12': 12,
        }
        for line in self:
            if not line.revenue_id or not line.revenue_id.year or not line.revenue_id.name:
                line.invoice_ids = False
                continue

            try:
                target_year = int(line.revenue_id.year)
            except ValueError:
                target_year = fields.Date.today().year

            m_num = month_map_nums.get(str(line.revenue_id.name).lower())
            if not m_num or not (1 <= m_num <= 12):
                line.invoice_ids = False
                continue

            start_date = date(target_year, m_num, 1)
            last_day = calendar.monthrange(target_year, m_num)[1]
            end_date = date(target_year, m_num, last_day)

            inv_domain = [
                ('state', '=', 'posted'),
                ('move_type', 'in', ['out_invoice', 'out_refund']),
                ('invoice_date', '>=', start_date),
                ('invoice_date', '<=', end_date),
            ]

            if 'x_studio_division' in self.env['crm.team']._fields:
                try:
                    teams_with_tag = self.env['crm.team'].search([('x_studio_division', 'in', [line.tag_id.id])])
                    if teams_with_tag:
                        inv_domain.append(('team_id', 'in', teams_with_tag.ids))
                except Exception:
                    pass

            invoices = self.env['account.move'].search(inv_domain)
            line.invoice_ids = invoices

    @api.depends('invoice_ids', 'invoice_ids.state', 'invoice_ids.amount_untaxed_signed', 'invoice_ids.amount_untaxed')
    def _compute_revenue_achieved(self):
        for line in self:
            calc = 0.0
            for inv in line.invoice_ids:
                if inv.state == 'posted':
                    amount = inv.amount_untaxed_signed or inv.amount_untaxed or 0.0
                    if inv.move_type == 'out_refund':
                        calc -= abs(amount)
                    else:
                        calc += abs(amount)
            line.revenue_achieved = round(calc, 2)

    @api.depends('revenue_target', 'revenue_achieved')
    def _compute_achieved_percentage(self):
        for line in self:
            if line.revenue_target:
                line.achieved_percentage = (line.revenue_achieved / line.revenue_target) * 100
            else:
                line.achieved_percentage = 0.0
