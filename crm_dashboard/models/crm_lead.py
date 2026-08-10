import logging
from odoo import models, fields, api,exceptions,_
from datetime import datetime
import calendar
from collections import defaultdict
from datetime import date
from dateutil.relativedelta import relativedelta
from odoo.addons.mail.models.mail_activity import MailActivity as MailActivityOriginal
_logger = logging.getLogger(__name__)  # Define the logger



class HrEmployeePrivate(models.Model):

    _inherit = "hr.employee"

    category_ids = fields.Many2many(
        'hr.employee.category', 'employee_category_rel',
        'employee_id', 'category_id', groups="hr.group_hr_user,crm_dashboard.dashboard_team_leader,payment_collection.group_employee_payment_employee,payment_collection.group_employee_payment_manager,may_month_changes.group_employee_accesss_own_record,may_month_changes.group_division_access",
        string='Tags')



class EmployeePaymentCollectionLine(models.Model):
    _inherit = 'employee.payment.collection.line'


    @api.model
    def _is_team_lead(self, user):
        team_ids = self.env['crm.team'].search([('user_id', '=', user.id)]).ids
        if not team_ids:
            return []
        team_members = self.env['crm.team.member'].search([('crm_team_id', 'in', team_ids)])
        return team_members.mapped('user_id.id')

    @api.model
    def _get_team_lead_domain(self):
        user = self.env.user
        if user.has_group('crm_dashboard.dashboard_team_leader'):
            member_ids = self._is_team_lead(user)
            return ['|', ('employee_id.user_id.id', '=', user.id), ('employee_id.user_id.id', 'in', member_ids)]
        return [('employee_id.user_id.id', '=', user.id)]

    @api.model
    def search(self, args, offset=0, limit=None, order=None):
        user = self.env.user
        if user.has_group('crm_dashboard.dashboard_team_leader') and not user.has_group('base.group_system'):
            args += self._get_team_lead_domain()
        return super().search(args, offset=offset, limit=limit, order=order)



class MailActivity(models.Model):
    _inherit = 'mail.activity'

    
    partner_name = fields.Char(
        string='Partner Name',
        store=True,
        readonly=False,
    )

    partner_mobile = fields.Char(
        string='Partner Mobile', 
        store=True,
        readonly=False,
    )

    
    start_date = fields.Datetime(string='Meeting Start Date', readonly=True)


    
    activity_from = fields.Selection(
            selection=[
                ('res.partner', 'Contact'),
                ('employee.payment.collection.line', 'Payment'),
                ('crm.lead', 'CRM'),
                ('others', 'Others')
            ],
            string='Activity From',
            compute='_compute_activity_from',
            store=True
        )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'res_model' in vals:
                vals['activity_from'] = vals['res_model'] if vals['res_model'] in ['res.partner', 'employee.payment.collection.line', 'crm.lead'] else 'others'
        return super().create(vals_list)
    
    def write(self, vals):
        if 'res_model' in vals:
            vals['activity_from'] = vals['res_model'] if vals['res_model'] in ['res.partner', 'employee.payment.collection.line', 'crm.lead'] else 'others'
        return super().write(vals)


    # def action_open_in_calendar(self):
    #     if self.calendar_event_id:
    #         return {
    #             'type': 'ir.actions.act_window',
    #             'name': 'Calendar View',
    #             'res_model': 'calendar.event',
    #             'view_mode': 'calendar',
    #             'domain': [('id', '=', self.calendar_event_id.id)],
    #             'context': {
    #                 'default_res_model': self.res_model,
    #                 'default_res_id': self.res_id,
    #             }
    #         }


    #     else:
                
    #         return {
    #             'type': 'ir.actions.act_window',
    #             'name': 'Calendar View',
    #             'res_model': 'mail.activity',
    #             'view_mode': 'calendar',
    #             'domain': [('id', '=', self.id)],
    #             'context': {
    #                 'default_res_model': self.res_model,
    #                 'default_res_id': self.res_id,
    #             }
    #         }

    @api.depends('res_model')
    def _compute_activity_from(self):
        for record in self:
            if record.res_model in ['res.partner', 'employee.payment.collection.line', 'crm.lead']:
                record.activity_from = record.res_model
            else:
                record.activity_from = 'others'



    @api.model
    def update_existing_activity_from(self):
        # Define the known models
        known_models = ['res.partner', 'employee.payment.collection.line', 'crm.lead']

        # Fetch all activities
        activities = self.search([])

        for activity in activities:
            if activity.res_model in known_models:
                activity.activity_from = activity.res_model
            else:
                activity.activity_from = 'others'
                

class CrmDoneActivity(models.Model):
    _name = 'crm.done.activitys'
    _description = 'Archived CRM Activities'

    name = fields.Char(string="Activity Type", required=True)
    # lead_id = fields.Many2one('crm.lead', string="Lead", ondelete='set null')
    lead_id = fields.Many2one('crm.lead', string="Lead (Old)", readonly=True)
    user_id = fields.Many2one('res.users', string="Assigned User", required=True)
    date_done = fields.Date(string="Completed Date", default=fields.Date.today)
    note = fields.Text(string="Description")
    expected_revenue = fields.Float(string="Expected Revenue")
    activity_id = fields.Many2one('mail.activity', string="Original Activity", ondelete='set null')
    res_model = fields.Char(string="Related Model")
    res_id = fields.Integer(string="Related Record ID")
     # old field
  

    # new reference field
    activity_ref = fields.Reference(selection='_referenceable_models', string="Related Record", readonly=True, compute='_compute_activity_ref', store=True)

    res_model = fields.Char(string="Related Model")
    res_id = fields.Integer(string="Related Record ID")

    @api.depends('res_model', 'res_id', 'lead_id')
    def _compute_activity_ref(self):
        for rec in self:
            if rec.res_model and rec.res_id:
                rec.activity_ref = f'{rec.res_model},{rec.res_id}'
            elif rec.lead_id:
                rec.activity_ref = f'crm.lead,{rec.lead_id.id}'
                
    @api.model
    def _referenceable_models(self):
        base = [
            ('crm.lead', 'Lead'),
            ('res.partner', 'Contact'),
            ('sale.order', 'Sale Order'),
            ('employee.payment.collection.line', 'Employee Payment Line'),
        ]
        # Dynamically add other models used in activities
        used_models = self.env['mail.activity'].search([]).mapped('res_model')
        dynamic_models = [(model, model.replace('.', ' ').title()) for model in used_models if model not in dict(base)]
        return base + dynamic_models


class MailActivity(models.Model):   
    _inherit="mail.activity"  

    customer_name = fields.Char(string="Customer Name", compute="_compute_customer_name", store=True)

    @api.depends('res_model', 'res_id')
    def _compute_customer_name(self):
        for activity in self:
            customer = ''
            if activity.res_model and activity.res_id:
                try:
                    record = self.env[activity.res_model].browse(activity.res_id)
                    if activity.res_model == 'res.partner':
                        customer = record.name
                    elif activity.res_model == 'crm.lead':
                        customer = record.partner_id.name if record.partner_id else ''
                    elif activity.res_model == 'employee.payment.collection.line':
                        customer = record.customer_id.name if record.customer_id else ''
                except Exception:
                    customer = ''
            activity.customer_name = customer



    def update_existing_customer_names(self):
        activities = self.env['mail.activity'].search([])  # or use domain if needed
        for activity in activities:
            customer = ''
            if activity.res_model and activity.res_id:
                try:
                    record = self.env[activity.res_model].browse(activity.res_id)
                    if activity.res_model == 'res.partner':
                        customer = record.name
                    elif activity.res_model == 'crm.lead':
                        customer = record.partner_id.name if record.partner_id else ''
                    elif activity.res_model == 'employee.payment.collection.line':
                        customer = record.customer_id.name if record.customer_id else ''
                except Exception:
                    continue  # skip if record not found or invalid
    
            activity.write({'customer_name': customer})

    
    @api.model_create_multi
    def create(self, vals_list):

        activities = super().create(vals_list)
           
        for activity in activities:
            if activity.res_model == 'employee.payment.collection.line':
                if activity._context.get('prevent_activity_recursion'):
                    continue
                
                res_model_id = self.env['ir.model']._get_id('employee.payment.collection.line')
                current_record = self.env['employee.payment.collection.line'].browse(activity.res_id)
                
                _logger.info("Current Record: ID=%s, Customer=%s, Division=%s, Employee=%s, Collection=%s",
                    current_record.id,
                    current_record.customer_id.name,
                    current_record.divition_id.name,
                    current_record.employee_id.name,
                )

                related_records = self.env['employee.payment.collection.line'].search([
                    ('id', '!=', current_record.id),
                    # ('divition_id', '=', current_record.divition_id.id),
                    ('customer_name', '=', current_record.customer_name),
                    ('employee_id', '=', current_record.employee_id.id),
                    ('collection_id', '=', current_record.collection_id.id),
                ])

                _logger.info("Related Records Found: %s", related_records.ids)

                # Normalize the date
                deadline = activity.date_deadline
                _logger.info("Original Activity Deadline: %s", deadline)

                for record in related_records:
                    _logger.info("Copying activity to Record ID: %s", record.id)

                    self.with_context(prevent_activity_recursion=True).sudo().create({
                        'activity_type_id': activity.activity_type_id.id,
                        'customer_name': activity.customer_name,
                        'date_deadline': deadline,
                        'user_id': activity.user_id.id,
                        'res_model_id': res_model_id,
                        'res_model': activity.res_model,
                        'res_id': record.id,
                        'note': activity.note,
                        'summary': activity.summary,  
                        'is_copied_activity': True,
                    })
        self.update_existing_activities()

        return activities


    def write(self, vals):
        res = super().write(vals)

        if 'date_deadline' in vals:
            for activity in self:
                _logger.info("write activity to Record ID: %s", activity)
                if activity.res_model == 'employee.payment.collection.line':
                    if self._context.get('prevent_activity_recursion'):
                        continue
                    
                    current_record = self.env['employee.payment.collection.line'].browse(activity.res_id)
                    _logger.info("write activity to current_record ID: %s", current_record)
             
                    
                    related_records = self.env['employee.payment.collection.line'].search([
                            ('id', '!=', current_record.id),
                            # ('divition_id', '=', current_record.divition_id.id),
                            ('customer_name', '=', current_record.customer_name),
                            ('employee_id', '=', current_record.employee_id.id),
                            ('collection_id', '=', current_record.collection_id.id),
                        ]).ids
                    related_activities = self.env['mail.activity'].search([
                            ('res_model', '=', 'employee.payment.collection.line'),
                            ('res_id', 'in', related_records)
                        ])


                    _logger.info("write activity to related_activities ID: %s", related_activities)
                    for related_activity in related_activities:
                        _logger.info("Updating deadline of related activity %s", related_activity.id)
                        related_activity.with_context(prevent_activity_recursion=True).sudo().write({
                            'date_deadline': vals['date_deadline']
                        })

        return res



    



    # @api.model_create_multi
    # def create(self, vals_list):
    #     activities = super().create(vals_list)
    #     for active in activities:
    #         if active.res_model == 'employee.payment.collection.line':
    #             if self._context.get('prevent_activity_recursion'):
    #                 return activities
    #             res_model_id = self.env['ir.model']._get_id('employee.payment.collection.line')
              
    #             current_record = self.env['employee.payment.collection.line'].browse(activities.res_id)
    #             related_records = self.env['employee.payment.collection.line'].search([
    #                             ('id', '!=', current_record.id),
    #                             ('divition_id', '=', current_record.divition_id.id),
    #                             ('customer_id', '=', current_record.customer_id.id),
    #                             ('employee_id', '=', current_record.employee_id.id),
    #                             ('collection_id', '=', current_record.collection_id.id),
    #                         ])
    #             for record in related_records:
    #                 for activity in activities:
    #                     if activity.res_model == 'employee.payment.collection.line':
    #                         self.with_context(prevent_activity_recursion=True).sudo().create({
    #                                         'activity_type_id': activity.activity_type_id.id,
    #                                         'summary': activity.summary,
    #                                         'date_deadline': activity.date_deadline,
    #                                         'user_id': activity.user_id.id,
    #                                         'res_model_id': res_model_id,
    #                                         'res_model':activity.res_model,
    #                                         'res_id': record.id,
    #                                         'note': activity.note,
    #                                         'is_copied_activity':True,
    #                                     })
                                    
            
    #             return activities
        

    def _action_done(self, feedback=False, attachment_ids=None):
        
        for activity in self:
            expected_revenue = 0.0
            lead_id = False

            if activity.res_model == 'crm.lead' and activity.res_id:
                lead = self.env['crm.lead'].browse(activity.res_id)
                expected_revenue = lead.expected_revenue
                lead_id = lead.id

            self.env['crm.done.activitys'].create({
                'name': activity.activity_type_id.name,
                'lead_id': lead_id,
                'user_id': activity.user_id.id,
                'date_done': fields.Date.today(),
                'note': activity.summary,
                'expected_revenue': expected_revenue,
                'res_model': activity.res_model,
                'res_id': activity.res_id,
                'activity_id': activity.id,
            })

            if activity.res_model == 'employee.payment.collection.line':
                current_record = self.env['employee.payment.collection.line'].browse(activity.res_id)

                if current_record:
                    related_records = self.env['employee.payment.collection.line'].search([
                        ('id', '!=', current_record.id),
                        # ('divition_id', '=', current_record.divition_id.id),
                        ('customer_id', '=', current_record.customer_id.id),
                        ('employee_id', '=', current_record.employee_id.id),
                        ('collection_id', '=', current_record.collection_id.id),
                    ])

                    for related_record in related_records:
                        related_activities = self.env['mail.activity'].search([
                            ('res_model', '=', 'employee.payment.collection.line'),
                            ('res_id', '=', related_record.id),
                            ('activity_type_id', '=', activity.activity_type_id.id),
                            ('user_id', '=', activity.user_id.id),
                        ])

                        for related_activity in related_activities:
                            if related_activity:
                                related_activity.unlink()

        # ✅ Now call the real, original Odoo method
        return MailActivityOriginal._action_done(self, feedback=feedback, attachment_ids=attachment_ids)
         
     # def action_cancel(self):        
     #    print("this is my method cancel")        
     #    for activity in self:            
     #        if activity.active:                
     #            activity.unlink('cancel')    
                
     # def unlink(self, data=None):        
     #    if data is None:            
     #        for record in self:                
     #            # Create a copy of the activity in crm.done.activitys                
     #            self.env['crm.done.activitys'].create({
     #                          'name': record.activity_type_id.name,  
     #                          'lead_id': record.res_id,                  
     #                          'user_id': record.user_id.id,  
     #                          'date_done': fields.Date.today(),  
     #                           'note': record.summary,  
     #                            'expected_revenue': record.res_model == 'crm.lead' and record.res_id and self.env['crm.lead'].browse(record.res_id).expected_revenue or 0.0   
     #                              })       
     #    return super(MailActivity, self).unlink()
    


