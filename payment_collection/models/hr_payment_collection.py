import base64
import io
try:
    import xlrd
except ImportError:
    xlrd = None
from odoo import models, fields, api, _,exceptions
from odoo.exceptions import ValidationError,UserError
import pandas as pd
from io import BytesIO
from odoo.tools.float_utils import float_compare  # ✅ This line is required
from collections import defaultdict

import logging

_logger = logging.getLogger(__name__)  # Define the logger

class EmployeePaymentCollection(models.Model):
    _name = 'employee.payment.collection'
    _description = 'Employee Payment Collection'

    excel_file = fields.Binary(string="Upload Excel")
    line_ids = fields.One2many('employee.payment.collection.line', 'collection_id', string="Lines")
    month_name = fields.Selection([
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
                ], string="Month Name")
    
    soa_detail_ids = fields.One2many('employee.payment.soa.detail','collection_id',string='SOA Details')
    lock_month = fields.Boolean(string="Lock")
    _rec_name = 'month_name' 
    def name_get(self):
        result = []
        for rec in self:
            name = dict(self._fields['month_name'].selection).get(rec.month_name) or 'Undefined'
            result.append((rec.id, name))
        return result

    
    # def action_import_excel(self):
    #     self.ensure_one()

    #     if not self.excel_file:
    #         raise UserError("Please upload an Excel file first.")

    #     # Read Excel into pandas DataFrame
    #     data = base64.b64decode(self.excel_file)
    #     df = pd.read_excel(BytesIO(data))

    #     required_columns = ["SL No", "Employee Name", "Customer Code", "Customer Name", "Due Type", "Division", "Due Amount", "Collected Amount"]
    #     for col in required_columns:
    #         if col not in df.columns:
    #             raise UserError(f"Missing required column: {col}")

    #     # Preload tags for validation
    #     tag_names = self.env['crm.tag'].search([]).mapped('name')
    #     employees = self.env['hr.employee'].search([])
    #     emp_name_to_id = {e.name: e for e in employees}

    #     existing_snos = self.line_ids.mapped('sl_no')

    #     # Iterate and create line records
    #     for _, row in df.iterrows():
    #         sl_no = row['SL No']
    #         employee_name = row['Employee Name']
    #         division = row['Division']

    #            # SL No Uniqueness Check
    #         if sl_no in existing_snos:
    #             raise UserError(f"SL No '{sl_no}' already exists in this collection.")

    #             # Division validation
    #         if division not in tag_names:
    #             raise UserError(f"Division '{division}' not found in CRM tags.")

    #         # Employee validation
    #         if employee_name not in emp_name_to_id:
    #             raise UserError(f"Employee '{employee_name}' not found in HR Employee.")

    #         employee = emp_name_to_id[employee_name]
    #         user_id = employee.user_id.id

    #         self.env['employee.payment.collection.line'].create({
    #             'collection_id': self.id,
    #             'sl_no': row['SL No'],
    #             'employee_id': employee.id,
    #             'employee_name': employee_name,
    #             'customer_code': row['Customer Code'],
    #             'customer_name': row['Customer Name'],
    #             'due_type': row['Due Type'],
    #             'division': division,
    #             'due_amount': row['Due Amount'] or 0.0,
    #             'collected_amount': row['Collected Amount'] or 0.0,
    #         })

    
    # def action_import_excel(self):
    #     self.ensure_one()
    
    #     if not self.excel_file:
    #         raise UserError("Please upload an Excel file first.")
    
    #     # Read Excel into pandas DataFrame
    #     data = base64.b64decode(self.excel_file)
    #     df = pd.read_excel(BytesIO(data))
    
    #     required_columns = ["SL No", "Employee Name", "Customer Code", "Customer Name", "Due Type", "Division", "Due Amount", "Collected Amount"]
    #     for col in required_columns:
    #         if col not in df.columns:
    #             raise UserError(f"Missing required column: {col}")
    
    #     # Preload tags and employee mappings
    #     tag_names = self.env['crm.tag'].search([]).mapped('name')
    #     employees = self.env['hr.employee'].search([])
    #     emp_name_to_id = {e.name: e for e in employees}
    #     existing_snos = self.line_ids.mapped('sl_no')
    
    #     for _, row in df.iterrows():
    #         sl_no = row['SL No']
    #         employee_name = str(row['Employee Name']).strip()
    #         division = str(row['Division']).strip()
    
    #         # SL No Uniqueness Check
    #         if sl_no in existing_snos:
    #             raise UserError(f"SL No '{sl_no}' already exists in this collection.")
    
    #         # Division validation
    #         if division not in tag_names:
    #             raise UserError(f"Division '{division}' not found in CRM tags.")
    
    #         # Employee validation
    #         if employee_name not in emp_name_to_id:
    #             raise UserError(f"Employee '{employee_name}' not found in HR Employee.")
    
    #         # Handle NaN or empty cells for amounts
    #         due_amount = 0.0 if pd.isna(row['Due Amount']) else row['Due Amount']
    #         collected_amount = 0.0 if pd.isna(row['Collected Amount']) else row['Collected Amount']
    
    #         employee = emp_name_to_id[employee_name]
    
    #         self.env['employee.payment.collection.line'].create({
    #             'collection_id': self.id,
    #             'sl_no': sl_no,
    #             'employee_id': employee.id,
    #             'employee_name': employee_name,
    #             'customer_code': str(row['Customer Code']).strip(),
    #             'customer_name': str(row['Customer Name']).strip(),
    #             'due_type': str(row['Due Type']).strip(),
    #             'division': division,
    #             'due_amount': due_amount,
    #             'collected_amount': collected_amount,
    #         })


    def action_open_form_view(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Employee Payment Collection',
            'res_model': 'employee.payment.collection',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'current',
        }


    def generate_soa_details(self):
        """
        Aggregate payment lines by (employee, division, customer).
        Update existing SOA details or create new ones if not found.
        Round outstanding amount to 2 decimal digits.
        """
        self.ensure_one()
        detail_model = self.env['employee.payment.soa.detail']
    
        # Prepare data from payment lines
        grouped = {}
        for line in self.line_ids:
            if not line.employee_id or not line.divition_id or not line.customer_id:
                continue
    
            key = (line.employee_id.id, line.divition_id.id, line.customer_id.id)
            grouped[key] = grouped.get(key, 0.0) + line.due_amount
    
        for (emp_id, div_id, cust_id), total in grouped.items():
            total = round(total, 2)  # Round to 2 decimal places
    
            # Check if detail already exists
            existing = detail_model.search([
                ('collection_id', '=', self.id),
                ('employee_id', '=', emp_id),
                ('division_id', '=', div_id),
                ('customer_id', '=', cust_id),
            ], limit=1)
    
            if existing:
                existing.outstanding_amount = total
            else:
                detail_model.create({
                    'collection_id': self.id,
                    'employee_id': emp_id,
                    'division_id': div_id,
                    'customer_id': cust_id,
                    'outstanding_amount': total,
                })
    
        return {
                'name': 'Upload SOA',
                'type': 'ir.actions.act_window',
                'res_model': 'employee.payment.soa.detail',
                'view_mode': 'list',
                'domain':[('collection_id', 'in', [self.id])],
                'target': 'new',
               'context': {
                         'default_collection_id': self.id,
                        },
            }

   

    # def generate_soa_details(self):
    #     """
    #     Aggregate existing payment lines by (employee, division, customer) and
    #     create SOA detail records with summed outstanding_amount.
    #     """
    #     self.ensure_one()
    #     # Remove old details
    #     self.soa_detail_ids.unlink()
    
    #     grouped = {}
    #     for line in self.line_ids:
    #         if not line.employee_id or not line.divition_id or not line.customer_id:
    #             continue  # Skip lines with missing mandatory fields
    
    #         emp = line.employee_id.id
    #         div = line.divition_id.id
    #         cust = line.customer_id.id
    #         key = (emp, div, cust)
    #         grouped[key] = grouped.get(key, 0.0) + line.due_amount
    
    #     for (emp, div, cust), total in grouped.items():
    #         self.env['employee.payment.soa.detail'].create({
    #             'collection_id': self.id,
    #             'employee_id': emp,
    #             'division_id': div,
    #             'customer_id': cust,
    #             'outstanding_amount': total,
    #         })
    
    #     return True


    def action_import_excel(self):
        self.ensure_one()
    
        if not self.excel_file:
            raise UserError("Please upload an Excel file first.")
    
        # Read Excel into pandas DataFrame
        data = base64.b64decode(self.excel_file)
        df = pd.read_excel(BytesIO(data))
    
        required_columns = ["SL No", "Employee Name", "Customer Code", "Customer Name", "Due Type", "Division", "Due Amount", "Collected Amount"]
        for col in required_columns:
            if col not in df.columns:
                raise UserError(f"Missing required column: {col}")
    
        # Preload mappings
        tag_map = {tag.name.strip(): tag.id for tag in self.env['crm.tag'].search([])}
        emp_map = {emp.name.strip(): emp for emp in self.env['hr.employee'].search([])}
        customer_map = {partner.name.strip(): partner.id for partner in self.env['res.partner'].search([])}
        existing_snos = self.line_ids.mapped('sl_no')
    
        for _, row in df.iterrows():
            sl_no = row['SL No']
            employee_name = str(row['Employee Name']).strip()
            division_name = str(row['Division']).strip()
            customer_name = str(row['Customer Name']).strip()
    
            # SL No uniqueness check
            if sl_no in existing_snos:
                raise UserError(f"SL No '{sl_no}' already exists in this collection.")
    
            # Validate division and employee
            if division_name not in tag_map:
                raise UserError(f"Division '{division_name}' not found in CRM tags.")
            if employee_name not in emp_map:
                raise UserError(f"Employee '{employee_name}' not found in HR Employee.")
    
            # Validate customer name
            if customer_name not in customer_map:
                raise UserError(f"Customer '{customer_name}' not found in system.")
    
            # Safe defaulting for amounts
            due_amount = 0.0 if pd.isna(row['Due Amount']) else row['Due Amount']
            collected_amount = 0.0 if pd.isna(row['Collected Amount']) else row['Collected Amount']
    
            employee = emp_map[employee_name]
            divition_id = tag_map.get(division_name)
            customer_id = customer_map.get(customer_name)
    
            values = {
                'collection_id': self.id,
                'sl_no': sl_no,
                'employee_id': employee.id,
                'employee_name': employee_name,
                'customer_code': str(row['Customer Code']).strip(),
                'customer_name': customer_name,
                'customer_id': customer_id,
                'due_type': str(row['Due Type']).strip(),
                'division': division_name,
                'divition_id': divition_id,
                'due_amount': due_amount,
                'collected_amount': collected_amount,
            }
    
            self.env['employee.payment.collection.line'].create(values)
    
    
    

