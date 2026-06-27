# -*- coding: utf-8 -*-
from odoo import fields, models


class SocialMarketingPostTemplate(models.Model):
    _inherit = 'social_marketing.post.template'

    facebook_message = fields.Text('Facebook Message')
    facebook_image_ids = fields.Many2many('ir.attachment', string='Facebook Images')
