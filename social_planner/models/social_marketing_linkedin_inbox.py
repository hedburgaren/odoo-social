# -*- coding: utf-8 -*-
# Vertel Sverige AB AGPL-3

from odoo import models

_logger = __import__('logging').getLogger(__name__)


class SocialMarketingAccountLinkedIn(models.Model):
    """ LinkedIn inbox integration — fetch and reply to DMs.
    Utökar social_marketing_linkedin's account model. """

    _inherit = 'social_marketing.account'

    def _fetch_inbox_messages(self):
        """ Hämta LinkedIn-meddelanden via LinkedIn API.
        NOTE: Full implementation requires LinkedIn Marketing API access
        with the 'r_member_social' or 'w_member_social' permission. """
        self.ensure_one()
        if self.media_type != 'linkedin':
            return super()._fetch_inbox_messages()

        # LinkedIn API implementation would go here
        # Currently returns 0 as LinkedIn DM API requires special approval
        _logger.info(
            "LinkedIn inbox fetch for account %s: "
            "LinkedIn DM API requires special partner approval.",
            self.display_name)
        return 0

    def _send_inbox_reply(self, message, body):
        """ Skicka svar via LinkedIn API. """
        self.ensure_one()
        if self.media_type != 'linkedin':
            return super()._send_inbox_reply(message, body)

        # LinkedIn Messaging API implementation
        # POST /v2/messages
        # Requires 'w_member_social' scope
        _logger.info(
            "LinkedIn reply for message %s: "
            "LinkedIn DM API requires special partner approval.",
            message.id)
        return False
