# -*- coding: utf-8 -*-
# Vertel AB AGPL-3

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class SocialMarketingMessage(models.Model):
    """ Unified inbox — samlar DM:s, kommentarer och mentions från alla
    anslutna sociala plattformar i en gemensam vy.

    Varje plattformsmodul (social_marketing_linkedin, _facebook, _instagram)
    implementerar _fetch_inbox_messages() för att hämta meddelanden. """

    _name = 'social_marketing.message'
    _description = 'Social Message (Unified Inbox)'
    _order = 'create_date desc, id desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_names_search = ['from_name', 'body']

    # Avsändare
    from_name = fields.Char('From', required=True)
    from_handle = fields.Char('Handle')
    from_avatar_url = fields.Char('Avatar URL')

    # Meddelande
    body = fields.Text('Message', required=True)
    external_id = fields.Char('External ID',
        help="Platform-specific message ID for deduplication.")
    external_url = fields.Char('External URL',
        help="Link to the message on the platform.")

    # Plattform & Typ
    media_type = fields.Selection([
        ('linkedin', 'LinkedIn'),
        ('facebook', 'Facebook'),
        ('instagram', 'Instagram'),
        ('twitter', 'Twitter / X'),
        ('youtube', 'YouTube'),
    ], string='Platform', required=True)
    message_type = fields.Selection([
        ('dm', 'Direct Message'),
        ('comment', 'Comment'),
        ('mention', 'Mention'),
        ('reaction', 'Reaction'),
        ('other', 'Other'),
    ], string='Type', default='dm', required=True)
    parent_id = fields.Many2one('social_marketing.message', string='Parent',
        ondelete='cascade',
        help="Parent message for threaded conversations.")
    child_ids = fields.One2many('social_marketing.message', 'parent_id',
        string='Replies')

    # Konto
    social_account_id = fields.Many2one('social_marketing.account',
        string='Social Account', required=True, ondelete='cascade')

    # Status
    state = fields.Selection([
        ('unread', 'Unread'),
        ('read', 'Read'),
        ('replied', 'Replied'),
        ('archived', 'Archived'),
    ], string='Status', default='unread', required=True, tracking=True)
    replied_via_odoo = fields.Boolean('Replied via Odoo',
        help="This message was replied to from within Odoo's unified inbox.")
    is_incoming = fields.Boolean('Incoming', default=True,
        help="Incoming messages from external platforms vs outgoing replies sent from Odoo.")

    # Tilldelning
    assigned_to = fields.Many2one('res.users', string='Assigned To', tracking=True)
    assignment_note = fields.Text('Assignment Note')

    # Taggning
    tag_ids = fields.Many2many('social_marketing.message.tag', string='Tags')
    priority = fields.Selection([
        ('0', 'Normal'),
        ('1', 'Low'),
        ('2', 'High'),
        ('3', 'Urgent'),
    ], string='Priority', default='0')

    # Metadata
    company_id = fields.Many2one(related='social_account_id.company_id',
        store=True, string='Company')
    response_time_minutes = fields.Integer('Response Time (min)',
        compute='_compute_response_time', store=True,
        help="Minutes between incoming message and first reply.")

    @api.depends('create_date', 'child_ids.create_date', 'state')
    def _compute_response_time(self):
        for msg in self:
            if msg.state == 'replied' and msg.child_ids:
                replies = msg.child_ids.filtered(lambda r: not r.is_incoming)
                if replies:
                    first_reply = min(replies.mapped('create_date'))
                    delta = first_reply - msg.create_date
                    msg.response_time_minutes = int(delta.total_seconds() / 60)

    def action_mark_read(self):
        self.write({'state': 'read'})

    def action_mark_unread(self):
        self.write({'state': 'unread'})

    def action_archive(self):
        self.write({'state': 'archived'})

    def action_assign_to_me(self):
        self.write({'assigned_to': self.env.user.id, 'state': 'read'})

    def action_reply(self, body):
        """ Skicka svar via plattformens API. Varje plattformsmodul
        implementerar _send_reply() för att hantera API-anropet. """
        self.ensure_one()
        if not body:
            raise UserError(_('Reply body is required.'))

        # Skicka via plattforms-API
        success = self._send_reply_platform(body)

        # Skapa reply-meddelande i Odoo (utgående)
        reply = self.env['social_marketing.message'].create({
            'from_name': self.env.user.name,
            'from_handle': 'odoo',
            'body': body,
            'media_type': self.media_type,
            'message_type': self.message_type,
            'social_account_id': self.social_account_id.id,
            'state': 'read',
            'replied_via_odoo': True,
            'is_incoming': False,
            'parent_id': self.id,
        })

        self.write({'state': 'replied'})

        if not success:
            reply.body = f"[FAILED TO SEND] {body}"

        # Notifiera i chatter
        self.message_post(
            body=_('Reply sent by %(user)s.', user=self.env.user.name),
            message_type='notification')

        return reply

    def _send_reply_platform(self, body):
        """ Överskuggas av plattformsmoduler för att skicka svar via API.
        Returnerar True om skickat, False om misslyckat. """
        self.ensure_one()
        if self.social_account_id:
            return self.social_account_id._send_inbox_reply(self, body)
        _logger = __import__('logging').getLogger(__name__)
        _logger.info(
            "social_marketing.message._send_reply_platform: "
            "platform=%s message_id=%s — no account",
            self.media_type, self.id)
        return False

    def action_open_external(self):
        """ Öppna meddelandet på plattformen. """
        self.ensure_one()
        if self.external_url:
            return {
                'type': 'ir.actions.act_url',
                'url': self.external_url,
                'target': 'new',
            }
        raise UserError(_('No external URL available for this message.'))

    @api.model
    def fetch_all_inbox(self):
        """ Hämta meddelanden från alla aktiva plattformar.
        Anropar varje plattforms _fetch_inbox_messages(). """
        accounts = self.env['social_marketing.account'].search([
            ('active', '=', True),
            ('is_media_disconnected', '=', False),
        ])
        new_count = 0
        for account in accounts:
            try:
                count = account._fetch_inbox_messages()
                new_count += count
            except Exception:
                _logger = __import__('logging').getLogger(__name__)
                _logger.exception(
                    "Failed to fetch inbox for account %s", account.display_name)
        return new_count

    @api.model
    def _get_unread_count(self):
        """ Antal olästa meddelanden för aktuell användare. """
        return self.search_count([
            ('state', '=', 'unread'),
            '|',
            ('assigned_to', '=', self.env.user.id),
            ('assigned_to', '=', False),
        ])


class SocialMarketingMessageTag(models.Model):
    _name = 'social_marketing.message.tag'
    _description = 'Message Tag'
    _order = 'name'

    name = fields.Char('Tag', required=True)
    color = fields.Integer('Color', default=0)
