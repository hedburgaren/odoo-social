# -*- coding: utf-8 -*-
# Vertel AB AGPL-3

from odoo import _, api, fields, models


class SocialMarketingListeningTopic(models.Model):
    """ Nyckelords-/hashtag-bevakning för social listening.
    Kopplas till social_marketing.stream för att övervaka specifika ämnen. """

    _name = 'social_marketing.listening.topic'
    _description = 'Social Listening Topic'
    _order = 'name'

    name = fields.Char('Topic Name', required=True)
    active = fields.Boolean('Active', default=True)

    keywords = fields.Text('Keywords',
        help="Keywords or phrases to monitor, one per line. "
             "Supports hashtags with # prefix.")
    exclude_keywords = fields.Text('Exclude Keywords',
        help="Keywords to exclude, one per line.")

    # Kopplingar
    policy_id = fields.Many2one('communication.policy', string='Policy',
        help="Link to communication policy for crisis detection.")
    stream_ids = fields.Many2many('social_marketing.stream', string='Streams',
        help="Streams to apply this listening topic to.")
    company_id = fields.Many2one('res.company', string='Company',
        default=lambda self: self.env.company)

    # Statistik
    mention_count = fields.Integer('Mentions (24h)', compute='_compute_mention_count')
    last_checked = fields.Datetime('Last Checked')

    @api.depends('stream_ids')
    def _compute_mention_count(self):
        for topic in self:
            # TODO: Implementera faktisk count från stream_posts som matchar keywords
            topic.mention_count = 0
