# -*- coding: utf-8 -*-
from odoo import models

_logger = __import__('logging').getLogger(__name__)


class SocialMarketingAccountFacebook(models.Model):
    _inherit = 'social_marketing.account'

    def _fetch_inbox_messages(self):
        self.ensure_one()
        if self.media_type != 'facebook':
            return super()._fetch_inbox_messages()

        # Facebook Graph API — conversations edge
        # GET /{page-id}/conversations?fields=messages{from,message,created_time}
        _logger.info("Facebook inbox fetch: account=%s", self.display_name)
        # TODO: Implement Facebook Messenger API integration
        return 0

    def _send_inbox_reply(self, message, body):
        self.ensure_one()
        if self.media_type != 'facebook':
            return super()._send_inbox_reply(message, body)

        # POST /{page-id}/messages
        # Body: {recipient: {id: sender_psid}, message: {text: body}}
        _logger.info("Facebook reply: message=%s", message.id)
        # TODO: Implement Facebook Messenger API send
        return False
