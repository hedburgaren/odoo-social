# -*- coding: utf-8 -*-
from odoo import fields, models

_logger = __import__('logging').getLogger(__name__)


class SocialMarketingAccountInstagram(models.Model):
    _inherit = 'social_marketing.account'

    def _fetch_inbox_messages(self):
        self.ensure_one()
        if self.media_type != 'instagram':
            return super()._fetch_inbox_messages()

        # Instagram Graph API — conversations/messages edge
        # GET /{ig-user-id}/conversations?fields=messages{from,message,timestamp}
        _logger.info("Instagram inbox fetch: account=%s", self.display_name)
        return 0

    def _send_inbox_reply(self, message, body):
        self.ensure_one()
        if self.media_type != 'instagram':
            return super()._send_inbox_reply(message, body)

        # POST /{ig-user-id}/messages
        _logger.info("Instagram reply: message=%s", message.id)
        return False
