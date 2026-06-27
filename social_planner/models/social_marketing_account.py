# -*- coding: utf-8 -*-
# Vertel AB AGPL-3

from odoo import models

_logger = __import__('logging').getLogger(__name__)


class SocialMarketingAccount(models.Model):
    """ Lägg till inbox-fetch hook på social_marketing.account.
    Varje plattformsmodul överskuggar _fetch_inbox_messages() för
    att hämta DMs/kommentarer via plattformens API. """

    _inherit = 'social_marketing.account'

    def _fetch_inbox_messages(self):
        """ Hämta meddelanden från plattformen.
        Överskuggas av plattformsmoduler.
        Returnerar antal nya meddelanden. """
        self.ensure_one()
        _logger.debug(
            "social_marketing.account._fetch_inbox_messages: "
            "account=%s platform=%s — no handler",
            self.display_name, self.media_type)
        return 0

    def _send_inbox_reply(self, message, body):
        """ Skicka svar via plattformens API.
        Överskuggas av plattformsmoduler.
        Returnerar True/False. """
        self.ensure_one()
        _logger.debug(
            "social_marketing.account._send_inbox_reply: "
            "account=%s platform=%s — no handler",
            self.display_name, self.media_type)
        return False