class EmployeePaymentCollectionLine(models.Model):
    _name = 'employee.payment.collection.line'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Payment Collection'
    
    
    collection_id = fields.Many2one('employee.payment.collection', string="Collection Reference", required=True, ondelete="cascade")
    month_name = fields.Selection(
        related='collection_id.month_name',
        string='Month',
        store=True,  # optional: only if you want to filter/sort by it
        readonly=True
    )
    
    sl_no = fields.Integer(string="SL No")
    employee_id = fields.Many2one('hr.employee', string="Employee", required=False)
    employee_name = fields.Char(string="Employee Name", required=True)

    customer_code = fields.Char(string="Customer Code", required=True)
    customer_name = fields.Char(string="Customer Name", required=True)
    customer_id =fields.Many2one('res.partner', string="Customer Id", required=False)

    division = fields.Char(string="Division", required=True)
    divition_id =fields.Many2one('crm.tag', string="Tag Id", required=False)
    
    _rec_name = 'customer_name' 

    due_type = fields.Selection([
        ('due', 'Due'),
        ('overdue', 'Overdue'),
        ('nodue', 'No Due')
    ], string="Due Type", required=True)

    due_amount = fields.Float(string="Due Amount", required=True)
    collected_amount = fields.Float(string="Collected Amount", default=0.0)
    month_name = fields.Selection(related='collection_id.month_name', store=True)


    
    activity_count = fields.Integer(string="Activity Count", compute="_compute_activity_count", store=False)

    verified = fields.Boolean(string="Verified")
    is_boolean_field = fields.Boolean(compute="_compute_is_boolean_field")




    def action_open_form_view(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'SOA Detail',
            'res_model': 'employee.payment.collection.line',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'current',
        }

    def action_bulk_send_reminder(self):
        template = self.env.ref('payment_collection.email_template_payment_overdue')
        attachment_ids = []
        related_ids = []
    
        if not self:
            raise UserError("No records selected.")
    
        # Single record logic
        if len(self) == 1:
            rec = self[0]
            related_ids = [rec.id]
    
            soa_detail = self.env['employee.payment.soa.detail'].search([
                ('employee_id', '=', rec.employee_id.id),
                ('division_id', '=', rec.divition_id.id),
                ('customer_id', '=', rec.customer_id.id),
                ('collection_id', '=', rec.collection_id.id)
            ], limit=1)
    
            if soa_detail and soa_detail.soa_file:
                attachment = self.env['ir.attachment'].create({
                    'name': f'SOA_{rec.customer_name}.pdf',
                    'type': 'binary',
                    'datas': soa_detail.soa_file,
                    'res_model': 'employee.payment.collection.line',
                    'res_id': rec.id,
                })
                attachment_ids.append(attachment.id)
    
            subject = f"Payment Overdue: {rec.customer_name} - {rec.division}"
            partner_ids = [(4, rec.customer_id.id)]
    
        else:
            # Multi-record logic
            first = self[0]
            related_ids = self.ids
    
            same_customer = all(rec.customer_id.id == first.customer_id.id for rec in self)
            same_division = all(rec.divition_id.id == first.divition_id.id for rec in self)
            same_employee = all(rec.employee_id.id == first.employee_id.id for rec in self)
    
            if not (same_customer and same_division and same_employee):
                raise UserError("Cannot send email: All selected records must have the same Customer, Division, and Employee.")
    
            soa_detail = self.env['employee.payment.soa.detail'].search([
                ('employee_id', '=', first.employee_id.id),
                ('division_id', '=', first.divition_id.id),
                ('customer_id', '=', first.customer_id.id),
                ('collection_id', '=', first.collection_id.id)
            ], limit=1)
    
            if soa_detail and soa_detail.soa_file:
                attachment = self.env['ir.attachment'].create({
                    'name': f'SOA_{first.customer_name}.pdf',
                    'type': 'binary',
                    'datas': soa_detail.soa_file,
                    'res_model': 'employee.payment.collection.line',
                    'res_id': first.id,
                })
                attachment_ids.append(attachment.id)
    
            subject = f"Payment Overdue: {first.customer_name} - {first.division}"
            partner_ids = [(4, first.customer_id.id)]
    
        # Prepare email context
        context = {
            'default_model': 'employee.payment.collection.line',
            'default_use_template': True,
            'default_template_id': template.id,
            'default_composition_mode': 'comment',  # always 'comment' so "To" field shows
            'default_res_ids': related_ids,
            'default_attachment_ids': [(4, att_id) for att_id in attachment_ids],
            'default_partner_ids': partner_ids,
            'default_subject': subject,
        }
    
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'mail.compose.message',
            'view_mode': 'form',
            'target': 'new',
            'context': context,
        }

    
    def _compute_is_boolean_field(self):
        for record in self:
            if self.env.user.has_group('base.group_system') or self.env.user.has_group('payment_collection.custom_accounts_payment_team'):
                record.is_boolean_field = False
            else:
                record.is_boolean_field = True

    def _compute_activity_count(self):
        MailActivity = self.env['mail.activity']
        DoneActivity = self.env['crm.done.activitys']
        for rec in self:
            open_count = MailActivity.search_count([
                ('res_model', '=', self._name),
                ('res_id', '=', rec.id)
            ])
            done_count = DoneActivity.search_count([
                ('res_model', '=', self._name),
                ('res_id', '=', rec.id)
            ])
            rec.activity_count = open_count + done_count
    @api.onchange('employee_name')
    def _onchange_employee_name(self):
        if self.employee_name:
            employee = self.env['hr.employee'].search([('name', '=', self.employee_name)], limit=1)
            if employee:
                self.employee_id = employee.id
            else:
                self.employee_id = False

    @api.constrains('division', 'employee_name')
    def _check_division_and_employee(self):
        for rec in self:
            crm_tags = self.env['crm.tag'].search([]).mapped('name')
            if rec.division not in crm_tags:
                raise ValidationError(_("Division '%s' not found in CRM Tags.") % rec.division)

            employee = self.env['hr.employee'].search([('name', '=', rec.employee_name)], limit=1)
            if not employee:
                raise ValidationError(_("Employee '%s' not found in HR records.") % rec.employee_name)
            else:
                rec.employee_id = employee.id


    def write(self, vals):
        res = super().write(vals)
        if 'collected_amount' in vals:
            for rec in self:
                rec._send_collection_email_if_applicable()
        return res

    def update_customer_and_division(self):
        records = self.env['employee.payment.collection.line'].search([])
    
        for rec in records:
            # Match Customer
            customer = self.env['res.partner'].search([('name', '=', rec.customer_name)], limit=1)
            # Match Division (Assuming it's using crm.tag model)
            division = self.env['crm.tag'].search([('name', '=', rec.division)], limit=1)
    
            updates = {}
            if customer:
                updates['customer_id'] = customer.id
            if division:
                updates['divition_id'] = division.id
    
            if updates:
                rec.write(updates)

    def _send_collection_email_if_applicable(self):
        if float_compare(self.collected_amount, 0.0, precision_rounding=0.01) > 0:
            accounts_group = self.env.ref('payment_collection.custom_accounts_payment_team')
            accounts_users = self.env['res.users'].search([('groups_id', 'in', accounts_group.id)])

            email_to = ",".join(user.partner_id.email for user in accounts_users if user.partner_id.email)
            if email_to:
                subject = f"New Payment Collection Updated: {self.customer_name} : {self.collected_amount}"
                body = f"""
                <p><strong>Customer Name:</strong> {self.customer_name}</p>
                <p><strong>Sales Engineer:</strong> {self.employee_name}</p>
                <p><strong>Division:</strong> {self.division}</p>
                <p><strong>Due Type:</strong> {self.due_type}</p>
                <p><strong>Due Amount:</strong> {self.due_amount}</p>
                <p><strong>Collected Amount:</strong> {self.collected_amount}</p>
                <br/>
                <p>Regards,<br/>Odoo Team</p>
                """
                self.env['mail.mail'].create({
                    'subject': subject,
                    'body_html': body,
                    'email_to': email_to,
                }).send()





