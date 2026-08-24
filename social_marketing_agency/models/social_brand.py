# Copyright (C) 2026 Vertel Sverige AB.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import json

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class SocialBrand(models.Model):
    """A brand — the scoping unit for all customer data.

    A brand belongs to exactly one customer (``res.partner``, the invoiced
    entity); a customer can have zero or more brands. All customer-scoped
    social records (underlag, policies, templates, posts, listening topics,
    streams, accounts, ...) carry a ``brand_id``.
    """

    _name = 'social.brand'
    _description = 'Social Brand'
    _order = 'name'

    name = fields.Char('Brand Name', required=True)
    active = fields.Boolean('Active', default=True)
    partner_id = fields.Many2one(
        'res.partner', string='Customer', required=True, ondelete='cascade',
        domain="[('is_company', '=', True)]",
        help="The customer (res.partner) that is invoiced for this brand. "
             "Its contacts can be invited as customer users.")
    logo = fields.Binary('Logo')
    color = fields.Char('Brand Color')
    customer_edit_enabled = fields.Boolean(
        'Customer Editing Enabled',
        help="If enabled, customer users of this brand get full editing rights "
             "on their own data; otherwise they can only read and approve.")

    default_policy_id = fields.Many2one(
        'communication.policy', string='Default Policy',
        help="Default communication policy used for posts of this brand.")
    dashboard_id = fields.Many2one(
        'dashboard.dashboard', string='Dashboard', copy=False,
        help="Per-brand BI dashboard (dashboard_vrtl), assigned to the brand's users.")

    # Relations
    document_ids = fields.One2many('social.agency.document', 'brand_id', string='Underlag')
    document_count = fields.Integer('Underlag', compute='_compute_document_count')

    _sql_constraints = [
        ('name_partner_uniq', 'UNIQUE(name, partner_id)',
         'A brand with this name already exists for this customer.'),
    ]

    @api.constrains('partner_id')
    def _check_partner_company(self):
        for brand in self:
            if brand.partner_id and not brand.partner_id.is_company:
                raise ValidationError(
                    _('The brand customer must be a company partner.'))

    @api.depends('document_ids')
    def _compute_document_count(self):
        for brand in self:
            brand.document_count = len(brand.document_ids)

    @api.model_create_multi
    def create(self, vals_list):
        brands = super().create(vals_list)
        for brand in brands:
            brand._ensure_dashboard()
        return brands

    def search(self, domain, offset=0, limit=None, order=None):
        """Brand kanban root shows only the agency user's assigned brands.

        Managers see all brands (they administer the platform); regular brand
        users (group_social_agency_brand_user) see only their ``brand_ids``.
        """
        user = self.env.user
        if (not user.share
                and user.has_group(
                    'social_marketing_agency.group_social_agency_brand_user')
                and not user.has_group(
                    'social_marketing.group_social_marketing_manager')):
            domain = list(domain) + [('id', 'in', user.brand_ids.ids)]
        return super().search(domain, offset=offset, limit=limit, order=order)

    def _ensure_dashboard(self):
        """Create (or return) the per-brand dashboard record."""
        self.ensure_one()
        if self.dashboard_id:
            return self.dashboard_id
        parent_menu = self.env.ref(
            'social_marketing_agency.menu_social_customer_dashboard',
            raise_if_not_found=False)
        dashboard = self.env['dashboard.dashboard'].create({
            'name': self.name,
            'key': 'social_brand_%s' % self.id,
            'category': 'Social Brand',
            'access_by': 'user',
            'user_ids': [],
            'parent_menu_id': parent_menu.id if parent_menu else False,
            'menu_sequence': 10,
            'menu_active': True,
        })
        if parent_menu:
            dashboard.create_update_menu()
        self.dashboard_id = dashboard
        self._add_brand_charts(dashboard)
        return dashboard

    def _add_brand_charts(self, dashboard):
        """Add per-brand KPI charts (awaiting customer approval, underlag, listening)."""
        self.ensure_one()
        domain = json.dumps([('brand_id', '=', self.id)])
        charts = [
            ('Awaiting Customer Approval',
             'metric_social_post_awaiting_customer', domain),
            ('Underlag', 'metric_social_agency_document', domain),
            ('Listening Topics', 'metric_social_listening_topic', domain),
        ]
        for name, metric_key, chart_domain in charts:
            metric = self.env.ref('social_marketing_agency.%s' % metric_key)
            self.env['dashboard.chart'].create({
                'name': name,
                'dashboard_id': dashboard.id,
                'metric_id': metric.id,
                'chart_type': 'kpi',
                'domain': chart_domain,
            })

    def action_view_documents(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Underlag',
            'res_model': 'social.agency.document',
            'view_mode': 'list,form',
            'domain': [('brand_id', '=', self.id)],
            'context': {'default_brand_id': self.id},
        }

    def action_open_dashboard(self):
        self.ensure_one()
        if not self.dashboard_id:
            self._ensure_dashboard()
        return {
            'type': 'ir.actions.client',
            'tag': 'dashboard_vrtl_amcharts',
            'params': {
                'record': self.dashboard_id.id,
                'dashboard_name': self.dashboard_id.name,
            },
        }

    def action_sync_dashboard_users(self):
        """Recompute the dashboard user_ids from brand customers + agency users."""
        for brand in self:
            brand._sync_dashboard_users()
        return True

    def _sync_dashboard_users(self):
        self.ensure_one()
        if not self.dashboard_id:
            self._ensure_dashboard()
        users = self.env['res.users'].search([
            ('share', '=', True),
            ('partner_id.commercial_partner_id', '=', self.partner_id.commercial_partner_id.id),
        ]) | self.env['res.users'].search([
            ('share', '=', False),
            ('brand_ids', 'in', self.id),
        ])
        self.dashboard_id.write({'user_ids': [(6, 0, users.ids)]})
        return users

    def action_set_focus(self):
        """Set this brand as the session brand and open the brand workspace."""
        self.ensure_one()
        if self.env.user.share:
            raise ValidationError(_('Customer users cannot switch brands.'))
        from odoo.http import request
        request.session['social_brand_id'] = self.id
        return {
            'type': 'ir.actions.act_window',
            'name': self.name,
            'res_model': 'social.agency.document',
            'view_mode': 'list,form',
            'domain': [('brand_id', '=', self.id)],
            'context': {'default_brand_id': self.id},
        }