class CrmLead(models.Model):
    _inherit = 'crm.lead'


    def write(self, vals):
        lost_stage = self.env['crm.stage'].search([('name', '=', 'Lost')], limit=1)

        for lead in self:
            # If the lead is being deactivated (active=False) or moved to a lost stage
            if vals.get('active') is False or (vals.get('stage_id') and vals['stage_id'] == lost_stage.id):
                vals['stage_id'] = lost_stage.id  # Ensure it is set to 'Lost'

        return super(CrmLead, self).write(vals)



    @api.model
    def get_company_currency(self, comp_id=None):
        """Fetch the dynamic currency name/symbol for the current or selected company."""
        if comp_id:
            try:
                company = self.env['res.company'].browse(int(comp_id))
            except Exception:
                company = self.env.company
        else:
            company = self.env.company
        if company and company.currency_id:
            return company.currency_id.name or company.currency_id.symbol or ''
        return ''

    @api.model
    def get_product_list(self, divition=None):
        """Fetch products from product.template or product.product safely."""
        products = self.env['product.template']
        if divition:
            try:
                div_id = int(divition)
                if 'tag_ids' in self.env['product.template']._fields:
                    products = self.env['product.template'].sudo().search([('tag_ids', 'in', [div_id])])
                if not products and 'x_studio_division' in self.env['product.template']._fields:
                    products = self.env['product.template'].sudo().search([('x_studio_division', 'in', [div_id])])
            except Exception as e:
                _logger.warning("Error filtering products by division: %s", e)

        if not products:
            products = self.env['product.template'].sudo().search([])

        if not products:
            products = self.env['product.product'].sudo().search([])

        return [{'id': p.id, 'name': p.display_name or p.name} for p in products]

 
    def get_divition_list(self):
        """Fetch all company or divition from crm.tag."""
        divition = self.env['crm.tag'].search([])
        return divition.read(['id', 'name','color'])  
    
    
    def get_tagids_lead(self,domain):
        """Fetch all company or divition from crm.tag."""
        divition = self.env['crm.lead'].search([domain])
        return divition.read(['id'])  

    def get_team_list(self):
        """Fetch all teams from crm.team."""
        teams = self.env['crm.team'].search([])
        return teams.read(['id', 'name'])  

    
    # def get_team_lead_access(self, user_id=None):
    #     """Fetch all teams from crm.team."""
    #     domain=[]
    #     if user_id:
    #         domain.append(('user_id', '=', user_id))
            
    #     teams = self.env['crm.team'].search(domain)
    #     company_list = self.get_team_changes(team_id=teams.id.ids)
    #     team_members = self.env['crm.team.member'].search([('crm_team_id','in',teams.id.ids)])
    #     user_ids = [tm['user_id'][0] for tm in team_members.read(['user_id']) if tm['user_id']]
    #     if not user_ids:
    #         team_members= []  # No members found
    #     employees = self.env['res.users'].browse(user_ids)
    #     employee_list = [{'id': emp.id, 'name': emp.name} for emp in employees]
        
    #     return { teams : teams.read(['id', 'name']) ,
    #              company_list : teams.read(['id', 'name']) ,
    #              employee_list : employee_list
    #             }

    def get_team_lead_access(self, user_id=None):
        """Fetch all teams from crm.team assigned to the given user, 
        and return team list, associated company tags, and employees in the teams."""
        
        domain = []
        if user_id:
            domain.append(('user_id', '=', user_id))
        
        teams = self.env['crm.team'].search(domain)
        team_ids = teams.ids
    
        # Get associated companies (tags)
        company_list = self.get_team_lead_changes(team_id=team_ids)
    
        # Get team members
        team_members = self.env['crm.team.member'].search([('crm_team_id', 'in', team_ids)])
        user_ids = [tm['user_id'][0] for tm in team_members.read(['user_id']) if tm['user_id']]
        
        # Get employee (user) info
        employees = self.env['res.users'].browse(user_ids)
        employee_list = [{'id': emp.id, 'name': emp.name} for emp in employees]
    
        # Final output dictionary
        return {
            'team_list': teams.read(['id', 'name']),
            'company_list': company_list,
            'employee_list': employee_list
        }


    def get_team_lead_access_ids(self):
        """Return team IDs, associated company tag IDs, and employee user IDs for the current user."""
        
        user_id = self.env.uid
    
        domain = []
        if user_id:
            domain.append(('user_id', '=', user_id))
        
        teams = self.env['crm.team'].search(domain)
        team_ids = teams.ids
    
        # Get associated company tag IDs from all teams
        company_list = self.get_team_lead_changes(team_id=team_ids)
        company_ids = [comp['id'] for comp in company_list]
    
        # Get team member user IDs
        team_members = self.env['crm.team.member'].search([('crm_team_id', 'in', team_ids)])
        user_ids = [tm['user_id'][0] for tm in team_members.read(['user_id']) if tm['user_id']]
    
        # Get employee (user) IDs
        employees = self.env['res.users'].browse(user_ids)
        employee_ids = employees.ids
    
        return {
            'team_ids': team_ids,
            'company_ids': company_ids,
            'employee_ids': employee_ids
        }
          
    def get_company_changes(self,comp_id=None):
        print("this is my comp id",comp_id,type(comp_id))
        if comp_id:
            comp_id=int(comp_id)
            print("this is my company id",comp_id,type(comp_id))

        team_lists=[]
        team_members=[]
        if comp_id:
            team_list = self.env['crm.team'].search([('x_studio_division','in',[comp_id])])
    
            team_member=self.env['crm.team.member'].search([('crm_team_id','in',team_list.ids)])
        else:
            team_list = self.env['crm.team'].search([])
    
            team_member=self.env['crm.team.member'].search([])
            

        # ✅ Format data correctly
        # team_lists = [{'id': emp.id, 'name': emp.name} for emp in team_list]

        # team_members=[{'id':emp.user_id.id, 'name':emp.user_id.name} for emp in team_member]

        # Remove duplicates while preserving the last occurrence
        team_lists = list({emp.id: {'id': emp.id, 'name': emp.name} for emp in team_list}.values())
        
        team_members = list({emp.user_id.id: {'id': emp.user_id.id, 'name': emp.user_id.name} for emp in team_member}.values())

        

        return {
        'team_lists': team_lists,
        'team_members': team_members
    }
        


    # def get_company_employee(self,comp_id=None):
    #     print("this is my comp id",comp_id,type(comp_id))
    #     if comp_id:
    #         comp_id=int(comp_id)
    #         print("this is my company id",comp_id,type(comp_id))

    #     emp_list = self.env['hr.employee'].search([('category_ids','in',[comp_id])])
        
    #     _logger.error("Info for Get emloyee list for that compnay:",emp_list)

    #     if not emp_list:
    #         return []  # No members found


    #     # ✅ Format data correctly
    #     emp_lists = [{'id': emp.user_id.id, 'name': emp.user_id.name} for emp in emp_list]

    #     return emp_lists

    def get_team_lead_changes(self,team_id=None):
        comp_lists=[]
      
        if team_id:
            team_companies = self.env['crm.team'].search([('id','in',team_id)])
    
            team_company=[{'id':[comp.x_studio_division.ids]} for comp in team_companies]
            
            team_company=team_company[0]['id']
    
            comp_list=self.env['crm.tag'].search([('id','in',team_company[0])])
            
            comp_lists = [{'id': comp.id, 'name': comp.name} for comp in comp_list]

        else:
            
            comp_list=self.env['crm.tag'].search([])
            
            comp_lists = [{'id': comp.id, 'name': comp.name} for comp in comp_list]
            

        return comp_lists




    def get_team_changes(self,team_id=None):
        
        user=self.env.user
        is_admin = user.has_group('base.group_system')  # Admin check
        is_team_lead = user.has_group('crm_dashboard.dashboard_team_leader')
        if is_team_lead and not team_id:
            crm_team = self.env['crm.team'].search([('user_id', '=', user.id)], limit=1)
            if crm_team:
                team_id = crm_team.id

            
        comp_lists=[]
        if team_id:
            team_id=int(team_id)
            print("this is my team id",team_id,type(team_id))

        
        if team_id:
            team_companies = self.env['crm.team'].search([('id','in',[team_id])])
    
            team_company=[{'id':[comp.x_studio_division.ids]} for comp in team_companies]
            
            team_company=team_company[0]['id']
    
            comp_list=self.env['crm.tag'].search([('id','in',team_company[0])])
            
            comp_lists = [{'id': comp.id, 'name': comp.name} for comp in comp_list]

        else:

            
            comp_list=self.env['crm.tag'].search([])
            
            comp_lists = [{'id': comp.id, 'name': comp.name} for comp in comp_list]
            

        return comp_lists
        

        

    def get_employee_changes(self, emp_id=None):
        if emp_id:
            emp_id = int(emp_id)
            print("This is my emp id:", emp_id, type(emp_id))
        
        team_list = []
        comp_lists = []
        
        if emp_id:
            team_member = self.env['crm.team.member'].search([('user_id', 'in', [emp_id])])
            team_list = [{'id': team.crm_team_id.id, 'name': team.crm_team_id.name} for team in team_member]
            
            # Ensure we are working with Odoo records
            crm_team_ids = team_member.mapped('crm_team_id.id')
            crm_team = self.env['crm.team'].browse(crm_team_ids)
            
            comp_lists = [
                {'id': tag.id, 'name': tag.name} 
                for comp in crm_team if isinstance(comp, type(self.env['crm.team']))
                for tag in comp.x_studio_division
            ]
        else:
            team_records = self.env['crm.team'].search([])
            team_list = [{'id': team.id, 'name': team.name} for team in team_records]
            
            # Ensure we use actual Odoo records
            comp_lists = [
                {'id': tag.id, 'name': tag.name} 
                for comp in team_records if isinstance(comp, type(self.env['crm.team']))
                for tag in comp.x_studio_division
            ]
        
        return {
            'comp_lists': comp_lists,
            'team_list': team_list,
        }

        

    
    def get_employee_list(self):
        """Fetch all employees who are also users in the system."""
        query = """
            SELECT rs.id AS id, rp.name AS name
            FROM res_users rs
            JOIN res_partner rp ON rp.id = rs.partner_id
            JOIN hr_employee he ON he.user_id = rs.id
        """
        self.env.cr.execute(query)
        result = self.env.cr.dictfetchall()  # Returns a list of dictionaries
        
        return result 
    

    def get_employee_team(self,crm_team_id=None):
        """Fetch all employees from hr.employee."""
        print("this is my team id",crm_team_id,type(crm_team_id))
        if crm_team_id:
            crm_team_id=int(crm_team_id)
            print("this is my team id",crm_team_id,type(crm_team_id))

        team_members = self.env['crm.team.member'].search([('crm_team_id','=',crm_team_id)])
       
        user_ids = [tm['user_id'][0] for tm in team_members.read(['user_id']) if tm['user_id']]

        if not user_ids:
            return []  # No members found

        # ✅ Fetch employee names using user IDs
        employees = self.env['res.users'].browse(user_ids)

        # ✅ Format data correctly
        employee_list = [{'id': emp.id, 'name': emp.name} for emp in employees]

        return employee_list


    

    # def get_employee_order_booking_target_and_achieved(self, team_id=None, user_id=None, comp_id=None, product_id=None, job_id=None):
    #         user = self.env.user
    #         is_admin = user.has_group('base.group_system')
    #         is_team_lead = user.has_group('crm_dashboard.dashboard_team_leader')
        
    #         if is_team_lead and not user_id and not team_id:
    #             user_id = user.id
        
    #         if team_id:
    #             team_id = int(team_id)
    #         if user_id:
    #             user_id = int(user_id)
    #         if comp_id:
    #             comp_id = int(comp_id)
        
    #         today = fields.Date.today()
    #         start_date = today.replace(month=1, day=1)
    #         end_date = today.replace(month=12, day=31)
        
    #         achieved_domain_base = [
    #             ('stage_id.name', 'in', ['Won', 'Partial Order Released']),
    #             ('date_open', '>=', start_date),
    #             ('date_open', '<=', end_date)
    #         ]
        
    #         # Declare global variables for domain filters
    #         domain_main = []
    #         domain_others = []
    #         domain_comp_id=[]
        
    #         total_booking_achieved = 0
    #         total_booking_achieved_others = 0
        
    #         # Case: No filter
    #         if not team_id and not user_id and not comp_id:
    #             total_booking_achieved = sum(
    #                 self.env['crm.lead'].search(achieved_domain_base).mapped('expected_revenue')
    #             )
        
    #         # Case: User-specific logic
    #         if user_id :
    #             employee = self.env['hr.employee'].search([('user_id', '=', user_id)], limit=1)
    #             employee_comp_ids = employee.mapped('category_ids.id')
        
    #             if comp_id:
    #                 # When comp_id is explicitly passed: split values
    #                 domain_main = achieved_domain_base + [('tag_ids', '=', comp_id), ('user_id', '=', user_id)]
    #                 total_booking_achieved = sum(self.env['crm.lead'].search(domain_main).mapped('expected_revenue'))
    #                 domain_others=[]            
                   
    #             else:
    #                 domain_main = achieved_domain_base + [('tag_ids', 'in', employee_comp_ids), ('user_id', '=', user_id)]
    #                 domain_others = achieved_domain_base + [('tag_ids', 'not in', employee_comp_ids), ('user_id', '=', user_id)]
            
    #                 total_booking_achieved = sum(self.env['crm.lead'].search(domain_main).mapped('expected_revenue'))
        
    #         # Case: Only team_id (without user_id)
    #         if team_id and not user_id:
    #             team = self.env['crm.team'].browse(team_id)
    #             team_comp_ids = team.x_studio_division.ids
    #             domain_others=[]
    #             if comp_id:
    #                 domain_main = achieved_domain_base + [('tag_ids', '=', comp_id)]
    #                 domain_others = []
    #             else:
    #                 domain_main = achieved_domain_base + [('tag_ids', 'in', team_comp_ids)]
        
    #             domain_main.append(('team_id', '=', team_id))
    #             total_booking_achieved = sum(self.env['crm.lead'].search(domain_main).mapped('expected_revenue'))
        
    #             if domain_others:
    #                 domain_others.append(('team_id', '=', team_id))
    #                 total_booking_achieved_others = sum(self.env['crm.lead'].search(domain_others).mapped('expected_revenue'))

    #         if team_id and user_id:
    #             team = self.env['crm.team'].browse(team_id)
    #             team_comp_ids = team.x_studio_division.ids
                
    #             _logger.warning('This is team_comp_ids: %s', team_comp_ids)
    #             domain_comp_id=domain_comp_id+team_comp_ids
    #             if comp_id:
    #                 domain_main = achieved_domain_base + [('tag_ids', '=', comp_id)]
    #                 domain_main.append(('team_id', '=', team_id))
                   
    #                 domain_others = []
    #             else:
    #                 domain_main = achieved_domain_base + [('tag_ids', 'in', team_comp_ids)]
    #                 domain_others = achieved_domain_base + [('tag_ids', 'not in', team_comp_ids)]
    #                 domain_main.append(('user_id', '=', user_id))
    #                 domain_others.append(('user_id', '=', user_id))
                    
        
    #             domain_main.append(('team_id', '=', team_id))
    #             total_booking_achieved = sum(self.env['crm.lead'].search(domain_main).mapped('expected_revenue'))
        
    #             if domain_others:
    #                 domain_others.append(('team_id', '=', team_id))
    #                 total_booking_achieved_others = sum(self.env['crm.lead'].search(domain_others).mapped('expected_revenue'))
        
        
    #         # Case: Only comp_id (no user_id or team_id)
    #         if comp_id:
    #             domain_main = achieved_domain_base + [('tag_ids', '=', comp_id)]
    #             total_booking_achieved = sum(self.env['crm.lead'].search(domain_main).mapped('expected_revenue'))
        
         
        
                            
                
    #         # # Target domain
    #         target_data = []
    #         today = fields.Date.today()
    #         start_date = today.replace(month=1, day=1)
    #         end_date = today.replace(month=12, day=31)
            
    #         target_domain = [('year', '=', str(start_date.year))]
            
    #         if team_id:
    #             team_id = int(team_id)
    #             team = self.env['crm.team'].browse(team_id)
    #             team_comp_ids = team.x_studio_division.ids  # Many2many field, so get related comp_ids
    #             target_domain.append(('x_studio_many2one_field_2t5_1in3f9cue', 'in', team_comp_ids))
            
    #         if user_id:
    #             user_id = int(user_id)
    #             employee_list = self.env['hr.employee'].search([('user_id', '=', user_id)])
    #             employee_ids = employee_list.mapped('id')
    #             target_domain.append(('employee_id', 'in', employee_ids))
            
    #         if comp_id:
    #             comp_id = int(comp_id)
    #             target_domain.append(('x_studio_many2one_field_2t5_1in3f9cue', '=', comp_id))
            
    #         target_data = self.env['hr.employee.target'].search(target_domain)
    #         total_booking_target = sum(target_data.mapped('order_booking_target'))
    
    #         totals_booking_achieveds_others = total_booking_achieved + total_booking_achieved_others
    #         percentage_achieved = round((totals_booking_achieveds_others / total_booking_target * 100), 2) if total_booking_target else 0
        

    #         return {
    #             'total_target': round(total_booking_target / 1_000_000, 2) if total_booking_target else 0,
    #             'total_achieved': round(total_booking_achieved / 1_000_000, 2) if total_booking_achieved else 0,
    #             'total_achieved_others': round(total_booking_achieved_others / 1_000_000, 2) if total_booking_achieved_others else 0,
    #             'percentage':percentage_achieved,
    #              'achieved_domain_base':achieved_domain_base,
    #             'domain_main':domain_main,
    #             'domain_others':domain_others,
    #             'domain_comp_id':domain_comp_id
          
    #         }


    def get_employee_order_booking_target_and_achieved(self, team_id=None, user_id=None, comp_id=None, product_id=None, job_id=None, month_name=None, selected_year=None):
            user = self.env.user
            is_admin = user.has_group('base.group_system')
            is_team_lead = user.has_group('crm_dashboard.dashboard_team_leader')
        
            if is_team_lead and not user_id and not team_id:
                user_id = user.id
        
            if team_id:
                team_id = int(team_id)
            if user_id:
                user_id = int(user_id)
            if comp_id:
                comp_id = int(comp_id)
                
            today = fields.Date.today()
            target_year = int(selected_year) if selected_year and str(selected_year).isdigit() and int(selected_year) > 0 else today.year
        
            if not month_name:
                start_date = date(target_year, 1, 1)
                end_date = date(target_year, 12, 31)
            else:
                month = int(month_name)
                start_date = date(target_year, month, 1)
                last_day = calendar.monthrange(target_year, month)[1]
                end_date = date(target_year, month, last_day)
        
            achieved_domain_base = [
                ('stage_id.name', 'in', ['Won', 'Partial Order Released']),
                ('date_open', '>=', start_date),
                ('date_open', '<=', end_date)
            ]
        
        
            # Declare global variables for domain filters
            domain_main = []
            domain_others = []
            domain_comp_id=[]

           
            total_booking_achieved = 0
            total_booking_achieved_others = 0
        
            # Case: No filter
            if not team_id and not user_id and not comp_id:
                domain_main=achieved_domain_base
                total_booking_achieved = sum(
                    self.env['crm.lead'].search(achieved_domain_base).mapped('expected_revenue')
                )
                
        
            # Case: User-specific logic
            if user_id and not team_id:
                teams = self.env['crm.team.member'].search([('user_id', '=', user_id)])

                # Collect all related company tag IDs from all teams
                team_comp_ids = set()
                for team_member in teams:
                    crm_team = team_member.crm_team_id
                    if crm_team and crm_team.x_studio_division:
                        team_comp_ids.update(crm_team.x_studio_division.ids)
            
                team_comp_ids = list(team_comp_ids)  # Convert to list if needed later
                # employee = self.env['hr.employee'].search([('user_id', '=', user_id)], limit=1)
                # employee_comp_ids = employee.mapped('category_ids.id')
                # _logger.error('This is employee_comp_ids: %s', team_comp_ids)
        
                if comp_id:
                    # When comp_id is explicitly passed: split values
                    domain_main = achieved_domain_base + [('tag_ids', '=', comp_id), ('user_id', '=', user_id)]
                    total_booking_achieved = sum(self.env['crm.lead'].search(domain_main).mapped('expected_revenue'))
                    domain_others=[]            
                   
                else:
                    domain_main = achieved_domain_base + [('tag_ids', 'in', team_comp_ids), ('user_id', '=', user_id)]
                    domain_others = achieved_domain_base + [('tag_ids', 'not in', team_comp_ids), ('user_id', '=', user_id)]
            
                    total_booking_achieved = sum(self.env['crm.lead'].search(domain_main).mapped('expected_revenue'))
        
            # Case: Only team_id (without user_id)
            if team_id and not user_id:
                team = self.env['crm.team'].browse(team_id)
                team_comp_ids = team.x_studio_division.ids
                domain_others=[]
                if comp_id:
                    domain_main = achieved_domain_base + [('tag_ids', '=', comp_id)]
                    domain_others = []
                else:
                    domain_main = achieved_domain_base + [('tag_ids', 'in', team_comp_ids)]
        
                domain_main.append(('team_id', '=', team_id))
                total_booking_achieved = sum(self.env['crm.lead'].search(domain_main).mapped('expected_revenue'))
        
                if domain_others:
                    domain_others.append(('team_id', '=', team_id))
                    total_booking_achieved_others = sum(self.env['crm.lead'].search(domain_others).mapped('expected_revenue'))

            if team_id and user_id:
                team = self.env['crm.team'].browse(team_id)
                team_comp_ids = team.x_studio_division.ids
                
                _logger.warning('This is team_comp_ids: %s', team_comp_ids)
                domain_comp_id=domain_comp_id+team_comp_ids
                if comp_id:
                    domain_main = achieved_domain_base + [('tag_ids', '=', comp_id)]
                    domain_main.append(('team_id', '=', team_id))
                   
                    domain_others = []
                else:
                    domain_main = achieved_domain_base + [('tag_ids', 'in', team_comp_ids)]
                    domain_others = achieved_domain_base + [('tag_ids', 'not in', team_comp_ids)]
                    domain_main.append(('user_id', '=', user_id))
                    domain_others.append(('user_id', '=', user_id))
                    
        
                domain_main.append(('team_id', '=', team_id))
                total_booking_achieved = sum(self.env['crm.lead'].search(domain_main).mapped('expected_revenue'))
        
                if domain_others:
                    domain_others.append(('team_id', '=', team_id))
                    total_booking_achieved_others = sum(self.env['crm.lead'].search(domain_others).mapped('expected_revenue'))
        
        
            # Case: Only comp_id (no user_id or team_id)
            if comp_id and not team_id and not user_id:
                domain_main = achieved_domain_base + [('tag_ids', '=', comp_id)]
                total_booking_achieved = sum(self.env['crm.lead'].search(domain_main).mapped('expected_revenue'))
        
         
        
                            
                
            # # Target domain
            target_data = []
            start_date=''
            end_date=''
        
            if not month_name:
                today = fields.Date.today()
                start_date = today.replace(month=1, day=1)
                end_date = today.replace(month=12, day=31)
            else:
                year = datetime.today().year
                month = int(month_name)
            
                start_date = datetime(year, month, 1).date()
                # Get last day of the month
                last_day = calendar.monthrange(year, month)[1]
                end_date = datetime(year, month, last_day).date()
            
            target_domain = [('year', '=', str(start_date.year))]
            
            if team_id:
                team_id = int(team_id)
                team = self.env['crm.team'].browse(team_id)
                team_comp_ids = team.x_studio_division.ids  # Many2many field, so get related comp_ids
                # target_domain.append(('x_studio_many2one_field_2t5_1in3f9cue', 'in', team_comp_ids))
            
            if user_id:
                user_id = int(user_id)
                employee_list = self.env['hr.employee'].search([('user_id', '=', user_id)])
                employee_ids = employee_list.mapped('id')
                target_domain.append(('employee_id', 'in', employee_ids))
            
            if comp_id:
                comp_id = int(comp_id)
                # target_domain.append(('x_studio_many2one_field_2t5_1in3f9cue', '=', comp_id))
            
            target_data = self.env['hr.employee.target'].search(target_domain)
        
            if month_name:
                total_booking_target = sum(target_data.mapped('order_booking_target'))/12
            else:
                 total_booking_target = sum(target_data.mapped('order_booking_target'))
    
            totals_booking_achieveds_others = total_booking_achieved + total_booking_achieved_others
            percentage_achieved = round((totals_booking_achieveds_others / total_booking_target * 100), 2) if total_booking_target else 0
        

            return {
                'total_target': round(total_booking_target, 2) if total_booking_target else 0,
                'total_achieved': round(total_booking_achieved, 2) if total_booking_achieved else 0,
                'total_achieved_others': round(total_booking_achieved_others, 2) if total_booking_achieved_others else 0,
                'percentage':percentage_achieved,
                 'achieved_domain_base':achieved_domain_base,
                'domain_main':domain_main,
                'domain_others':domain_others,
                'domain_comp_id':domain_comp_id
          
            }
    


    



    
        
        
              

    def get_employee_invoice_target_and_achieved(self, comp_id=None, team_id=None, user_id=None, product_id=None, job_id=None, month_name=None, selected_year=None):
        user=self.env.user
        is_admin = user.has_group('base.group_system')  # Admin check
        is_team_lead = user.has_group('crm_dashboard.dashboard_team_leader')

        if is_team_lead and not user_id and not team_id:
            user_id =user.id
            
        today = fields.Date.today()
        target_year = int(selected_year) if selected_year and str(selected_year).isdigit() and int(selected_year) > 0 else today.year

        target_domain=[]
        if comp_id:
            target_domain.append(('tag_id', '=', int(comp_id)))

        if month_name:
             revenue_rec = self.env['monthly.crm.revenue'].search([('name', '=', month_name), ('year', '=', str(target_year))], limit=1)
             if not revenue_rec:
                 revenue_rec = self.env['monthly.crm.revenue'].search([('name', '=', month_name)], limit=1)
             if revenue_rec:
                 target_domain.append(('revenue_id', '=', revenue_rec.id))
             else:
                 target_domain.append(('revenue_id', '=', 0))
        else:
             revenue_recs = self.env['monthly.crm.revenue'].search([('year', '=', str(target_year))])
             if revenue_recs:
                 target_domain.append(('revenue_id', 'in', revenue_recs.ids))
            
        if team_id:
                if not comp_id:
                         
                    team_companies = self.env['crm.team'].search([('id','in',[int(team_id)])])
                    category_ids=team_companies.x_studio_division.ids
                    if category_ids:
                        target_domain.append(('tag_id', 'in', category_ids))
        if user_id:
           
            if not team_id or  not comp_id:
                
                 team_member = self.env['crm.team.member'].search([('user_id', '=', int(user_id))])
                 team= self.env['crm.team'].search([('id','in',team_member.crm_team_id.ids)])
                 category_ids=team.x_studio_division.ids
                 if category_ids:
                     target_domain.append(('tag_id', 'in', category_ids))
            
             
             
            
                    

        
        
        # Use target_domain in search to filter results
        target_data = self.env['monthly.crm.revenue.line'].search(target_domain)
    
        total_invoice_target = sum(target_data.mapped('revenue_target'))
        total_invoice_achieved = sum(target_data.mapped('revenue_achieved'))

    
        percentage_achieved = round((total_invoice_achieved / total_invoice_target * 100), 2) if total_invoice_target else 0

        return {
            'total_target': round(total_invoice_target, 2) if total_invoice_target else 0,
            'total_achieved': round(total_invoice_achieved, 2) if total_invoice_achieved else 0,
            'percentage': percentage_achieved,       
             'target_domain':target_domain
        }


    

    def get_quote_submitted(self, comp_id=None, team_id=None, user_id=None, product_id=None, job_id=None, filter_by='month', selected_year=None):
        """Retrieve total expected revenue and lead count in the 'Quote Submitted' stage."""
        user = self.env.user
        is_admin = user.has_group('base.group_system')
        is_team_lead = user.has_group('crm_dashboard.dashboard_team_leader')
        
        stages = [
            'Quote Submitted',
            'Expecting (60%)',
            'Commit (90%)',
            'Partial Order Released'
        ]
        
        stage_ids = self.env['crm.stage'].search([('name', 'in', stages)])
        stage_list = [stage['id'] for stage in stage_ids.read(['id'])]  
        
        if not stage_ids:
            return {'error': 'Stage list not found.'}
    
        domain = [('stage_id', 'in', stage_list)]
    
        if comp_id:
            domain.append(('tag_ids', '=', int(comp_id)))

        if job_id:
            domain.append(('job_type', '=', job_id))
        if product_id:
            domain.append(('product_ids','=',int(product_id)))
        if is_admin:
            if team_id:
                domain.append(('team_id', '=', int(team_id)))
            if user_id:
                domain.append(('user_id', '=', int(user_id)))
        elif is_team_lead and not is_admin:
             if team_id:
                domain.append(('team_id', '=', int(team_id)))
             if user_id:
                domain.append(('user_id', '=', int(user_id)))
        else:
            domain.append(('user_id', '=', user.id))
    
        today = fields.Date.today()
        target_year = int(selected_year) if selected_year and str(selected_year).isdigit() and int(selected_year) > 0 else today.year
        
        if filter_by == 'month':
            start_date = date(target_year, today.month, 1)
            last_day = calendar.monthrange(target_year, today.month)[1]
            end_date = date(target_year, today.month, last_day)
        else:
            start_date = date(target_year, 1, 1)
            end_date = date(target_year, 12, 31)
        
        domain.extend([
            '|',
            '&', ('date_open', '>=', start_date), ('date_open', '<=', end_date),
            '&', ('create_date', '>=', start_date), ('create_date', '<=', end_date)
        ])
    
        # Search leads
        leads_in_stage = self.env['crm.lead'].search(domain)
        
        # Calculate total expected revenue & lead count
        total_expected_revenue = sum(leads_in_stage.mapped('expected_revenue') or [0])
        total_expected_revenue = round(total_expected_revenue, 2)
        lead_count = len(leads_in_stage)
        
        leads_in_stage1 = self.env['crm.lead'].search(domain).mapped('name') 
        return {
            'total_expected_revenue': total_expected_revenue or 0,
            'lead_count': lead_count or 0,
            'filter': filter_by,
            'domain':domain,
            'leads_in_stage':leads_in_stage1,
            'user':user
        }
    
    


    def get_probability_values(self, comp_id=None, team_id=None, user_id=None, product_id=None, job_id=None, filter_by='month', selected_year=None):
        """Retrieve total expected revenue and lead count for different probability stages."""
        domain=[]

        if comp_id:
            domain.append(['tag_ids','=',int(comp_id)])
        if job_id:
            domain.append(('job_type', '=', job_id))
        if product_id:
            domain.append(('product_ids','=',int(product_id)))
        if team_id:
            domain.append(('team_id', '=', int(team_id)))
        if user_id:
            domain.append(('user_id', '=', int(user_id)))

        user = self.env.user
        is_admin = user.has_group('base.group_system')
        is_team_lead = user.has_group('crm_dashboard.dashboard_team_leader')

        if not user_id and not team_id:
            if is_team_lead:
                employee = self.env['hr.employee'].search([('user_id', '=', user.id)], limit=1)
                if employee:
                    domain.append(('user_id', '=', user.id))

        stages = [
            'Quote Submitted',
            'Expecting (60%)',
            'Commit (90%)',
            'Partial Order Released',
            'Won',
            'Hold'    
        ]

        today = fields.Date.today()
        target_year = int(selected_year) if selected_year and str(selected_year).isdigit() and int(selected_year) > 0 else today.year

        if filter_by == 'month':
            start_date = date(target_year, today.month, 1)
            last_day = calendar.monthrange(target_year, today.month)[1]
            end_date = date(target_year, today.month, last_day)
        else:
            start_date = date(target_year, 1, 1)
            end_date = date(target_year, 12, 31)

        # Filter by the current year
        domain += [('date_open', '>=', start_date), ('date_open', '<=', end_date)]
        print("this is probability domain",domain)


        if not is_admin and not is_team_lead:
            
            # If not admin, return leads assigned to the logged-in user
            employee = self.env['hr.employee'].search([('user_id', '=', user.id)], limit=1)
            if employee:
                domain.append(('user_id', '=', user.id))  # Filter leads assigned to the logged-in user
            else:
                return {'error': 'Employee record not found for this user.'}
      

        # Initialize result dictionary
        result = []

        # Iterate over stages and calculate totals
        for stage_name in stages:
            if stage_name:
                     if stage_name == 'Lost':
                         domain.append(('active', 'in', [True,False])); 
                     lead= self.env['crm.lead'].search(domain + [('stage_id.name', '=', stage_name)])
                     print("this is my big lead of probalbility",lead.stage_id.name)
                
                     expected_revenue = int(sum(lead.mapped('expected_revenue')))
                     expected_revenue = "{:,}".format(expected_revenue)
                     count_lead=len(lead)

                     if stage_name == 'Quote Submitted':
                         result.append(
                            { 'quote_submitted':{
                                 'expected_revenue':expected_revenue or 0,
                                 'count':count_lead or 0
                             }
                             }
                         )

                     if stage_name == 'Expecting (60%)':
                         result.append(
                            { 'below_50':{
                                 'expected_revenue':expected_revenue or 0,
                                 'count':count_lead or 0
                             }
                             }
                         )

                     if stage_name == 'Commit (90%)':
                         result.append(
                            { 'above_50':{
                                 'expected_revenue':expected_revenue or 0,
                                 'count':count_lead or 0
                             }
                             }
                         )


                  
                     if stage_name == 'Partial Order Released':
                         result.append(
                            { 'partial_order':{
                                 'expected_revenue':expected_revenue or 0,
                                 'count':count_lead or 0
                             }
                             }
                         )

                     if stage_name == 'Hold':
                             result.append(
                                { 'tender':{
                                     'expected_revenue':expected_revenue or 0,
                                     'count':count_lead or 0
                                 }
                                 }
                             )


                     if stage_name == 'Won':
                         result.append(
                            { 'won':{
                                 'expected_revenue':expected_revenue or 0,
                                 'count':count_lead or 0
                             }
                             }
                         )
                     if stage_name == 'Lost':
                         result.append(
                            { 'lose':{
                                 'expected_revenue':expected_revenue or 0,
                                 'count':count_lead or 0
                             }
                             }
                         )

                     result.append({'domain':domain})

        return result
    

    @api.model
    def get_activity(self, comp_id=None, team_id=None, user_id=None,product_id=None,job_id=None):
        """Returns planned and done activity counts for today and this month.
        
        - Admin: Gets all users' data but allows filtering.
        - Non-Admin: Can see only their own data without filters.
        """

        domain = []
        user = self.env.user
        is_admin = user.has_group('base.group_system')
        is_team_lead = user.has_group('crm_dashboard.dashboard_team_leader')
        

        # Apply filters only if the user is an admin
        # if comp_id:
        #         domain.append(('tag_ids', '=', int(comp_id)))
        # if job_id:
        #     domain.append(('job_type', '=', job_id))
        # if product_id:
        #     domain.append(('product_ids','=',int(product_id)))
     
        # Get leads based on the domain
        # leads = self.env['crm.lead'].search(domain)
        # lead_list = leads.ids if leads else []

        today = fields.Date.today()
        first_day_of_month = today.replace(day=1)
        last_day_of_month = today.replace(day=calendar.monthrange(today.year, today.month)[1])
        
        # Define base domains for activities
        domain_planning_today = [('date_deadline', '=', today)]
        domain_done_today = [('date_done', '=', today)]
        
        domain_planning_month = [('date_deadline', '>=', first_day_of_month), ('date_deadline', '<=', last_day_of_month)]
        domain_done_month = [('date_done', '>=', first_day_of_month), ('date_done', '<=', last_day_of_month)]



        if is_admin:
          
             if team_id and not user_id:
                        team_id = int(team_id)
                        team_members = self.env['crm.team.member'].search([('crm_team_id', '=', team_id)])
                        member_ids = team_members.mapped('user_id.id')
                        domain_planning_today.append(('user_id', 'in', member_ids))
                        domain_planning_month.append(('user_id', 'in', member_ids))
                        domain_done_today.append(('user_id', 'in', member_ids))
                        domain_done_month.append(('user_id', 'in', member_ids))
            
             if user_id:
                        domain_planning_today.append(('user_id', '=',  int(user_id)))
                        domain_planning_month.append(('user_id', '=',  int(user_id)))
                        domain_done_today.append(('user_id', '=',  int(user_id)))
                        domain_done_month.append(('user_id', '=',  int(user_id)))

        
        elif is_team_lead  and not is_admin:
            
             if team_id and not user_id:
                        team_id = int(team_id)
                        team_members = self.env['crm.team.member'].search([('crm_team_id', '=', team_id)])
                        member_ids = team_members.mapped('user_id.id')
                        domain_planning_today.append(('user_id', 'in', member_ids))
                        domain_planning_month.append(('user_id', 'in', member_ids))
                        domain_done_today.append(('user_id', 'in', member_ids))
                        domain_done_month.append(('user_id', 'in', member_ids))
             if user_id:
                        domain_planning_today.append(('user_id', '=',  int(user_id)))
                        domain_planning_month.append(('user_id', '=',  int(user_id)))
                        domain_done_today.append(('user_id', '=',  int(user_id)))
                        domain_done_month.append(('user_id', '=',  int(user_id)))
             if not team_id and not user_id:
                        domain_planning_today.append(('user_id', '=',  user.id))
                        domain_planning_month.append(('user_id', '=',  user.id))
                        domain_done_today.append(('user_id', '=',  user.id))
                        domain_done_month.append(('user_id', '=', user.id))
                 
        else:
            # Non-admin users can see only their own data
            domain_planning_today.append(('user_id', '=',  user.id))
            domain_planning_month.append(('user_id', '=',  user.id))
            domain_done_today.append(('user_id', '=',  user.id))
            domain_done_month.append(('user_id', '=', user.id))

        # if user_id:
        #     domain_planning_today.append(('user_id', '=', int(user_id)))
        #     domain_done_today.append(('user_id', '=', int(user_id)))
        #     domain_planning_month.append(('user_id', '=', int(user_id)))
        #     domain_done_month.append(('user_id', '=', int(user_id)))
        
        # if not is_admin and not is_team_lead :
        #     domain_planning_today.append(('user_id', '=', user.id))
        #     domain_done_today.append(('user_id', '=', user.id))
        #     domain_planning_month.append(('user_id', '=', user.id))
        #     domain_done_month.append(('user_id', '=', user.id))
        # if not is_admin and is_team_lead and :
        #     domain_planning_today.append(('user_id', '=', user.id))
        #     domain_done_today.append(('user_id', '=', user.id))
        #     domain_planning_month.append(('user_id', '=', user.id))
        #     domain_done_month.append(('user_id', '=', user.id))
            
            
     
        # else:
        #     domain_planning_today.append(('res_id', '=', 0))
        #     domain_done_today.append(('lead_id', '=', 0))
        #     domain_planning_month.append(('res_id', '=', 0))
        #     domain_done_month.append(('lead_id', '=', 0))

        # Initialize variables
        planning_today = planning_month = done_today = done_month = 0
        
        plan_month_domain=[]
        plan_day_domain=[]
        done_month_domain=[]
        done_day_domain=[]

        # Fetch counts with error handling
        try:
            planning_today = self.env['mail.activity'].search(domain_planning_today)
            related_record=[]
            if comp_id:
                tag = self.env['crm.tag'].browse(int(comp_id))
                if tag.exists():
                    
                    for planning in planning_today:
                        if planning.res_model in ['crm.lead', 'employee.payment.collection.line']:
                            if planning.res_model and planning.res_id:
                                if planning.res_model == 'crm.lead':
                                    lead = self.env['crm.lead'].search([
                                        ('id', '=', planning.res_id),
                                        ('tag_ids', '=', int(comp_id))
                                    ])
                                    if lead:
                                        related_record.append(lead)
                                        plan_day_domain.append(planning.id)
                                
                                elif planning.res_model == 'employee.payment.collection.line' and tag:
                                    record = self.env['employee.payment.collection.line'].search([
                                        ('id', '=', planning.res_id),
                                        ('division', '=', tag.name)
                                    ])
                                    if record:
                                        plan_day_domain.append(planning.id)
                                        related_record.append(record)
            if related_record:  
                
                planning_today = len(related_record)
            else:
                plan_day_domain=planning_today.ids
                planning_today= len(planning_today)
                
            
        except Exception as e:
            _logger.error("Error fetching planning_today: %s", str(e))
            planning_today = '###'  # Set default to 1 in case of error

        try:
            planning_month = self.env['mail.activity'].search(domain_planning_month)
            related_record=[]
            if comp_id:
                tag = self.env['crm.tag'].browse(int(comp_id))
                if tag.exists():

                    for planning in planning_month:
                        if planning.res_model in ['crm.lead', 'employee.payment.collection.line']:
                            if planning.res_model and planning.res_id:
                                if planning.res_model == 'crm.lead':
                                    lead = self.env['crm.lead'].search([
                                        ('id', '=', planning.res_id),
                                        ('tag_ids', '=', int(comp_id))
                                    ])
                                    if lead:
                                        related_record.append(lead)
                                        plan_month_domain.append(planning.id)
                                
                                elif planning.res_model == 'employee.payment.collection.line' and tag:
                                    record = self.env['employee.payment.collection.line'].search([
                                        ('id', '=', planning.res_id),
                                        ('division', '=', tag.name)
                                    ])
                                    if record:
                                        plan_month_domain.append(planning.id)
                                        related_record.append(record)
            if related_record:
                planning_month = len(related_record)
            else:
                plan_month_domain = planning_month.ids
                planning_month=len(planning_month)
                
                
            
        except Exception as e:
            _logger.error("Error fetching planning_month: %s", str(e))
            planning_month = '###' 

        try:
            done_today = self.env['crm.done.activitys'].search(domain_done_today)
            related_record=[]
            if comp_id:
                tag = self.env['crm.tag'].browse(int(comp_id))
                if tag.exists():

                    for planning in done_today:
                        if planning.res_model in ['crm.lead', 'employee.payment.collection.line']:
                            if planning.res_model and planning.res_id:
                                if planning.res_model == 'crm.lead':
                                    lead = self.env['crm.lead'].search([
                                        ('id', '=', planning.res_id),
                                        ('tag_ids', '=', int(comp_id))
                                    ])
                                    if lead:
                                        related_record.append(lead)
                                        done_day_domain.append(planning.id)
                                
                                elif planning.res_model == 'employee.payment.collection.line' and tag:
                                    record = self.env['employee.payment.collection.line'].search([
                                        ('id', '=', planning.res_id),
                                        ('division', '=', tag.name)
                                    ])
                                    if record:
                                        done_day_domain.append(planning.id)
                                        related_record.append(record)
            if related_record:
                done_today = len(related_record)
            else:
                done_day_domain=done_today.ids
                done_today=len(done_today)
            
        except Exception as e:
            _logger.error("Error fetching done_today: %s", str(e))
            done_today = '###'

        try:
            done_month = self.env['crm.done.activitys'].search(domain_done_month)
            related_record=[]
            if comp_id:
                tag = self.env['crm.tag'].browse(int(comp_id))
                if tag.exists():
                    for planning in done_month:
                        if planning.res_model in ['crm.lead', 'employee.payment.collection.line']:
                            if planning.res_model and planning.res_id:
                                if planning.res_model == 'crm.lead':
                                    lead = self.env['crm.lead'].search([
                                        ('id', '=', planning.res_id),
                                        ('tag_ids', '=', int(comp_id))
                                    ])
                                    if lead:
                                        related_record.append(lead)
                                        done_month_domain.append(planning.id)
                                
                                elif planning.res_model == 'employee.payment.collection.line' and tag:
                                    record = self.env['employee.payment.collection.line'].search([
                                        ('id', '=', planning.res_id),
                                        ('division', '=', tag.name)
                                    ])
                                    if record:
                                        done_month_domain.append(planning.id)
                                        related_record.append(record)
            if related_record:  
                done_month = len(related_record)
            else:
                done_month_domain=done_month.ids
                done_month = len(done_month)
            

        except Exception as e:
            _logger.error("Error fetching done_month: %s", str(e))
            done_month = '###'  

        return {
            'planning_today': planning_today or 0,
            'planning_month': planning_month or 0,
            'done_today': done_today or 0,
            'done_month': done_month or 0,
            'domain':{
                'planning_today':plan_day_domain,
                'planning_month':plan_month_domain,
                'done_today':done_day_domain,
                'done_month':done_month_domain
            }
        }



    def get_quote_submitted_graph_company(self, comp_id=None, team_id=None, user_id=None, job_id=None, filter_by='month', selected_year=None):
        domain = []
        onclick_domain = []
    
        if comp_id:
            domain.append(f"tag.id = {int(comp_id)}")
            onclick_domain.append(('tag_ids', '=', int(comp_id)))
        if team_id:
            domain.append(f"crm.team_id = {int(team_id)}")
            onclick_domain.append(('team_id', '=', int(team_id)))
        if user_id:
            domain.append(f"crm.user_id = {int(user_id)}")
            onclick_domain.append(('user_id', '=', int(user_id)))
        if job_id:
            domain.append(f'crm."job_type" = \'{job_id}\'')
            onclick_domain.append(('job_type', '=', job_id))
    
        user = self.env.user
        is_admin = user.has_group('base.group_system')
        is_team_lead = user.has_group('crm_dashboard.dashboard_team_leader')
    
        stages = ['Quote Submitted', 'Expecting (60%)', 'Commit (90%)', 'Won', 'Partial Order Released']
        quote_submitted_stage = self.env['crm.stage'].search([('name', 'in', stages)])
        if not quote_submitted_stage:
            return {'error': 'Stage list not found.'}
        stage_list = [stage.id for stage in quote_submitted_stage]
        domain.append(f"crm.stage_id IN {tuple(stage_list) if len(stage_list) > 1 else f'({stage_list[0]})'}")
        onclick_domain.append(('stage_id', 'in', stage_list))
    
        today = fields.Date.today()
        target_year = int(selected_year) if selected_year and str(selected_year).isdigit() and int(selected_year) > 0 else today.year
        if filter_by == 'month':
            start_date = date(target_year, today.month, 1)
            last_day = calendar.monthrange(target_year, today.month)[1]
            end_date = date(target_year, today.month, last_day)
        else:
            start_date = date(target_year, 1, 1)
            end_date = date(target_year, 12, 31)
        domain.append(f"crm.date_open >= '{start_date}'")
        domain.append(f"crm.date_open <= '{end_date}'")
        onclick_domain.append(('date_open', '>=', start_date))
        onclick_domain.append(('date_open', '<=', end_date))
    
        if not is_admin and not is_team_lead:
            employee = self.env['hr.employee'].search([('user_id', '=', user.id)], limit=1)
            if employee:
                domain.append(f"crm.user_id = {user.id}")
                onclick_domain.append(('user_id', '=', user.id))
            else:
                return {'error': 'Employee record not found for this user.'}
    
        if not is_admin and is_team_lead and not team_id and not user_id:
            employee = self.env['hr.employee'].search([('user_id', '=', user.id)], limit=1)
            if employee:
                domain.append(f"crm.user_id = {user.id}")
                onclick_domain.append(('user_id', '=', user.id))
            else:
                return {'error': 'Employee record not found for this user.'}
    
        where_clause = f"WHERE {' AND '.join(domain)}" if domain else ""
    
        # 🔀 Conditional grouping based on comp_id
        if comp_id:
            # Group by salesperson
            query = f"""
                SELECT 
                    crm.user_id AS user_id,
                    rp.name AS user_name,
                    SUM(crm.expected_revenue) AS revenue,
                    COUNT(crm.id) AS total_leads
                FROM crm_lead AS crm
                LEFT JOIN res_users AS ru ON ru.id = crm.user_id
                LEFT JOIN res_partner AS rp ON rp.id = ru.partner_id
                LEFT JOIN crm_tag_rel AS tag_rel ON tag_rel.lead_id = crm.id
                LEFT JOIN crm_tag AS tag ON tag.id = tag_rel.tag_id
                {where_clause}
                GROUP BY crm.user_id, rp.name
                ORDER BY revenue DESC;
            """
        else:
            # Group by tag
            query = f"""
                SELECT 
                    tag.id AS tag_id,
                    tag.name AS tag_name,
                    SUM(crm.expected_revenue) AS revenue,
                    COUNT(crm.id) AS total_leads
                FROM crm_lead AS crm
                LEFT JOIN crm_tag_rel AS tag_rel ON tag_rel.lead_id = crm.id
                LEFT JOIN crm_tag AS tag ON tag.id = tag_rel.tag_id
                {where_clause}
                GROUP BY tag.id, tag.name
                ORDER BY revenue DESC;
            """
    
        self.env.cr.execute(query)
        results = self.env.cr.dictfetchall()
    
        if comp_id:
            formatted_result = {
                "tag_id": [res["user_id"] for res in results],
                "tag_name": [res["user_name"] or "No Salesperson" for res in results],
                "revenue": [res["revenue"] for res in results],
                "total_leads": [res["total_leads"] for res in results],
                "domain1": query,
                "domain": onclick_domain
            }
        else:
            formatted_result = {
                "tag_id": [res["tag_id"] for res in results],
                "tag_name": [res["tag_name"].get("en_US") if isinstance(res["tag_name"], dict) else res["tag_name"] or "No Tag" for res in results],
                "revenue": [res["revenue"] for res in results],
                "total_leads": [res["total_leads"] for res in results],
                "domain1": query,
                "domain": onclick_domain
            }
    
        return formatted_result





    def get_won_stage_graph_company(self, comp_id=None, team_id=None, user_id=None, job_id=None, filter_by='month', selected_year=None):
        domain = []
        onclick_domain = []
    
        if comp_id:
            domain.append(f"tag.id = {int(comp_id)}")  # still needed to filter tag
            onclick_domain.append(('tag_ids', '=', int(comp_id)))
        if team_id:
            domain.append(f"crm.team_id = {int(team_id)}")
            onclick_domain.append(('team_id', '=', int(team_id)))
        if user_id:
            domain.append(f"crm.user_id = {int(user_id)}")
            onclick_domain.append(('user_id', '=', int(user_id)))
        if job_id:
            domain.append(f"crm.\"job_type\" = '{job_id}'")
            onclick_domain.append(('job_type', '=', job_id))
    
        user = self.env.user
        is_admin = user.has_group('base.group_system')
        is_team_lead = user.has_group('crm_dashboard.dashboard_team_leader')
    
        stages = self.env['crm.stage'].search([
            '|',
            ('name', 'ilike', 'Won'),
            ('name', 'ilike', 'Partial Order Released')
        ])
        stage_list = [stage.id for stage in stages]
        stage_ids_str = ', '.join(str(sid) for sid in stage_list)
    
        today = fields.Date.today()
        target_year = int(selected_year) if selected_year and str(selected_year).isdigit() and int(selected_year) > 0 else today.year
        if filter_by == 'month':
            start_date = date(target_year, today.month, 1)
            last_day = calendar.monthrange(target_year, today.month)[1]
            end_date = date(target_year, today.month, last_day)
        else:
            start_date = date(target_year, 1, 1)
            end_date = date(target_year, 12, 31)
    
        domain += [
            f"crm.stage_id in ({stage_ids_str})",
            f"COALESCE(crm.date_open, crm.create_date) >= '{start_date}'",
            f"COALESCE(crm.date_open, crm.create_date) <= '{end_date}'"
        ]
        onclick_domain += [
            ('date_open', '>=', start_date),
            ('date_open', '<=', end_date),
            ('stage_id', 'in', stage_list)
        ]
    
        if not is_admin and not is_team_lead:
            domain.append(f"crm.user_id = {user.id}")
            onclick_domain.append(('user_id', '=', user.id))
        if not is_admin and is_team_lead and not team_id and not user_id:
            domain.append(f"crm.user_id = {user.id}")
            onclick_domain.append(('user_id', '=', user.id))
    
        where_clause = f"WHERE {' AND '.join(domain)}" if domain else ""
    
        if comp_id:
            # Group by Salesperson
           query = f"""
                SELECT 
                    crm.user_id AS user_id,
                    rp.name AS user_name,
                    SUM(crm.expected_revenue) AS revenue,
                    COUNT(crm.id) AS total_leads
                FROM crm_lead AS crm
                LEFT JOIN res_users AS ru ON ru.id = crm.user_id
                LEFT JOIN res_partner AS rp ON rp.id = ru.partner_id
                LEFT JOIN crm_tag_rel AS tag_rel ON tag_rel.lead_id = crm.id
                LEFT JOIN crm_tag AS tag ON tag.id = tag_rel.tag_id
                {where_clause}
                GROUP BY crm.user_id, rp.name
                ORDER BY revenue DESC;
            """

        else:
            # Group by Tag
            query = f"""
                SELECT 
                    tag.id AS tag_id,
                    tag.name AS tag_name,
                    SUM(crm.expected_revenue) AS revenue,
                    COUNT(crm.id) AS total_leads
                FROM crm_lead AS crm
                LEFT JOIN crm_tag_rel AS tag_rel ON tag_rel.lead_id = crm.id
                LEFT JOIN crm_tag AS tag ON tag.id = tag_rel.tag_id
                {where_clause}
                GROUP BY tag.id, tag.name
                ORDER BY revenue DESC;
            """
    
        self.env.cr.execute(query)
        results = self.env.cr.dictfetchall()
    
        if comp_id:
            # Format by Salesperson
            formatted_result = {
                "tag_id": [res["user_id"] for res in results],
                "tag_name": [res["user_name"] or "No Salesperson" for res in results],
                "revenue": [res["revenue"] for res in results],
                "total_leads": [res["total_leads"] for res in results],
                "domain1": query,
                "domain": onclick_domain
            }
        else:
            # Format by Tag
            formatted_result = {
                "tag_id": [res["tag_id"] for res in results],
                "tag_name": [res["tag_name"].get("en_US") if isinstance(res["tag_name"], dict) else res["tag_name"] or "No Comp" for res in results],
                "revenue": [res["revenue"] for res in results],
                "total_leads": [res["total_leads"] for res in results],
                "domain1": query,
                "domain": onclick_domain
            }
    
        return formatted_result


    
    
        

    def get_quote_submitted_graph_product(self, comp_id=None, team_id=None, user_id=None, product_id=None, job_id=None, filter_by='month', selected_year=None):
        domain = []
        onclick_domain=[]
    
        if job_id:
            domain.append(f'crm."job_type" = \'{job_id}\'')
            onclick_domain.append(('job_type','=',job_id))
        if product_id:
            domain.append(f"pt.id = {int(product_id)}")  # Ensure only the selected product is shown
            onclick_domain.append(('product_ids','=',int(product_id)))
        if comp_id:
            domain.append(f"tag.id = {int(comp_id)}")
            onclick_domain.append(('tag_ids','=',int(comp_id)))
        if team_id:
            domain.append(f"crm.team_id = {int(team_id)}")
            onclick_domain.append(('team_id','=',int(team_id)))
        if user_id:
            domain.append(f"crm.user_id = {int(user_id)}")
            onclick_domain.append(('user_id','=',int(user_id)))
    
        user = self.env.user
        is_admin = user.has_group('base.group_system')  # Admin check
        is_team_lead = user.has_group('crm_dashboard.dashboard_team_leader')
        
    
        today = fields.Date.today()
        target_year = int(selected_year) if selected_year and str(selected_year).isdigit() and int(selected_year) > 0 else today.year
    
        # Set the date range based on the filter (month or year)
        if filter_by == 'month':
            start_date = date(target_year, today.month, 1)
            last_day = calendar.monthrange(target_year, today.month)[1]
            end_date = date(target_year, today.month, last_day)
        else:  # Default to year filter
            start_date = date(target_year, 1, 1)
            end_date = date(target_year, 12, 31)
    
        # Stages to filter
        stages = [
            'Quote Submitted',
            'Expecting (60%)',
            'Commit (90%)',
            'Won',
            'Partial Order Released'
        ]
        stage_list = [stage.id for stage in self.env['crm.stage'].search([('name', 'in', stages)])]
    
        if stage_list:
            domain.append(f"crm.stage_id IN ({', '.join(map(str, stage_list))})")
            onclick_domain.append(('stage_id','in',stage_list))
    
        domain.append(f"COALESCE(crm.date_open, crm.create_date) >= '{start_date}'")
        domain.append(f"COALESCE(crm.date_open, crm.create_date) <= '{end_date}'")
        onclick_domain.append(('date_open','>=',start_date))
        onclick_domain.append(('date_open','<=',end_date))
    
        if not is_admin and not is_team_lead:
            employee = self.env['hr.employee'].search([('user_id', '=', user.id)], limit=1)
            if employee:
                domain.append(f"crm.user_id = {user.id}")
                onclick_domain.append(('user_id','=',user.id))
            else:
                return {'error': 'Employee record not found for this user.'}
        if not is_admin and is_team_lead and not team_id and not user_id:
            employee = self.env['hr.employee'].search([('user_id', '=', user.id)], limit=1)
            if employee:
                domain.append(f"crm.user_id = {user.id}")
                onclick_domain.append(('user_id','=',user.id))
            else:
                return {'error': 'Employee record not found for this user.'}
    
        where_clause = f"WHERE {' AND '.join(domain)}" if domain else ""
    
        query = f"""
            SELECT 
                pt.name AS product,
                SUM(crm.expected_revenue) AS revenue,
                COUNT(crm.id) AS total_leads
            FROM crm_lead AS crm
            LEFT JOIN crm_lead_product_template_rel AS pt_rel ON pt_rel.lead_id = crm.id
            LEFT JOIN product_template AS pt ON pt.id = pt_rel.product_id
            LEFT JOIN crm_tag_rel AS tag_rel ON tag_rel.lead_id = crm.id
            LEFT JOIN crm_tag AS tag ON tag.id = tag_rel.tag_id
            {where_clause}
            GROUP BY pt.id, pt.name
            ORDER BY revenue DESC;
        """
    
        print("this is my query", query)
        self.env.cr.execute(query)
        results = self.env.cr.dictfetchall()
        print("this is my result query", results)
    
        formatted_result = {
            "product": [res["product"].get("en_US") if isinstance(res.get("product"), dict) else res.get("product") or "No Product" for res in results],
            "revenue": [res["revenue"] for res in results],
            "total_leads": [res["total_leads"] for res in results],
            "domain1": query,
            "domain":onclick_domain
        }
    
        return formatted_result if results else {  "product": [],
                                                    "revenue": [],
                                                    "total_leads": [],
                                                    "domain1": query,
                                                    "domain":onclick_domain}

        
 
    def get_forecast_submitted_graph_company(self, comp_id=None, team_id=None, user_id=None, job_id=None, filter_by='year', month_name=None, selected_year=None):
        domain = []
        domain_year=[]
        params = []
        onclick_domain = []

        if not month_name:
            month_name = fields.Date.today().strftime('%m')
    
        if job_id:
            domain.append(f"crm.\"job_type\" = '{job_id}'")
            domain_year.append(f"crm.\"job_type\" = '{job_id}'")
            onclick_domain.append(('job_type', '=', job_id))
    
        if comp_id:
            domain.append(f"tag.id = {int(comp_id)}")
            domain_year.append(f"tag.id = {int(comp_id)}")
            onclick_domain.append(('tag_ids', '=', int(comp_id)))
    
        if team_id:
            domain.append(f"crm.team_id = {int(team_id)}")
            domain_year.append(f"crm.team_id = {int(team_id)}")
            onclick_domain.append(('team_id', '=', int(team_id)))
    
        if user_id:
            domain.append(f"crm.user_id = {int(user_id)}")
            domain_year.append(f"crm.user_id = {int(user_id)}")
            onclick_domain.append(('user_id', '=', int(user_id)))
    
        user = self.env.user
        is_admin = user.has_group('base.group_system')
        is_team_lead = user.has_group('crm_dashboard.dashboard_team_leader')
    
        stages = ['Regret', 'Won', 'Lost']
        quote_submitted_stage = self.env['crm.stage'].search([('name', 'in', stages)])
        stage_list = [stage.id for stage in quote_submitted_stage]
        today = fields.Date.today()
        target_year = int(selected_year) if selected_year and str(selected_year).isdigit() and int(selected_year) > 0 else today.year
        
        start_date=''
        end_date=''
        year_start_date=''
        year_end_date=''
        
        if month_name:
                month = int(month_name)
                start_date = date(target_year, month, 1)
                last_day = calendar.monthrange(target_year, month)[1]
                end_date = date(target_year, month, last_day)

        if filter_by == 'year':
            year_start_date = date(target_year, 1, 1)
            year_end_date = date(target_year, 12, 31)
            
    
        domain.append(f"crm.date_deadline >= '{start_date}'")
        domain.append(f"crm.date_deadline <= '{end_date}'")

        domain_year.append(f"crm.date_deadline >= '{year_start_date}'")
        domain_year.append(f"crm.date_deadline <= '{year_end_date}'")
        
        onclick_domain += [('date_deadline', '>=', start_date), ('date_deadline', '<=', end_date)]
    
        if not is_admin and not is_team_lead:
            employee = self.env['hr.employee'].search([('user_id', '=', user.id)], limit=1)
            if employee:
                domain.append(f"crm.user_id = {user.id}")
                domain_year.append(f"crm.user_id = {user.id}")
                onclick_domain.append(('user_id', '=', user.id))
            else:
                return {'error': 'Employee record not found for this user.'}
    
        if not is_admin and is_team_lead and not team_id and not user_id:
            employee = self.env['hr.employee'].search([('user_id', '=', user.id)], limit=1)
            if employee:
                domain.append(f"crm.user_id = {user.id}")
                domain_year.append(f"crm.user_id = {user.id}")
                onclick_domain.append(('user_id', '=', user.id))
            else:
                return {'error': 'Employee record not found for this user.'}
    
        domain.append("crm.date_deadline IS NOT NULL")
        domain_year.append("crm.date_deadline IS NOT NULL")
        onclick_domain.append(('date_deadline', '!=', False))
    
        if stage_list:
            stage_ids = ', '.join(map(str, stage_list))
            domain.append(f"crm.stage_id NOT IN ({stage_ids})")
            domain_year.append(f"crm.stage_id NOT IN ({stage_ids})")
            onclick_domain.append(('stage_id', 'not in', stage_list))
    
        where_clause = f"WHERE {' AND '.join(domain)}" if domain else ""

        where_clause_year = f"WHERE {' AND '.join(domain_year)}" if domain_year else ""
    
        # GROUP BY logic based on comp_id
        if comp_id:
            group_by_field = "month,crm.user_id,res.name"
            select_field = "res.name AS salesperson"
            join_user = "LEFT JOIN res_users AS usr ON usr.id = crm.user_id LEFT JOIN res_partner AS res ON res.id = usr.partner_id"
        else:
            group_by_field = "month,tag.id, tag.name"
            select_field = "tag.name AS tag_name"
            join_user = ""
    
        query = f"""
            SELECT 
                {select_field},
                TO_CHAR(crm.date_deadline, 'MM') AS month,
                SUM(crm.expected_revenue) AS revenue,
                COUNT(crm.id) AS total_leads
            FROM crm_lead AS crm
            LEFT JOIN crm_tag_rel AS tag_rel ON tag_rel.lead_id = crm.id
            LEFT JOIN crm_tag AS tag ON tag.id = tag_rel.tag_id
            LEFT JOIN crm_lead_product_template_rel AS pt_rel ON pt_rel.lead_id = crm.id
            LEFT JOIN product_template AS pt ON pt.id = pt_rel.product_id
            {join_user}
            {where_clause}
            GROUP BY {group_by_field}
            ORDER BY revenue DESC;
        """

        year_query = f"""
            SELECT 
                {select_field},
                TO_CHAR(crm.date_deadline, 'MM') AS month,
                SUM(crm.expected_revenue) AS revenue,
                COUNT(crm.id) AS total_leads
            FROM crm_lead AS crm
            LEFT JOIN crm_tag_rel AS tag_rel ON tag_rel.lead_id = crm.id
            LEFT JOIN crm_tag AS tag ON tag.id = tag_rel.tag_id
            LEFT JOIN crm_lead_product_template_rel AS pt_rel ON pt_rel.lead_id = crm.id
            LEFT JOIN product_template AS pt ON pt.id = pt_rel.product_id
            {join_user}
            {where_clause_year}
            GROUP BY {group_by_field}
            ORDER BY revenue DESC;
        """
    
    
        print("this is my query", query)
        
        self.env.cr.execute(query)
        results = self.env.cr.dictfetchall()
        self.env.cr.execute(year_query)
        results_year = self.env.cr.dictfetchall()
        
        available_months = sorted(set(row['month'] for row in results_year if row.get('month')))
        
        def _get_name(val):
            if isinstance(val, dict):
                return val.get('en_US') or next(iter(val.values()), '')
            return str(val) if val else 'No Tag'
        
        print("this is my result query", results)
    
        return {
            "group_by": "salesperson" if comp_id else "tag_name",
            "tag_name": [res["salesperson"] if comp_id else _get_name(res.get("tag_name")) for res in results],
            "revenue": [res["revenue"] for res in results],
            "total_leads": [res["total_leads"] for res in results],
            "domain": onclick_domain,
            "domain_year": domain_year,
            "year_query":year_query,
            "query":query,
            'results':results,
            'results_year':results_year,
            "available_months":available_months,
            "year_start_date":str(year_start_date),
            "year_end_date":str(year_end_date),
            "start_date":str(start_date),
            "end_date":str(end_date)
        }





    def get_forecast_submitted_graph_product(self, comp_id=None, team_id=None, user_id=None, product_id=None, job_id=None, filter_by='month', month_name=None, selected_year=None):
        domain = []
        onclick_domain=[]

        if not month_name:
            month_name = fields.Date.today().strftime('%m')
    
        if job_id:
            domain.append(f'crm."job_type" = \'{job_id}\'')
            onclick_domain.append(('job_type','=',job_id))
        if product_id:
            domain.append(f"pt.id = {int(product_id)}")  # Filter by product_id
            onclick_domain.append(('product_ids','=',int(product_id)))
        if comp_id:
            domain.append(f"tag.id = {int(comp_id)}")
            onclick_domain.append(('tag_ids','=',int(comp_id)))
        if team_id:
            domain.append(f"crm.team_id = {int(team_id)}")
            onclick_domain.append(('team_id','=',int(team_id)))
        if user_id:
            domain.append(f"crm.user_id = {int(user_id)}")
            onclick_domain.append(('user_id','=',int(user_id)))
    
        user = self.env.user
        is_admin = user.has_group('base.group_system')
        is_team_lead = user.has_group('crm_dashboard.dashboard_team_leader')
        
        stages = ['Regret', 'Won', 'Lost']
        quote_submitted_stage = self.env['crm.stage'].search([('name', 'in', stages)])
        stage_list = [stage['id'] for stage in stage_ids.read(['id'])] if 'stage_ids' in locals() else [s.id for s in quote_submitted_stage]
        excluded_stage_ids = [s.id for s in quote_submitted_stage]
    
        today = fields.Date.today()
        target_year = int(selected_year) if selected_year and str(selected_year).isdigit() and int(selected_year) > 0 else today.year
    
        if month_name:
                month = int(month_name)
                start_date = date(target_year, month, 1)
                last_day = calendar.monthrange(target_year, month)[1]
                end_date = date(target_year, month, last_day)
    
        domain.append(f"crm.date_deadline >= '{start_date}'")
        domain.append(f"crm.date_deadline <= '{end_date}'")
        
        onclick_domain.append(('date_deadline','>=',start_date))
        onclick_domain.append(('date_deadline','<=',end_date))
        
    
        if not is_admin and not is_team_lead:
            employee = self.env['hr.employee'].search([('user_id', '=', user.id)], limit=1)
            if employee:
                domain.append(f"crm.user_id = {user.id}")
                onclick_domain.append(('user_id','=',user.id))
    
            else:
                return {'error': 'Employee record not found for this user.'}

        if not is_admin and is_team_lead and not team_id and not user_id:
            employee = self.env['hr.employee'].search([('user_id', '=', user.id)], limit=1)
            if employee:
                domain.append(f"crm.user_id = {user.id}")
                onclick_domain.append(('user_id','=',user.id))
            else:
                return {'error': 'Employee record not found for this user.'}

        
        domain.append("crm.date_deadline IS NOT NULL")
        onclick_domain.append(('date_deadline','!=',False))
    
        if excluded_stage_ids:
            stage_ids_str = ', '.join(map(str, excluded_stage_ids))  # Convert list to comma-separated string
            domain.append(f"crm.stage_id NOT IN ({stage_ids_str})")
            onclick_domain.append(('stage_id','not in',stage_list))
    
        where_clause = f"WHERE {' AND '.join(domain)}" if domain else ""
    
        query = f"""
            SELECT 
                pt.name AS product,
                SUM(crm.expected_revenue) AS revenue,
                COUNT(crm.id) AS total_leads
            FROM crm_lead AS crm
            LEFT JOIN crm_lead_product_template_rel AS pt_rel ON pt_rel.lead_id = crm.id
            LEFT JOIN product_template AS pt ON pt.id = pt_rel.product_id
            LEFT JOIN crm_tag_rel AS tag_rel ON tag_rel.lead_id = crm.id
            LEFT JOIN crm_tag AS tag ON tag.id = tag_rel.tag_id
            {where_clause}
            GROUP BY pt.id, pt.name
            ORDER BY revenue DESC;
        """
    
        self.env.cr.execute(query)
        results = self.env.cr.dictfetchall()
        available_months = sorted(set(
            row['month'] for row in results if row.get('month')
        ))
    
        def _get_name(val):
            if isinstance(val, dict):
                return val.get('en_US') or next(iter(val.values()), '')
            return str(val) if val else 'No Product'

        formatted_result = {
            "product": [_get_name(res.get("product")) for res in results],
            "revenue": [res["revenue"] for res in results],
            "total_leads": [res["total_leads"] for res in results],
            "domain":onclick_domain,
            "domain1":query,
            "available_months":available_months
        }
    
        return formatted_result if results else { "product": [],
                                                    "revenue": [],
                                                    "total_leads": [],
                                                  "domain":onclick_domain,
                                                    "domain1":query}


        
    def get_mail_activity_lists(self, user_id=None,comp_id=None,team_id=None,filter_by='year'):
            domain = []
            user = self.env.user
            is_admin = user.has_group('base.group_system')  # Admin check
            is_team_lead = user.has_group('crm_dashboard.dashboard_team_leader')
        
            if not user_id and team_id:
                 team_members = self.env['crm.team.member'].search([('crm_team_id', '=', int(team_id))])
                 user_ids = [tm['user_id'][0] for tm in team_members.read(['user_id']) if tm['user_id']]
                 employees =[emp.id for emp in self.env['res.users'].browse(user_ids)]
                 # employee_list = [{'id': emp.id, 'name': emp.name} for emp in employees]
                 if employees:
                     domain.append(['user_id', 'in', employees])
      
                            
            if not is_admin and not is_team_lead:
                domain.append(['user_id', '=', user.id])

            if not is_admin and is_team_lead and not user_id and not team_id:
                domain.append(['user_id', '=', user.id])
            
            if user_id:
                domain.append(['user_id', '=', int(user_id)])
        
            today = fields.Date.today()
        
            if filter_by == 'month':
                start_date = today.replace(day=1)  # First day of the current month
            else:  # Default to year filter
                start_date = today.replace(month=1, day=1)  # First day of the current year
        
            end_date = today  # Today's date
            
            # domain.append(['date_deadline', '>=', start_date])
            domain.append(['date_deadline', '<=', end_date])
            domain.append(('is_copied_activity', '=', False))
            # Using search_read to fetch only required fields
            activities = self.env['mail.activity'].search_read(
                domain,
                ['id', 'res_id', 'activity_from', 'res_model', 'customer_name','activity_type_id', 'user_id', 'date_deadline']
            )
            activity_ids=[acti['id']for acti in activities]
        
            # Fetch names for res_id records dynamically
            formatted_activities = []
            activity_from_map = {
                'res.partner': 'Contact',
                'employee.payment.collection.line': 'Payment',
                'crm.lead': 'CRM',
                'others': 'Others'
            }
            for activity in activities:
                res_model = activity.get('res_model')
                res_id = activity.get('res_id')
                date_deadline = activity.get('date_deadline')
                activity_from =  activity_from_map.get(activity.get('activity_from'), 'Others')
        
                # Get the name of the related record dynamically

                if comp_id:
                    if res_model in  ['crm.lead','employee.payment.collection.line'] :
                        res_name = ''
                        if res_model and res_id:
                            related_record=''
                            if res_model == 'crm.lead':
                                related_record = self.env[res_model].search([('id','=',res_id),('tag_ids','=',int(comp_id))])
                            if res_model == 'employee.payment.collection.line':    
                                 tag = self.env['crm.tag'].browse(int(comp_id))
                                 if tag.exists():
                                    record = self.env['employee.payment.collection.line'].search([
                                        ('id', '=', res_id),
                                        ('division', '=', tag.name)
                                    ])
                                    if record:
                                        related_record=record

                            if related_record:
                                res_name = related_record.name if hasattr(related_record, 'name') else f"ID {res_id}"
                
                                # Calculate remaining days
                                deadline_label = ''
                                if date_deadline:
                                    deadline_date = fields.Date.from_string(date_deadline)
                                    diff_days = (deadline_date - today).days
                        
                                    if diff_days == 0:
                                        deadline_label = "Today"
                                    elif diff_days == -1:
                                        deadline_label = "Yesterday"
                                    elif diff_days == 1:
                                        deadline_label = "Tomorrow"
                                    elif diff_days < 0:
                                        deadline_label = f"{abs(diff_days)} days ago"
                                    else:
                                        deadline_label = f"In {diff_days} days"
                        
                                formatted_activities.append({
                                    'id': activity.get('id'),
                                    'from': activity_from_map.get(activity.get('activity_from'), 'Others'),
                                    'res_id': activity.get('res_id'),
                                    'res_model':activity.get('res_model'),
                                    'res_name':activity.get('customer_name'),
                                    'activity_type': self.env['mail.activity.type'].browse(activity.get('activity_type_id')[0]).name if activity.get('activity_type_id') else '',
                                    'user_name': self.env['res.users'].browse(activity.get('user_id')[0]).name if activity.get('user_id') else '',
                                    'date_deadline': date_deadline,
                                    'remaining_days': deadline_label,  # Added label
                                })
        
        


                if not comp_id:
                     
                    res_name = ''
                    if res_model and res_id:
                        related_record = self.env[res_model].browse(res_id)
                        res_name = related_record.name if hasattr(related_record, 'name') else f"ID {res_id}"
            
                    # Calculate remaining days
                    deadline_label = ''
                    if date_deadline:
                        deadline_date = fields.Date.from_string(date_deadline)
                        diff_days = (deadline_date - today).days
            
                        if diff_days == 0:
                            deadline_label = "Today"
                        elif diff_days == -1:
                            deadline_label = "Yesterday"
                        elif diff_days == 1:
                            deadline_label = "Tomorrow"
                        elif diff_days < 0:
                            deadline_label = f"{abs(diff_days)} days ago"
                        else:
                            deadline_label = f"In {diff_days} days"
            
                    formatted_activities.append({
                        'id': activity.get('id'),
                        'from': activity_from_map.get(activity.get('activity_from'), 'Others'),
                        'res_id': activity.get('res_id'),
                        'res_model':activity.get('res_model'),
                        'res_name':activity.get('customer_name'),
                        'activity_type': self.env['mail.activity.type'].browse(activity.get('activity_type_id')[0]).name if activity.get('activity_type_id') else '',
                        'user_name': self.env['res.users'].browse(activity.get('user_id')[0]).name if activity.get('user_id') else '',
                        'date_deadline': date_deadline,
                        'remaining_days': deadline_label,  # Added label
                    })

            id_list = [activity['id'] for activity in formatted_activities]
        
        
            return { 'formatted_activities':formatted_activities,
                    'id_list':id_list,
                    'domain':domain,
                    'activity_ids':activity_ids
                   }



    
     
    def get_employee_payment_totals(self, user_id=None, team_id=None, comp_id=None, month_name=None):
        """
        Returns structured payment data with formatted amounts (with commas).
        """
        domain = []
        user = self.env.user
        is_admin = user.has_group('base.group_system')
        is_team_lead = user.has_group('crm_dashboard.dashboard_team_leader')
        
    
        if not is_admin and not is_team_lead:
            domain.append(('employee_id.user_id', '=', user.id))

        if not is_admin and is_team_lead and not team_id and not user_id:
            domain.append(('employee_id.user_id', '=', user.id))
            
    
        if comp_id:
            domain.append(('divition_id', '=', int(comp_id)))
                
        
        if month_name:
            domain.append(('month_name', '=', month_name))
    
        if user_id:
            domain.append(('employee_id.user_id', '=', int(user_id)))
        elif team_id and not user_id:
           
            team_id = int(team_id)
            team_members = self.env['crm.team.member'].search([('crm_team_id', '=', team_id)])
            member_ids = team_members.mapped('user_id.id')
            domain.append(('employee_id.user_id', 'in', member_ids))
    
        lines = self.env['employee.payment.collection.line'].search(domain)
    
        # Raw totals for calc
        raw_totals = {
            'overdue': {'amount': 0.0, 'collected': 0.0},
            'due': {'amount': 0.0, 'collected': 0.0},
            'nondue': {'amount': 0.0, 'collected': 0.0},
        }
    
        for rec in lines:
            if rec.due_type == 'overdue':
                raw_totals['overdue']['amount'] += rec.due_amount
                if rec.verified:
                    raw_totals['overdue']['collected'] += rec.collected_amount
            elif rec.due_type == 'due':
                raw_totals['due']['amount'] += rec.due_amount
                if rec.verified:
                    raw_totals['due']['collected'] += rec.collected_amount
            elif rec.due_type == 'nodue':
                raw_totals['nondue']['amount'] += rec.due_amount
                if rec.verified:
                    raw_totals['nondue']['collected'] += rec.collected_amount
    
        # Helper function for percentage
        def calc_percent(collected, amount):
            return round((collected / amount * 100), 2) if amount else 0.0
    
        def fmt(value):
            return "{:,.2f}".format(value)
    
        # Build final formatted structure
        result = {
            'domain':domain,
            'overdue': {
                'amount': fmt(raw_totals['overdue']['amount']),
                'collected': fmt(raw_totals['overdue']['collected']),
                'collected_percentage': calc_percent(raw_totals['overdue']['collected'], raw_totals['overdue']['amount']),
            },
            'due': {
                'amount': fmt(raw_totals['due']['amount']),
                'collected': fmt(raw_totals['due']['collected']),
                'collected_percentage': calc_percent(raw_totals['due']['collected'], raw_totals['due']['amount']),
            },
            'nondue': {
                'amount': fmt(raw_totals['nondue']['amount']),
                'collected': fmt(raw_totals['nondue']['collected']),
                'collected_percentage': calc_percent(raw_totals['nondue']['collected'], raw_totals['nondue']['amount']),
            },
        }
    
        total_amount = sum(raw_totals[k]['amount'] for k in raw_totals)
        total_collected = sum(raw_totals[k]['collected'] for k in raw_totals)
        result['total'] = {
            'totalamount': fmt(total_amount),
            'totalcollected': fmt(total_collected),
            'totalcollected_percentage': calc_percent(total_collected, total_amount)
        }
    
        return result




    def get_realization_summary(self, user_id=None, team_id=None, comp_id=None, month_name=None):
        domain = []
        onclick_domain=[]
        user = self.env.user
        is_admin = user.has_group('base.group_system')
        is_team_lead = user.has_group('crm_dashboard.dashboard_team_leader')
    
        if not is_admin and not is_team_lead:
            domain.append(('group_id.employee_id.user_id.id', '=', user.id))
            onclick_domain.append(('employee_id.user_id.id', '=', user.id))
        if not is_admin and is_team_lead and not team_id and not user_id:
            domain.append(('group_id.employee_id.user_id.id', '=', user.id))
            onclick_domain.append(('group_id.employee_id.user_id.id', '=', user.id))
    
        if comp_id:
            domain.append(('group_id.divition_id.id', '=', int(comp_id)))
            domain.append(('group_id.employee_id', '!=', False))
            onclick_domain.append(('divition_id.id', '=', int(comp_id)))
            onclick_domain.append(('employee_id', '!=', False))
    
        if month_name:
            domain.append(('group_id.month_name', '=', month_name))
            onclick_domain.append(('month_name', '=', month_name))
        if user_id:
            domain.append(('group_id.employee_id.user_id', '=', int(user_id)))
            onclick_domain.append(('employee_id.user_id', '=', int(user_id)))
            team_comp_ids = self.env['crm.team.member'].search([('user_id', '=', int(user_id))]).mapped('crm_team_id.x_studio_division.id')
            if team_comp_ids:
                domain.append(('group_id.divition_id.id', 'in', team_comp_ids))
                onclick_domain.append(('divition_id.id', 'in', team_comp_ids))
        elif team_id and not user_id:
            team_members = self.env['crm.team.member'].search([('crm_team_id', '=', int(team_id))])
            member_ids = team_members.mapped('user_id.id')
            domain.append(('group_id.employee_id.user_id', 'in', member_ids))
            onclick_domain.append(('employee_id.user_id', 'in', member_ids))
    
        domain.append(('verified', '=', True))
       
    
        today = date.today()
        current_month_start = today.replace(day=1)
        current_month_end = current_month_start + relativedelta(months=1) - relativedelta(days=1)
        next_month_start = current_month_start + relativedelta(months=1)
        year_end = today.replace(month=12, day=31)
    
        lines = self.env['report.employee.payment.grouped.basic.line'].search(domain)
    
        def get_group_key(line):
            if comp_id:
                return (line.group_id.employee_id.name or 'Unknown', line.group_id.employee_id.id)
            else:
                return (line.group_id.divition_id.name or 'Unknown', line.group_id.divition_id.id)
    
        summary = defaultdict(lambda: {
            'outstanding': 0.0,
            'current_month_pdc': 0.0,
            'future_month_pdc': 0.0,
            'collection_current': 0.0,
            'collection_pdc': 0.0,
            'total_collection': 0.0,
            'total_realised': 0.0,
            'balance_realise_current': 0.0,
            'balance_realise_future': 0.0,
            'record_ids': set(),
        })
    
        def fmt(val):
            return "{:,.2f}".format(val)
    
        for line in lines:
            key = get_group_key(line)
            s = summary[key]
            s['record_ids'].add(line.id)
          
    
            realization_date = line.realisation_date
            actual_realized_date = line.actual_realised_date or None
            is_pdc = line.custom_type in ('pdc', 'lc')
    
            # Outstanding
            s['outstanding'] += line.invoice_amount or 0.0
    
            # Current Month PDC/LC: Year start to current month, not realized, realization_date <= current month end
            if is_pdc and not line.is_realised and realization_date and realization_date <= current_month_end and realization_date.year == today.year:
                s['current_month_pdc'] += line.collected_amount or 0.0
    
            # Future Month PDC/LC: Next month to year end, not realized, realization_date > current month end
            if is_pdc and not line.is_realised and realization_date and realization_date > current_month_end and realization_date.year == today.year:
                s['future_month_pdc'] += line.collected_amount or 0.0
    
            # Collection (Current): Current month, verified, type == 'tt_cdc'
            if line.custom_type == 'tt_cdc' and realization_date and realization_date.month == today.month and realization_date.year == today.year:
                s['collection_current'] += line.collected_amount or 0.0
    
            # Collection PDC/LC: Current month, verified, type in ('pdc', 'lc')
            if is_pdc and realization_date and realization_date.month == today.month and realization_date.year == today.year:
                s['collection_pdc'] += line.collected_amount or 0.0
    
            # Total Collection
            s['total_collection'] = s['collection_current'] + s['collection_pdc']
    
            # Total Realized: current month, realized, actual_realized_date in current month
            if line.is_realised and actual_realized_date and actual_realized_date.month == today.month and actual_realized_date.year == today.year:
                s['total_realised'] += line.collected_amount or 0.0
    
            # Balance To Realize (Current): Not realized, realization_date <= current_month_end
            if not line.is_realised and realization_date and realization_date <= current_month_end:
                s['balance_realise_current'] += line.collected_amount or 0.0
    
            # Balance To Realize (Future): Not realized, realization_date > current_month_end
            if not line.is_realised and realization_date and realization_date > current_month_end:
                s['balance_realise_future'] += line.collected_amount or 0.0
    
        result = []
             
        for (label, _id), values in summary.items():
            record = {
                'order': label,
                'outstanding': fmt(values['outstanding']),
                'current_month_pdc': fmt(values['current_month_pdc']),
                'future_month_pdc': fmt(values['future_month_pdc']),
                'collection_current': fmt(values['collection_current']),
                'collection_pdc': fmt(values['collection_pdc']),
                'total_collection': fmt(values['total_collection']),
                'total_realised': fmt(values['total_realised']),
                'balance_realise_current': fmt(values['balance_realise_current']),
                'balance_realise_future': fmt(values['balance_realise_future']),
                'record_ids': list(values['record_ids']),
            }

            # Add employee_id or divition_id based on comp_id
            if comp_id:
                record['employee_id'] = _id
            else:
                record['divition_id'] = _id

            result.append(record)

    
        return {
            'result':result,
            'onclick_domain':onclick_domain
        }




    # def get_realization_summary(self, user_id=None, team_id=None, comp_id=None, month_name=None):
    #     domain = []
    #     onclick_domain = []
    #     user = self.env.user
    #     is_admin = user.has_group('base.group_system')
    #     is_team_lead = user.has_group('crm_dashboard.dashboard_team_leader')
    
    #     if not is_admin and not is_team_lead:
    #         domain.append(('group_id.employee_id.user_id.id', '=', user.id))
    #         onclick_domain.append(('employee_id.user_id.id', '=', user.id))
    #     if not is_admin and is_team_lead and not team_id and not user_id:
    #         domain.append(('group_id.employee_id.user_id.id', '=', user.id))
    #         onclick_domain.append(('group_id.employee_id.user_id.id', '=', user.id))
    
    #     if comp_id:
    #         domain.append(('group_id.divition_id.id', '=', int(comp_id)))
    #         domain.append(('group_id.employee_id', '!=', False))
    #         onclick_domain.append(('divition_id.id', '=', int(comp_id)))
    #         onclick_domain.append(('employee_id', '!=', False))
    
    #     if month_name:
    #         domain.append(('group_id.month_name', '=', month_name))
    #         onclick_domain.append(('month_name', '=', month_name))
    
    #     if user_id:
    #         domain.append(('group_id.employee_id.user_id', '=', int(user_id)))
    #         onclick_domain.append(('employee_id.user_id', '=', int(user_id)))
    #         team_comp_ids = self.env['crm.team.member'].search([('user_id', '=', int(user_id))]).mapped('crm_team_id.x_studio_division.id')
    #         if team_comp_ids:
    #             domain.append(('group_id.divition_id.id', 'in', team_comp_ids))
    #             onclick_domain.append(('divition_id.id', 'in', team_comp_ids))
    #     elif team_id and not user_id:
    #         team_members = self.env['crm.team.member'].search([('crm_team_id', '=', int(team_id))])
    #         member_ids = team_members.mapped('user_id.id')
    #         domain.append(('group_id.employee_id.user_id', 'in', member_ids))
    #         onclick_domain.append(('employee_id.user_id', 'in', member_ids))
    
    #     domain.append(('verified', '=', True))
    
    #     today = date.today()
    #     current_month_start = today.replace(day=1)
    #     current_month_end = current_month_start + relativedelta(months=1) - relativedelta(days=1)
    #     next_month_start = current_month_start + relativedelta(months=1)
    #     year_end = today.replace(month=12, day=31)
    
    #     lines = self.env['report.employee.payment.grouped.basic.line'].search(domain)
    
    #     def get_group_key(line):
    #         if comp_id:
    #             return (line.group_id.employee_id.name or 'Unknown', line.group_id.employee_id.id)
    #         else:
    #             return (line.group_id.divition_id.name or 'Unknown', line.group_id.divition_id.id)
    
    #     summary = defaultdict(lambda: {
    #         'outstanding': 0.0,
    #         'current_month_pdc': 0.0,
    #         'future_month_pdc': 0.0,
    #         'collection_current': 0.0,
    #         'collection_pdc': 0.0,
    #         'total_collection': 0.0,
    #         'total_realised': 0.0,
    #         'balance_realise_current': 0.0,
    #         'balance_realise_future': 0.0,
    #     })
    
    #     def fmt(val):
    #         return "{:,.2f}".format(val)
    
    #     for line in lines:
    #         key = get_group_key(line)
    #         s = summary[key]
    
    #         realization_date = line.realisation_date
    #         actual_realized_date = line.actual_realised_date or None
    #         is_pdc = line.custom_type in ('pdc', 'lc')
    
    #         # Outstanding
    #         s['outstanding'] += line.invoice_amount or 0.0
    
    #         # Current Month PDC/LC
    #         if is_pdc and not line.is_realised and realization_date and realization_date <= current_month_end and realization_date.year == today.year:
    #             s['current_month_pdc'] += line.collected_amount or 0.0
    
    #         # Future Month PDC/LC
    #         if is_pdc and not line.is_realised and realization_date and realization_date > current_month_end and realization_date.year == today.year:
    #             s['future_month_pdc'] += line.collected_amount or 0.0
    
    #         # Collection (Current)
    #         if line.custom_type == 'tt_cdc' and realization_date and realization_date.month == today.month and realization_date.year == today.year:
    #             s['collection_current'] += line.collected_amount or 0.0
    
    #         # Collection PDC/LC
    #         if is_pdc and realization_date and realization_date.month == today.month and realization_date.year == today.year:
    #             s['collection_pdc'] += line.collected_amount or 0.0
    
    #         # Total Collection
    #         s['total_collection'] = s['collection_current'] + s['collection_pdc']
    
    #         # Total Realized
    #         if line.is_realised and actual_realized_date and actual_realized_date.month == today.month and actual_realized_date.year == today.year:
    #             s['total_realised'] += line.collected_amount or 0.0
    
    #         # Balance To Realize (Current)
    #         if not line.is_realised and realization_date and realization_date <= current_month_end:
    #             s['balance_realise_current'] += line.collected_amount or 0.0
    
    #         # Balance To Realize (Future)
    #         if not line.is_realised and realization_date and realization_date > current_month_end:
    #             s['balance_realise_future'] += line.collected_amount or 0.0
    
    #     result = []
    #     for (label, id_), values in summary.items():
    #         result_entry = {
    #             'order': label,
    #             'outstanding': fmt(values['outstanding']),
    #             'current_month_pdc': fmt(values['current_month_pdc']),
    #             'future_month_pdc': fmt(values['future_month_pdc']),
    #             'collection_current': fmt(values['collection_current']),
    #             'collection_pdc': fmt(values['collection_pdc']),
    #             'total_collection': fmt(values['total_collection']),
    #             'total_realised': fmt(values['total_realised']),
    #             'balance_realise_current': fmt(values['balance_realise_current']),
    #             'balance_realise_future': fmt(values['balance_realise_future']),
    #         }
    
    #         # Add employee_id or divition_id
    #         if comp_id:
    #             result_entry['employee_id'] = id_
    #         else:
    #             result_entry['divition_id'] = id_
    
    #         result.append(result_entry)
    
    #     return {
    #         'result': result,
    #         'onclick_domain': onclick_domain
    #     }



  

    def new_get_employee_payment_totals(self, user_id=None, team_id=None, comp_id=None, month_name=None):
        domain = []
        onclick_domain=[]
        user = self.env.user
        is_admin = user.has_group('base.group_system')
        is_team_lead = user.has_group('crm_dashboard.dashboard_team_leader')
    
        if not is_admin and not is_team_lead:
            domain.append(('group_id.employee_id.user_id', '=', user.id))
            onclick_domain.append(('employee_id.user_id', '=', user.id))
    
        if not is_admin and is_team_lead and not team_id and not user_id:
            domain.append(('group_id.employee_id.user_id', '=', user.id))
            onclick_domain.append(('employee_id.user_id', '=', user.id))
    
        # Filter by company/divition tag
        if comp_id:
            domain.append(('group_id.divition_id.id', '=', int(comp_id)))
            onclick_domain.append(('divition_id.id', '=', int(comp_id)))
    
        # Filter by month
        if month_name:
            domain.append(('group_id.month_name', '=', month_name))
            onclick_domain.append(('month_name', '=', month_name))
        # Filter by user_id
        if user_id:
            domain.append(('group_id.employee_id.user_id.id', '=', int(user_id)))
            onclick_domain.append(('employee_id.user_id.id', '=', int(user_id)))
            team_comp_ids = self.env['crm.team.member'].search([('user_id', '=', int(user_id))]).mapped('crm_team_id.x_studio_division.id')
            if team_comp_ids:
                domain.append(('group_id.divition_id.id', 'in', team_comp_ids))
                onclick_domain.append(('divition_id.id', 'in', team_comp_ids))
    
        elif team_id and not user_id:
            team_members = self.env['crm.team.member'].search([('crm_team_id', '=', int(team_id))])
            member_ids = team_members.mapped('user_id.id')
            domain.append(('group_id.employee_id.user_id.id', 'in', member_ids))
            onclick_domain.append(('employee_id.user_id.id', 'in', member_ids))
            
    
        # Query payment lines
        lines = self.env['report.employee.payment.grouped.basic.line'].search(domain)
    
        def calc_percent(collected, amount):
            return round((collected / amount * 100), 2) if amount else 0.0
    
        def fmt(val):
            return "{:,.2f}".format(val)
            
        result = defaultdict(lambda: {
        'overdue': {'amount': 0.0, 'collected': 0.0, 'record_ids': []},
        'due': {'amount': 0.0, 'collected': 0.0, 'record_ids': []},
        'nodue': {'amount': 0.0, 'collected': 0.0, 'record_ids': []},
    })

    
     

        if not comp_id:
            # Group by Division
            for line in lines:
                division = line.group_id.divition_id.name or 'Unknown'
                div_id = line.group_id.divition_id.id or 0
                status = (line.due_status or '').lower()
        
                data = result[(division, div_id)][status]
                data['amount'] += line.invoice_amount
                if line.verified:
                    data['collected'] += line.collected_amount
        
                data['record_ids'].append(line.id)  # ✅ Add this line
        else:
            # Group by Employee
            for line in lines:
                employee = line.group_id.employee_id.name or 'Unknown'
                emp_id = line.group_id.employee_id.id or 0
                status = (line.due_status or '').lower()
        
                data = result[(employee, emp_id)][status]
                data['amount'] += line.invoice_amount
                if line.verified:
                    data['collected'] += line.collected_amount
        
                data['record_ids'].append(line.id)  # ✅ Add this line

        formatted = []
        for (key_name, key_id), data in result.items():
            summary = []
            total_amount = total_collected = 0.0
            all_ids = []
        
            for status, vals in data.items():
                amount = vals['amount']
                collected = vals['collected']
                record_ids = vals['record_ids']
                all_ids.extend(record_ids)
        
                total_amount += amount
                total_collected += collected
        
                summary.append({
                    'status': status,
                    'label': {
                        'overdue': 'Over Due',
                        'due': 'Due',
                        'nodue': 'Not Due'
                    }.get(status, status.title()),
                    'amount': fmt(amount),
                    'collected': fmt(collected),
                    'collected_percentage': f"{calc_percent(collected, amount)}%",
                    'record_ids': record_ids  # ✅ for each status group
                })
        
            summary.append({
                'status': 'total',
                'label': 'Total',
                'amount': fmt(total_amount),
                'collected': fmt(total_collected),
                'collected_percentage': f"{calc_percent(total_collected, total_amount)}%",
                'record_ids': all_ids  # ✅ all combined record ids
            })
        
            formatted.append({
                'key': key_name,
                'id': key_id,
                'summary': summary,
                'record_ids': all_ids  # ✅ top-level if needed
            })
    
   
        
        return {
            'domain': domain,
            'onclick_domain':onclick_domain,
            'group_by': 'CMP' if not comp_id else 'EMP',
            'summary': formatted
        }
            
    




        


class MailActivity(models.Model):
    _inherit = 'mail.activity'

    is_copied_activity = fields.Boolean('Is Copied Activity', default=False)
     