class CrmLead(models.Model):
    _inherit = 'crm.lead'

    meeting_count = fields.Integer(string="Meeting", compute="_compute_activity_counts", store=False)
    call_count = fields.Integer(string="Call", compute="_compute_activity_counts", store=False)
    site_meeting_count = fields.Integer(string="Site Meeting", compute="_compute_activity_counts", store=False)
    consultant_meeting_count = fields.Integer(string="Consultant Meeting", compute="_compute_activity_counts", store=False)
    email_count = fields.Integer(string="Email", compute="_compute_activity_counts", store=False)
    todo_count = fields.Integer(string="To-Do", compute="_compute_activity_counts", store=False)

    @api.depends('activity_ids.activity_type_id', 'activity_ids.res_id')
    def _compute_activity_counts(self):
        Activity = self.env['mail.activity']
        DoneActivity = self.env['crm.done.activitys']

        for rec in self:
            summary = defaultdict(int)

            # Open activities
            open_acts = Activity.search([
                ('res_model', '=', 'crm.lead'),
                ('res_id', '=', rec.id),
            ])
            for act in open_acts:
                name = act.activity_type_id.name or ''
                summary[name] += 1

            # Done activities
            done_acts = DoneActivity.search([('lead_id', '=', rec.id)])
            for act in done_acts:
                name = act.name or ''
                summary[name] += 1

            # Assign values to fields
            rec.meeting_count = summary.get('Meeting', 0)
            rec.call_count = summary.get('Call', 0)
            rec.site_meeting_count = summary.get('Site Meeting', 0)
            rec.consultant_meeting_count = summary.get('Consultant Meeting', 0)
            rec.email_count = summary.get('Email', 0)
            rec.todo_count = summary.get('To-Do', 0)



