# -*- coding: utf-8 -*-
# Vertel AB AGPL-3

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class CommunicationPlanLine(models.Model):
    """ En planerad post-rad i en kommunikationsplan. Varje rad representerar
    en planerad publicering på en specifik kanal med tema och innehållstyp. """

    _name = 'communication.plan.line'
    _description = 'Communication Plan Line'
    _order = 'date, time, sequence, id'

    plan_id = fields.Many2one('communication.plan', string='Plan',
        required=True, ondelete='cascade')
    sequence = fields.Integer('Sequence', default=10)

    # Kanal & Innehållstyp
    channel = fields.Selection([
        ('linkedin', 'LinkedIn'),
        ('facebook', 'Facebook'),
        ('instagram', 'Instagram'),
        ('twitter', 'Twitter / X'),
        ('youtube', 'YouTube'),
        ('multi', 'Multi-platform'),
    ], string='Channel', required=True, default='linkedin')
    content_type = fields.Selection([
        ('post', 'Post'),
        ('story', 'Story'),
        ('reel', 'Reel'),
        ('video', 'Video'),
        ('article', 'Article'),
        ('poll', 'Poll'),
    ], string='Content Type', required=True, default='post')

    # Schemaläggning
    date = fields.Date('Date', required=True, default=fields.Date.today)
    time = fields.Float('Time',
        help="Planerad tid i timmar (ex: 14.5 = 14:30)")

    # Innehåll
    theme = fields.Char('Theme',
        help="Tema för posten, t.ex. 'Produktlansering' eller 'Kundcase'.")
    notes = fields.Text('Notes',
        help="Interna anteckningar — syns inte i den publicerade posten.")

    # Status
    status = fields.Selection([
        ('planned', 'Planned'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='planned', required=True, tracking=True)

    # Koppling till poster
    post_ids = fields.One2many('social_marketing.post', 'plan_line_id',
        string='Posts', copy=False)
    post_count = fields.Integer('Number of Posts', compute='_compute_post_count')

    # Metadata
    company_id = fields.Many2one(related='plan_id.company_id', store=True)

    @api.depends('post_ids')
    def _compute_post_count(self):
        for line in self:
            line.post_count = len(line.post_ids)

    def action_create_post(self):
        """ Skapa en social_marketing.post från denna planeringsrad.
        Posten förifylls med data från planen och policyn. """
        self.ensure_one()

        # Hämta policy från planen för compliance check
        policy = self.plan_id.policy_id

        # Kör policy compliance check (om policyn är aktiv)
        if policy.state == 'active':
            # Kontrollera posting frequency
            existing_posts_today = self.env['social_marketing.post'].search_count([
                ('plan_line_id.plan_id', '=', self.plan_id.id),
                ('plan_line_id.date', '=', self.date),
            ])
            if policy.posting_frequency_max_daily > 0 and existing_posts_today >= policy.posting_frequency_max_daily:
                raise UserError(_(
                    'Maximum daily posts (%(max)s) reached for this plan. '
                    'Please adjust the schedule or the policy.',
                    max=policy.posting_frequency_max_daily
                ))

        # Bestäm media_type från channel
        channel_media_map = {
            'linkedin': 'linkedin',
            'facebook': 'facebook',
            'instagram': 'instagram',
            'twitter': 'twitter',
            'youtube': 'youtube',
        }

        # Hitta konton för vald kanal
        media_type = channel_media_map.get(self.channel)
        account_ids = self.env['social_marketing.account'].search([
            ('media_type', '=', media_type),
        ])

        if not account_ids:
            raise UserError(_(
                'No social accounts found for channel "%(channel)s". '
                'Please add an account for this channel first.',
                channel=self.channel
            ))

        # Skapa posten
        post = self.env['social_marketing.post'].create({
            'plan_line_id': self.id,
            'account_ids': [(6, 0, account_ids.ids)],
            # Förifyllda fält kommer från template/inherit
        })

        # Uppdatera status
        self.status = 'in_progress'

        return {
            'type': 'ir.actions.act_window',
            'name': _('Create Post'),
            'res_model': 'social_marketing.post',
            'res_id': post.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_cancel(self):
        self.write({'status': 'cancelled'})

    def action_replan(self):
        self.write({'status': 'planned'})

    def _check_line_completion(self):
        """ Called when a post is completed. If all posts on this line are posted,
        mark the line as completed. """
        for line in self:
            if line.post_ids and all(
                p.state == 'posted' for p in line.post_ids
            ):
                line.status = 'completed'
                line.plan_id._check_plan_completion()
