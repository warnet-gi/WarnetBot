OWNER_ID = 278821688894947328  # Change this value with your discord ID
PRIVATE_DEV_GUILD_ID = 835725357423919104  # Change this value with your own private guild for bot testing
WARNET_GUILD_ID = 761644411486339073

# These are administrator role on Warnet guild
ADMINISTRATOR_ROLE_ID = {
    'admin': '761650159833841674',
    'mod': '761662280541798421'
}
STAFF_ROLE_ID = 951170972671701063

DEFAULT = {
    'guild_id': WARNET_GUILD_ID,
    'prefix': ['war!', 'War!', 'WAR!'],
}

class TCGConfig:
    TCG_TITLE_ROLE_ID = (
        1051867676202512415,  # Novice Duelist
        1051865453208801361,  # Expert Duelist
        1051865448980942948,  # Master Duelist
        1051865444073611365,  # Immortal Duelist
    )
    TCG_EVENT_STAFF_ROLE_ID = 977488765234855986
    TCG_MATCH_REPORT_CHANNEL_ID = 1053525411725836428
    TCG_MATCH_LOG_CHANNEL_ID = 1053525862982631516
    TCG_TITLE_EMOJI = {
        TCG_TITLE_ROLE_ID[0]: '<:NoviceDuelist:1052440393461022760>',
        TCG_TITLE_ROLE_ID[1]: '<:ExpertDuelist:1052440396489314304>',
        TCG_TITLE_ROLE_ID[2]: '<:MasterDuelist:1052440400822018078>',
        TCG_TITLE_ROLE_ID[3]: '<:ImmortalDuelist:1052440404135518228>'
    }