class EmployeePaymentSOADetail(models.Model):
    _name = 'employee.payment.soa.detail'
    _description = 'SOA Detail (Aggregated Outstanding)'

    collection_id = fields.Many2one(
        'employee.payment.collection',
        string='Collection',
        required=True,
        ondelete='cascade',
    )
    
    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        required=True,
    )
    division_id = fields.Many2one(
        'crm.tag',
        string='Division',
        required=True,
    )
    customer_id = fields.Many2one(
        'res.partner',
        string='Customer',
        required=True,
    )
    outstanding_amount = fields.Float(
        string='Outstanding Amount',
        required=True,
        default=0.0,
    )
    soa_file = fields.Binary(
        string='SOA (Statement of Account)'
    )





class MailActivity(models.Model):
    _inherit = 'mail.activity'

    project_name = fields.Char(string='Project Name')
    customer_name = fields.Char(string='Customer Name')
    

    @api.model
    def create(self, vals):
        # Check if it's related to crm.lead
        if vals.get('res_model') == 'crm.lead' and vals.get('res_id'):
            lead = self.env['crm.lead'].browse(vals['res_id'])
            if lead:
                # Assign lead's job_type to project_name
                vals['project_name'] = lead.job_type or ''
                vals['customer_name']=lead.partner_id.name
                
            else:
                vals['project_name'] = ''
                vals['customer_name']= ''
                
        elif vals.get('res_model') == 'res.partner' and vals.get('res_id'):
            partner = self.env['res.partner'].browse(vals['res_id'])
            if partner:
                # Assign lead's job_type to x_project_name
                vals['project_name'] =  ''
                vals['customer_name']=partner.name
                
            else:
                vals['project_name'] = ''
                vals['customer_name']= ''

        elif vals.get('res_model') == 'employee.payment.collection.line' and vals.get('res_id'):
            collection = self.env['employee.payment.collection.line'].browse(vals['res_id'])
            if collection:
                # Assign lead's job_type to x_project_name
                vals['project_name'] =  ''
                vals['customer_name']=collection.customer_name
                
            else:
                vals['project_name'] = ''
                vals['customer_name']= ''
            
        else:
            vals['project_name'] = '' 
            vals['customer_name']= ''

        return super(MailActivity, self).create(vals)



    def update_existing_activities(self):
        activities = self.env['mail.activity'].search([])
        for activity in activities:
            if activity.res_model == 'crm.lead' and activity.res_id:
                lead = self.env['crm.lead'].browse(activity.res_id)
                if lead:
                    activity.project_name = lead.job_type or ''
                    activity.customer_name = lead.partner_id.name or ''
                else:
                    activity.project_name = ''
                    activity.customer_name = ''
    
            elif activity.res_model == 'res.partner' and activity.res_id:
                partner = self.env['res.partner'].browse(activity.res_id)
                if partner:
                    activity.project_name = ''
                    activity.customer_name = partner.name or ''
                else:
                    activity.project_name = ''
                    activity.customer_name = ''
    
            elif activity.res_model == 'employee.payment.collection.line' and activity.res_id:
                collection = self.env['employee.payment.collection.line'].browse(activity.res_id)
                if collection:
                    activity.project_name = ''
                    activity.customer_name = collection.customer_name or ''
                else:
                    activity.project_name = ''
                    activity.customer_name = ''
    
            else:
                activity.project_name = ''
                activity.customer_name = ''
    





