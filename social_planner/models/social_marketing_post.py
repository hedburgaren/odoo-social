# -*- coding: utf-8 -*-
# Vertel AB AGPL-3

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class SocialMarketingPost(models.Model):
    """ Ärv social_marketing.post (Vertel CE) med kommunikationsplanering,
    policy-koppling, godkännandeflöde och compliance-validering. """

    _inherit = 'social_marketing.post'

    # Koppling till plan och policy
    plan_line_id = fields.Many2one('communication.plan.line',
        string='Plan Line', ondelete='set null', tracking=True,
        help="Koppling till planeringsraden i kommunikationsplanen.")
    plan_id = fields.Many2one(related='plan_line_id.plan_id',
        string='Plan', store=True)
    policy_id = fields.Many2one(related='plan_line_id.plan_id.policy_id',
        string='Policy', store=True)

    # Godkännandeflöde
    approval_state = fields.Selection([
        ('draft', 'Draft'),
        ('pending_approval', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ], string='Approval Status', default='draft', required=True, tracking=True)
    reviewer_id = fields.Many2one('res.users', string='Reviewer',
        tracking=True)
    rejection_reason = fields.Text('Rejection Reason',
        help="Anledning till att posten avvisades.")

    # Policy compliance
    compliance_check_passed = fields.Boolean('Compliance Check Passed',
        default=False)
    compliance_warnings = fields.Text('Compliance Warnings',
        help="Varningar från policy-compliance-kontrollen.")

    # AI-generering
    ai_generated = fields.Boolean('AI Generated', default=False,
        help="Innehållet genererades av AI.")
    ai_prompt = fields.Text('AI Prompt',
        help="Prompten som användes för AI-generering.")

    def action_submit_for_approval(self):
        """ Skicka posten för godkännande. Kör policy compliance check först. """
        self.ensure_one()
        if self.approval_state not in ('draft', 'rejected'):
            raise UserError(_('Only draft or rejected posts can be submitted for approval.'))

        # Kör compliance check
        warnings = self._check_policy_compliance()
        if warnings:
            self.compliance_warnings = '\n'.join(warnings)
            self.compliance_check_passed = False
        else:
            self.compliance_warnings = False
            self.compliance_check_passed = True

        # Bestäm reviewer från policy.approval_chain
        self._assign_reviewer_from_policy()

        self.approval_state = 'pending_approval'

        # Notifiera reviewer via activity
        if self.reviewer_id:
            self.activity_schedule(
                'mail.mail_activity_data_todo',
                user_id=self.reviewer_id.id,
                note=_('Please review and approve/reject the social media post "%(post)s" for plan "%(plan)s".',
                       post=self.display_name, plan=self.plan_id.name)
            )
        # Notifiera creator via chatter
        self.message_post(
            body=_('Post submitted for approval. Reviewer: %(reviewer)s',
                   reviewer=self.reviewer_id.name if self.reviewer_id else 'Not assigned'),
            message_type='notification',
            subtype_xmlid='mail.mt_comment')

    def _assign_reviewer_from_policy(self):
        """ Tilldela reviewer baserat på policy.approval_chain JSON.
        Exempel på approval_chain:
        [{"role": "creator", "action": "submit"},
         {"role": "approver", "action": "approve", "user_id": 3}]
        Om user_id är specificerad, används den. Annars söks användare med approver-gruppen."""
        self.ensure_one()
        if not self.policy_id or not self.policy_id.approval_chain:
            return

        import json
        try:
            chain = self.policy_id.approval_chain
            if isinstance(chain, str):
                chain = json.loads(chain)
        except (json.JSONDecodeError, TypeError):
            return

        if not isinstance(chain, list):
            return

        # Hitta approver-steget
        for step in chain:
            if isinstance(step, dict) and step.get('role') == 'approver':
                if step.get('user_id'):
                    self.reviewer_id = step['user_id']
                    return
                # Annars hitta första användaren med approver-gruppen
                approver = self.env['res.users'].search([
                    ('groups_id', 'in', self.env.ref('social_planner.group_social_content_approver').id),
                    ('share', '=', False),
                ], limit=1)
                if approver:
                    self.reviewer_id = approver.id
                return

    def action_approve(self):
        """ Godkänn posten — den kan nu publiceras. """
        self.ensure_one()
        if self.approval_state != 'pending_approval':
            raise UserError(_('Only posts pending approval can be approved.'))
        self.approval_state = 'approved'
        self.message_post(
            body=_('Post approved by %(user)s.', user=self.env.user.name),
            message_type='notification',
            subtype_xmlid='mail.mt_comment')
        # Markera aktiviteten som klar
        self.activity_feedback(['mail.mail_activity_data_todo'])

    def action_reject(self, reason=False):
        """ Avvisa posten — tillbaka till draft med kommentar. """
        self.ensure_one()
        if self.approval_state != 'pending_approval':
            raise UserError(_('Only posts pending approval can be rejected.'))
        self.approval_state = 'rejected'
        if reason:
            self.rejection_reason = reason
        self.message_post(
            body=_('Post rejected by %(user)s. Reason: %(reason)s',
                   user=self.env.user.name,
                   reason=self.rejection_reason or 'No reason provided'),
            message_type='notification',
            subtype_xmlid='mail.mt_comment',
            partner_ids=[self.create_uid.partner_id.id])
        # Markera aktiviteten som klar
        self.activity_feedback(['mail.mail_activity_data_todo'])

    def action_post(self):
        """ Överskugga action_post för att kräva godkännande (om policyn kräver det). """
        if self.policy_id and self.policy_id.state == 'active':
            if self.approval_state not in ('approved', 'draft'):
                raise UserError(_(
                    'This post must be approved before publishing. '
                    'Current status: %(status)s',
                    status=self.approval_state
                ))
        return super().action_post()

    def _check_policy_compliance(self):
        """ Validera posten mot communication.policy. Returnerar lista med varningar. """
        self.ensure_one()
        warnings = []

        if not self.policy_id or self.policy_id.state != 'active':
            return warnings

        policy = self.policy_id

        # 1. Kontrollera prohibited_content
        if policy.prohibited_content and self.message:
            prohibited_words = [
                w.strip().lower()
                for w in policy.prohibited_content.split('\n')
                if w.strip()
            ]
            message_lower = self.message.lower()
            found_words = [w for w in prohibited_words if w in message_lower]
            if found_words:
                warnings.append(_(
                    'Message contains prohibited content: %(words)s',
                    words=', '.join(found_words)
                ))

        # 2. Kontrollera posting frequency (om plan_line finns)
        if policy.posting_frequency_max_daily > 0 and self.plan_line_id:
            existing_count = self.search_count([
                ('plan_line_id.plan_id', '=', self.plan_line_id.plan_id.id),
                ('plan_line_id.date', '=', self.plan_line_id.date),
                ('id', '!=', self.id),
            ])
            if existing_count >= policy.posting_frequency_max_daily:
                warnings.append(_(
                    'Maximum daily posts (%(max)s) exceeded for this plan.',
                    max=policy.posting_frequency_max_daily
                ))

        # 3. Kontrollera hashtag-policy
        # TODO: Implementera hashtag-validering mot policyn

        # 4. Bildanalys — görs via AI i Fas 3
        # TODO: Implementera AI-bildanalys

        return warnings

    def write(self, vals):
        res = super().write(vals)
        if vals.get('state') == 'posted':
            for post in self:
                if post.plan_line_id:
                    post.plan_line_id._check_line_completion()
        return res

    # --- AI Integration ---

    def action_ai_generate(self):
        """ Generera innehåll med AI. """
        self.ensure_one()
        ai_helper = self.env['social.planner.ai']
        success = ai_helper.generate_post_content(self.id)
        if success:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('AI Content Generated'),
                    'message': _('Content has been generated and filled into the post.'),
                    'type': 'success',
                    'sticky': False,
                }
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('AI Generation Failed'),
                    'message': _('Could not generate content. Make sure an AI agent is configured.'),
                    'type': 'warning',
                    'sticky': True,
                }
            }

    def action_ai_suggest_hashtags(self):
        """ Föreslå hashtags med AI. """
        self.ensure_one()
        ai_helper = self.env['social.planner.ai']
        hashtags = ai_helper.suggest_hashtags(self.id)
        if hashtags:
            current = self.message or ''
            new_message = current + '\n\n' + ' '.join(hashtags)
            self.write({'message': new_message})

    def action_ai_analyze_sentiment(self):
        """ Analysera sentiment för postens innehåll. """
        self.ensure_one()
        if not self.message:
            return
        ai_helper = self.env['social.planner.ai']
        result = ai_helper.analyze_sentiment(self.message)
        self.message_post(
            body=_('AI Sentiment Analysis: %(sentiment)s (score: %(score).2f)',
                   sentiment=result['sentiment'], score=result['score']),
            message_type='notification')
