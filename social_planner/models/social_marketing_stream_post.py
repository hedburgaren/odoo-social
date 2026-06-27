# -*- coding: utf-8 -*-
# Vertel AB AGPL-3

from odoo import _, api, fields, models


class SocialMarketingStreamPost(models.Model):
    """ Ärv social_marketing.stream.post för AI-sentimentanalys
    och auto-moderation kopplat till policy. """

    _inherit = 'social_marketing.stream.post'

    sentiment = fields.Selection([
        ('positive', 'Positive'),
        ('neutral', 'Neutral'),
        ('negative', 'Negative'),
    ], string='Sentiment', default='neutral', tracking=True)
    sentiment_score = fields.Float('Sentiment Score', digits=(3, 2),
        help="AI sentiment score: 0.0 (very negative) → 1.0 (very positive).")
    needs_review = fields.Boolean('Needs Review',
        help="Flagged for manual review (negative sentiment, potential crisis).")
    policy_flag = fields.Boolean('Policy Flag',
        help="Content flagged by communication policy rules (crisis keywords, etc.).")

    def action_analyze_sentiment(self):
        """ Analysera sentiment för detta stream-post-meddelande. """
        ai_helper = self.env['social.planner.ai']
        for post in self:
            message = post.message or ''
            if not message:
                continue
            result = ai_helper.analyze_sentiment(message)
            post.write({
                'sentiment': result.get('sentiment', 'neutral'),
                'sentiment_score': result.get('score', 0.0),
                'needs_review': result.get('sentiment') == 'negative',
            })

    def action_check_policy(self):
        """ Kontrollera om stream-posten flaggas av någon aktiv policy. """
        policies = self.env['communication.policy'].search([
            ('state', '=', 'active'),
            ('prohibited_content', '!=', False),
        ])
        for post in self:
            message = (post.message or '').lower()
            flagged = False
            for policy in policies:
                if not policy.prohibited_content:
                    continue
                prohibited = [
                    w.strip().lower()
                    for w in policy.prohibited_content.split('\n')
                    if w.strip()
                ]
                if any(w in message for w in prohibited):
                    flagged = True
                    break
            post.policy_flag = flagged
            if flagged:
                post.needs_review = True
