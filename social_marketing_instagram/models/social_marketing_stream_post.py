# -*- coding: utf-8 -*-
from odoo import models

class SocialStreamPostInstagram(models.Model):
    _inherit = 'social_marketing.stream.post'

    # Instagram-specifika stream post fields hanteras via existing model
