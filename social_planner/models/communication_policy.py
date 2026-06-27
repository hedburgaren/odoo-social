# -*- coding: utf-8 -*-
# Vertel AB AGPL-3

from odoo import _, api, fields, models


class CommunicationPolicy(models.Model):
    """ Kommunikationspolicy — definierar *hur* organisationen kommunicerar.
    Policyn är grunden som styr all kommunikationsplanering, godkännandeflöden
    och AI-genererat innehåll. """

    _name = 'communication.policy'
    _description = 'Communication Policy'
    _order = 'name'

    name = fields.Char('Policy Name', required=True, translate=True)
    description = fields.Text('Description',
        help="Övergripande beskrivning av policyns syfte och omfattning.")
    active = fields.Boolean('Active', default=True)

    # Tonalitet & Varumärkesröst
    tone_of_voice = fields.Html('Tone of Voice',
        help="Riktlinjer för tonalitet — formell, personlig, humoristisk, etc.")
    brand_voice_guidelines = fields.Html('Brand Voice Guidelines',
        help="Specifik varumärkesröst — ord att använda/undvika, språkregler, stilguide.")

    # Publiceringsregler
    hashtag_policy = fields.Html('Hashtag Policy',
        help="Riktlinjer för hashtag-användning — varumärkesspecifika, bransch, max antal per post.")
    posting_frequency_max_daily = fields.Integer('Max Daily Posts',
        help="Max antal poster per kanal och dag. 0 = ingen gräns.",
        default=5)
    posting_frequency_max_weekly = fields.Integer('Max Weekly Posts',
        help="Max antal poster per kanal och vecka. 0 = ingen gräns.",
        default=20)
    image_guidelines = fields.Html('Image Guidelines',
        help="Riktlinjer för bilder — format, storlek, varumärkesfärger, alt-text-krav.")
    prohibited_content = fields.Text('Prohibited Content',
        help="Förbjudna ämnen, ord eller fraser — ett per rad. Poster som innehåller "
             "dessa flaggas automatiskt.")

    # Godkännandekedja
    approval_chain = fields.Json('Approval Chain',
        help="Stegkedja för godkännande. "
             "Ex: [{'role': 'creator', 'action': 'submit'}, "
             "{'role': 'approver', 'action': 'approve'}]")
    response_time_target = fields.Integer('Response Time Target',
        help="Målsvarstid i minuter för kommentarer/DM.",
        default=60)

    # Krisprotokoll
    crisis_response_protocol = fields.Html('Crisis Response Protocol',
        help="Protokoll för krishantering — eskalering, frysta kanaler, svarstider, "
             "kontaktpersoner.")

    # Metadata
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('archived', 'Archived'),
    ], string='Status', default='draft', required=True)
    version = fields.Integer('Version', default=1, readonly=True,
        help="Versionsnummer. Auto-inkrementeras vid ändring.")
    company_id = fields.Many2one('res.company', string='Company',
        default=lambda self: self.env.company)
    owner_id = fields.Many2one('res.users', string='Owner',
        default=lambda self: self.env.user,
        help="Ägare/ansvarig för policyn.")

    # Relationer
    plan_ids = fields.One2many('communication.plan', 'policy_id',
        string='Communication Plans',
        help="Planer som följer denna policy.")
    plan_count = fields.Integer('Number of Plans', compute='_compute_plan_count')

    @api.depends('plan_ids')
    def _compute_plan_count(self):
        for policy in self:
            policy.plan_count = len(policy.plan_ids)

    def write(self, vals):
        """ Auto-inkrementera version vid faktisk ändring av policy-innehåll. """
        policy_fields = [
            'tone_of_voice', 'brand_voice_guidelines', 'hashtag_policy',
            'posting_frequency_max_daily', 'posting_frequency_max_weekly',
            'image_guidelines', 'prohibited_content', 'approval_chain',
            'response_time_target', 'crisis_response_protocol',
        ]
        if any(field in vals for field in policy_fields):
            vals['version'] = self.version + 1
        return super().write(vals)

    def action_activate(self):
        self.write({'state': 'active'})

    def action_archive(self):
        self.write({'state': 'archived'})

    def action_draft(self):
        self.write({'state': 'draft'})
