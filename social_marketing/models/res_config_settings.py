# coding: utf-8
# Vertel AB AGPL-3

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    module_social_marketing_demo = fields.Boolean('Enable Demo Mode', groups="base.group_system")
