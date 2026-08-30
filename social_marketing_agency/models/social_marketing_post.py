# Copyright (C) 2026 Vertel Sverige AB.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import json
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class SocialMarketingPost(models.Model):
    _name = 'social_marketing.post'
    """Post scoped to a brand, with a customer approval step."""

    _inherit = ['social_marketing.post', 'social.brand.focus.mixin']

    brand_id = fields.Many2one(
        'social.brand', string='Brand',
        default=lambda self: self._get_default_brand())

    # ── Reuse pool (level one) ───────────────────────────────────────────
    # Evergreen posts may go out again once their cooldown has passed. No
    # performance based selection here: the metrics that would drive it do
    # not exist yet. Order is oldest-reused-first.
    is_evergreen = fields.Boolean(
        'Evergreen', default=False,
        help="This post may be reused later.")
    reuse_cooldown_days = fields.Integer(
        'Reuse Cooldown (days)', default=30,
        help="Minimum number of days before this post may go out again.")
    last_reused_date = fields.Date('Last Reused', readonly=True, copy=False)

    # Customer approval step: internal approval hands the post to the
    # customer's users when the policy approval chain contains role 'customer'.
    approval_state = fields.Selection(
        selection_add=[('awaiting_customer', 'Awaiting Customer')],
        ondelete={'awaiting_customer': 'set default'})

    @api.model_create_multi
    def create(self, vals_list):
        """Ensure the UTM source name is derived from the post message.

        The post's ``_rec_name`` resolves to 'name' (utm.source.mixin wins
        the MRO over the template's 'message'), so the mixin would create
        a UTM source with a NULL name and hit a NOT NULL constraint.
        Pre-fill the name from the message before delegating.
        """
        for vals in vals_list:
            if not vals.get('source_id') and not vals.get('name'):
                content = vals.get('message')
                if content:
                    vals['name'] = self.env['utm.source']._generate_name(
                        self, content)
        return super().create(vals_list)

    # ── Customer approval helpers ────────────────────────────────────────

    def _policy_requires_customer_approval(self):
        """True when the policy approval chain has a role='customer' step."""
        self.ensure_one()
        if not self.policy_id or not self.policy_id.approval_chain:
            return False
        chain = self.policy_id.approval_chain
        if isinstance(chain, str):
            try:
                chain = json.loads(chain)
            except (json.JSONDecodeError, TypeError):
                return False
        if not isinstance(chain, list):
            return False
        return any(
            isinstance(step, dict) and step.get('role') == 'customer'
            for step in chain)

    def _check_customer_rights(self):
        """Raise unless the current user is a customer user of this brand."""
        self.ensure_one()
        if not self.env.user.has_group(
                'social_marketing_agency.group_social_customer_approver'):
            raise UserError(
                _('Only customer users can act on the customer approval step.'))
        if (self.brand_id and
                self.brand_id.partner_id.commercial_partner_id !=
                self.env.user.partner_id.commercial_partner_id):
            raise UserError(
                _('You can only approve or reject posts of your own brands.'))

    def _notify_customer_approval(self):
        """Create a TODO activity for every customer user of the brand."""
        self.ensure_one()
        if not self.brand_id:
            return
        group = self.env.ref(
            'social_marketing_agency.group_social_customer_approver')
        customer_users = self.env['res.users'].search([
            ('share', '=', True),
            ('groups_id', 'in', group.id),
            ('partner_id.commercial_partner_id', '=',
             self.brand_id.partner_id.commercial_partner_id.id),
        ])
        for user in customer_users:
            self.activity_schedule(
                'mail.mail_activity_data_todo',
                user_id=user.id,
                note=_('Please approve or reject the social media post '
                       '"%s" for your brand.', self.display_name))

    # ── Approval flow overrides ──────────────────────────────────────────

    def action_approve(self):
        """Internal approval; sends the post to customer approval if required."""
        res = super().action_approve()
        for post in self:
            if post._policy_requires_customer_approval():
                post.write({'approval_state': 'awaiting_customer'})
                post.message_post(
                    body=_('Post approved internally and sent to customer '
                           'approval.'),
                    message_type='notification',
                    subtype_xmlid='mail.mt_comment')
                post._notify_customer_approval()
        return res

    def _safe_message_post(self, **kwargs):
        """Post a chatter message, never letting mail delivery block the action.

        Customer actions (approve/reject) must succeed even when the
        notification email cannot be delivered (e.g. SMTP relay refuses a
        customer address); the notification is best-effort.
        """
        try:
            return self.message_post(**kwargs)
        except Exception:
            _logger.warning(
                'Chatter notification failed for %s (id %s)',
                self._name, self.ids, exc_info=True)
            return False

    def action_customer_approve(self):
        """Customer approval — the post becomes publishable."""
        self.ensure_one()
        self._check_customer_rights()
        if self.approval_state != 'awaiting_customer':
            raise UserError(
                _('Only posts awaiting customer approval can be approved '
                  'by the customer.'))
        self.write({'approval_state': 'approved'})
        self._safe_message_post(
            body=_('Post approved by customer %(user)s.',
                   user=self.env.user.name),
            message_type='notification',
            subtype_xmlid='mail.mt_comment')
        self.sudo().activity_feedback(['mail.mail_activity_data_todo'])
        return True

    def action_customer_reject(self, reason=False):
        """Customer rejection — back to rejected with a reason."""
        self.ensure_one()
        self._check_customer_rights()
        if self.approval_state != 'awaiting_customer':
            raise UserError(
                _('Only posts awaiting customer approval can be rejected '
                  'by the customer.'))
        self.write({
            'approval_state': 'rejected',
            'rejection_reason': reason or _('Rejected by customer'),
        })
        self._safe_message_post(
            body=_('Post rejected by customer %(user)s. Reason: %(reason)s',
                   user=self.env.user.name,
                   reason=self.rejection_reason),
            message_type='notification',
            subtype_xmlid='mail.mt_comment',
            partner_ids=[self.create_uid.partner_id.id])
        self.sudo().activity_feedback(['mail.mail_activity_data_todo'])
        return True

    def action_post(self):
        """Never publish a post that is still awaiting customer approval."""
        for post in self:
            if post.approval_state == 'awaiting_customer':
                raise UserError(
                    _('This post is awaiting customer approval and cannot '
                      'be published yet.'))
        return super().action_post()


    # ── Reuse pool helpers ───────────────────────────────────────────────

    def _reuse_reference_date(self):
        """Date the cooldown is counted from."""
        self.ensure_one()
        if self.last_reused_date:
            return self.last_reused_date
        if self.published_date:
            return self.published_date.date()
        return self.create_date.date()

    @api.model
    def _get_reusable_posts(self, brand, reference_date=None):
        """Posts of ``brand`` that may be reused, oldest-reused-first.

        Eligible means: evergreen, published, and at least
        ``reuse_cooldown_days`` days past the last time it went out. A post
        exactly on the cooldown boundary is eligible.
        """
        today = reference_date or fields.Date.context_today(self)
        posts = self.search([
            ('brand_id', '=', brand.id if brand else False),
            ('is_evergreen', '=', True),
            ('state', '=', 'posted'),
        ])
        eligible = posts.filtered(
            lambda post: (today - post._reuse_reference_date()).days
            >= post.reuse_cooldown_days)
        return eligible.sorted(key=lambda post: post._reuse_reference_date())

    def _mark_reused(self, reference_date=None):
        """Stamp the reuse date so the cooldown restarts."""
        self.write({
            'last_reused_date': reference_date
            or fields.Date.context_today(self),
        })
        return True
