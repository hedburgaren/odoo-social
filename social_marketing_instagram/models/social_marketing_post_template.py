# -*- coding: utf-8 -*-
from odoo import fields, models


class SocialMarketingPostTemplate(models.Model):
    _inherit = 'social_marketing.post.template'

    instagram_message = fields.Text('Instagram Message')
    instagram_image_ids = fields.Many2many('ir.attachment', string='Instagram Images')