class UploadBulkSOAWizard(models.TransientModel):
    _name = 'upload.bulk.soa.wizard'
    _description = 'Upload Bulk SOA Files Wizard'

    collection_id = fields.Many2one('employee.payment.collection', string="Collection")
    sales_person=fields.Many2one('hr.employee',string="Sales Person")
    tag_id=fields.Many2one('crm.tag',string="Company")
    number_of_records=fields.Char(string='Total Records')
    upload_file_ids = fields.Many2many('ir.attachment', string="Upload Files")
    
    @api.onchange('sales_person', 'tag_id')
    def _onchange_records(self):
        domain = [('collection_id', '=', self.collection_id.id)]
        if self.sales_person:
            domain.append(('employee_id', '=', self.sales_person.id))
        if self.tag_id:
            domain.append(('division_id', '=', self.tag_id.id))

        soa_records_count = self.env['employee.payment.soa.detail'].search_count(domain)
        self.number_of_records = f'{soa_records_count} Available'
        
        
            
            

    def action_upload_soas(self):
        if not self.collection_id:
            raise UserError("Collection record not found.")

        soa_details = self.env['employee.payment.soa.detail'].search([
            ('collection_id', '=', self.collection_id.id),
            ('division_id','=',self.tag_id.id),
            ('employee_id','=',self.sales_person.id),
            
        ])

        if not soa_details:
            raise UserError("No SOA Detail records found for this Collection.")

        uploaded = 0
        skipped_existing = 0
        not_found = 0

        for attachment in self.upload_file_ids:
            customer_name = attachment.name.split('.')[0].strip()

            # Find SOA record inside this collection only
            soa_record = soa_details.filtered(lambda s: s.customer_id.name == customer_name)

            if soa_record:
                if soa_record.soa_file:
                    skipped_existing += 1  # Already has a file
                else:
                    soa_record.soa_file = attachment.datas
                    uploaded += 1
            else:
                not_found += 1  # No matching customer

        message = f"{uploaded} file(s) uploaded successfully."
        if skipped_existing:
            message += f" {skipped_existing} file(s) skipped (already uploaded)."
        if not_found:
            message += f" {not_found} file(s) skipped (no matching customer found)."

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': ('SOA Upload Result'),
                'message': message,
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }

