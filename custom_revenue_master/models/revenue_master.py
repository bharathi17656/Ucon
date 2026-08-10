from odoo import models, fields, api

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
    revenue_achieved = fields.Float(string="Revenue Achieved", required=True)
    achieved_percentage = fields.Float(string="Achieved %", compute="_compute_achieved_percentage", store=True)

    @api.depends('revenue_target', 'revenue_achieved')
    def _compute_achieved_percentage(self):
        for line in self:
            if line.revenue_target:
                line.achieved_percentage = (line.revenue_achieved / line.revenue_target) * 100
            else:
                line.achieved_percentage = 0.0
