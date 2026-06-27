# -*- coding: utf-8 -*-
from odoo import models

class SocialStreamPostFacebook(models.Model):
    _inherit = 'social_marketing.stream.post'

    # Facebook-specifika stream post fields hanteras via existing model
    # Author name: author_name (already in base)
    # Engagement: engagement (already in base)
    # External URL: external_url (already in base)
