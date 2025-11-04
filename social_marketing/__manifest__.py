# -*- coding: utf-8 -*-
# Vertel AB AGPL-3

{
    'name': 'Social Marketing',
    'category': 'Marketing/Social Marketing',
    'summary': 'Manage your social marketing',
    'version': '1.1',
    'description': """Manage your social marketing """,
    'website': 'https://vertel.se/app/odoo-social',
    'depends': ['web', 'mail','link_tracker'],
    'data': [
        'security/social_marketing_security.xml',
        'security/ir.model.access.csv',
        'data/ir_cron_data.xml',
        # ~ 'views/social_marketing_menu_views.xml',
        'views/social_marketing_account_views.xml',
        'views/social_marketing_post_template_views.xml',
        'views/social_marketing_post_views.xml',
        'views/res_config_settings_views.xml',
        'views/utm_campaign_views.xml',
        # ~ 'views/social_marketing_templates.xml'
    ],
    'demo': [
        'data/social_marketing_demo.xml'
    ],
    'application': True,
    'installable': True,
    'license': 'AGPL-3',
}
