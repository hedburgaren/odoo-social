from odoo import models, fields, api, _


class DiscussChannel(models.Model):
    _inherit = 'discuss.channel'

    social_account_id = fields.Many2one('social_marketing.account', string="Social Account")

