# -*- coding: utf-8 -*-
# Vertel AB AGPL-3

from odoo import api, fields, models


class SocialPlannerDashboard(models.AbstractModel):
    """ Dashboard model providing computed fields for the dashboard view.
    Uses related/computed fields that lazy-load the data. """

    _name = 'social.planner.dashboard'
    _description = 'Social Planner Dashboard'

    # Active Plans
    active_plan_ids = fields.Many2many(
        'communication.plan',
        compute='_compute_active_plan_ids',
        string='Active Plans')

    # Unread Messages
    unread_message_ids = fields.Many2many(
        'social_marketing.message',
        compute='_compute_unread_message_ids',
        string='Unread Messages')

    # Pending Approvals
    pending_approval_ids = fields.Many2many(
        'social_marketing.post',
        compute='_compute_pending_approval_ids',
        string='Pending Approvals')

    # Top Competitors
    top_competitor_ids = fields.Many2many(
        'social_marketing.competitor',
        compute='_compute_top_competitor_ids',
        string='Top Competitors')

    # Recent Posts
    recent_post_ids = fields.Many2many(
        'social_marketing.post',
        compute='_compute_recent_post_ids',
        string='Recent Posts')

    @api.model
    def _compute_active_plan_ids(self):
        plans = self.env['communication.plan'].search([
            ('state', '=', 'active'),
        ], limit=6)
        self.active_plan_ids = plans

    @api.model
    def _compute_unread_message_ids(self):
        messages = self.env['social_marketing.message'].search([
            ('state', '=', 'unread'),
        ], limit=10, order='create_date desc')
        self.unread_message_ids = messages

    @api.model
    def _compute_pending_approval_ids(self):
        posts = self.env['social_marketing.post'].search([
            ('approval_state', '=', 'pending_approval'),
        ], limit=10)
        self.pending_approval_ids = posts

    @api.model
    def _compute_top_competitor_ids(self):
        competitors = self.env['social_marketing.competitor'].search([
            ('threat_level', 'in', ['high', 'critical']),
        ], limit=6, order='follower_count desc')
        self.top_competitor_ids = competitors

    @api.model
    def _compute_recent_post_ids(self):
        posts = self.env['social_marketing.post'].search([
            ('state', '!=', 'draft'),
        ], limit=10, order='create_date desc')
        self.recent_post_ids = posts
