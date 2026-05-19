"""Categorias pré-definidas de domínios para políticas de sites.

Espelha 1:1 a constante `App\\Models\\SitePolicy::CATEGORIES` do projeto Laravel
original (divsystem-app). Manter os domínios sincronizados com aquele projeto.
"""
from __future__ import annotations

SITE_CATEGORIES: dict[str, dict] = {
    "redes_sociais": {
        "label": "Redes Sociais",
        "icon": "users",
        "domains": [
            # Facebook (Meta)
            "facebook.com", "www.facebook.com", "m.facebook.com",
            "web.facebook.com", "touch.facebook.com", "mobile.facebook.com",
            "fb.com", "www.fb.com", "fb.watch", "fb.me", "fb.gg",
            "facebook.net", "fbcdn.net", "fbsbx.com",
            "fbcdn.com", "fbpigeon.com", "accountkit.com",
            # Instagram
            "instagram.com", "www.instagram.com", "i.instagram.com",
            "l.instagram.com", "about.instagram.com",
            "ig.me", "ig.com",
            "cdninstagram.com",
            # Twitter/X
            "twitter.com", "www.twitter.com", "mobile.twitter.com",
            "x.com", "www.x.com",
            "t.co", "pic.twitter.com",
            "twimg.com", "pbs.twimg.com", "abs.twimg.com",
            "tweetdeck.com",
            # TikTok
            "tiktok.com", "www.tiktok.com", "m.tiktok.com",
            "vm.tiktok.com", "vt.tiktok.com",
            "tiktokcdn.com", "tiktokv.com",
            "musical.ly", "muscdn.com",
            "isnssdk.com", "byteoversea.com", "ibytedtos.com",
            # LinkedIn
            "linkedin.com", "www.linkedin.com",
            "lnkd.in", "licdn.com",
            # Reddit
            "reddit.com", "www.reddit.com", "old.reddit.com", "new.reddit.com",
            "redd.it", "i.redd.it", "v.redd.it",
            "redditmedia.com", "redditstatic.com",
            # Threads (Meta)
            "threads.net", "www.threads.net",
            # Pinterest
            "pinterest.com", "www.pinterest.com", "br.pinterest.com",
            "pin.it", "pinimg.com",
            # Snapchat
            "snapchat.com", "www.snapchat.com",
            "snap.com", "sc-cdn.net",
        ],
    },
    "streaming": {
        "label": "Streaming",
        "icon": "play",
        "domains": [
            # YouTube
            "youtube.com", "www.youtube.com", "m.youtube.com",
            "youtu.be", "youtube-nocookie.com",
            "youtubei.googleapis.com", "youtube.googleapis.com",
            "yt.be", "ytimg.com", "i.ytimg.com",
            "yt3.ggpht.com", "yt3.googleusercontent.com",
            "googlevideo.com",
            # Netflix
            "netflix.com", "www.netflix.com",
            "nflxvideo.net", "nflximg.net", "nflximg.com",
            "nflxso.net", "nflxext.com",
            # Twitch
            "twitch.tv", "www.twitch.tv", "m.twitch.tv",
            "clips.twitch.tv", "static.twitchcdn.net",
            "jtvnw.net", "ttvnw.net",
            # Spotify
            "spotify.com", "open.spotify.com", "www.spotify.com",
            "scdn.co", "spotifycdn.com",
            "i.scdn.co", "mosaic.scdn.co",
            # Amazon Prime Video
            "primevideo.com", "www.primevideo.com",
            "aiv-cdn.net", "aiv-delivery.net",
            # Globoplay
            "globoplay.globo.com", "globoplay.com.br",
            # Disney+
            "disneyplus.com", "www.disneyplus.com",
            "disney-plus.net", "bamgrid.com", "dssott.com",
            # HBO Max
            "max.com", "www.max.com", "hbomax.com",
            # Paramount+
            "paramountplus.com", "www.paramountplus.com",
            # Deezer
            "deezer.com", "www.deezer.com",
        ],
    },
    "jogos": {
        "label": "Jogos",
        "icon": "puzzle-piece",
        "domains": [
            # Steam
            "store.steampowered.com", "steampowered.com", "steamcommunity.com",
            "steamstatic.com", "steamcontent.com", "steamgames.com",
            # Epic Games
            "epicgames.com", "www.epicgames.com",
            "epicgames.dev", "unrealengine.com",
            # Roblox
            "roblox.com", "www.roblox.com",
            "rbxcdn.com", "rbx.com",
            # Miniclip / Friv
            "miniclip.com", "www.miniclip.com",
            "friv.com", "www.friv.com",
            # Outros jogos populares
            "leagueoflegends.com", "riotgames.com",
            "ea.com", "origin.com",
            "blizzard.com", "battle.net",
            "garena.com",
            "poki.com", "www.poki.com",
            "jogos360.com.br", "clickjogos.com.br",
        ],
    },
    "mensagens": {
        "label": "Mensagens",
        "icon": "chat-bubble-left-right",
        "domains": [
            # WhatsApp (Meta)
            "web.whatsapp.com", "whatsapp.com", "www.whatsapp.com",
            "whatsapp.net", "wa.me",
            # Telegram
            "telegram.org", "web.telegram.org", "www.telegram.org",
            "telegram.me", "t.me", "tdesktop.com",
            "telesco.pe",
            # Discord
            "discord.com", "www.discord.com",
            "discord.gg", "discordapp.com",
            "cdn.discordapp.com", "media.discordapp.net",
            # Signal
            "signal.org", "www.signal.org",
            # Messenger (Meta)
            "messenger.com", "www.messenger.com",
            # Slack
            "slack.com", "www.slack.com",
            "slack-edge.com", "slack-imgs.com",
            # Microsoft Teams
            "teams.microsoft.com", "teams.live.com",
        ],
    },
    "apostas": {
        "label": "Apostas",
        "icon": "currency-dollar",
        "domains": [
            # Bet365
            "bet365.com", "www.bet365.com", "members.bet365.com",
            # Sportingbet
            "sportingbet.com", "www.sportingbet.com", "sportingbet.com.br",
            # Betano
            "betano.com", "www.betano.com", "betano.com.br", "br.betano.com",
            # Pixbet
            "pixbet.com", "www.pixbet.com", "pixbet.com.br",
            # Estrelabet
            "estrelabet.com", "www.estrelabet.com",
            # Blaze
            "blaze.com", "www.blaze.com", "blaze.bet", "blaze.ac",
            # Outros populares no Brasil
            "betfair.com", "www.betfair.com",
            "galera.bet", "www.galera.bet",
            "novibet.com", "www.novibet.com",
            "betnacional.com", "www.betnacional.com",
            "f12.bet", "www.f12.bet",
            "vaidebet.com", "www.vaidebet.com",
            "superbet.com", "www.superbet.com",
            "casa-de-apostas.com",
            "parimatch.com", "www.parimatch.com",
            "1xbet.com", "www.1xbet.com",
            "22bet.com", "www.22bet.com",
            "stake.com", "www.stake.com",
            "pinnacle.com", "www.pinnacle.com",
            "betsson.com", "www.betsson.com",
            "rivalo.com", "www.rivalo.com",
            "betway.com", "www.betway.com",
            "bodog.com", "www.bodog.com",
            "kto.com", "www.kto.com",
            "mrjack.bet",
        ],
    },
    "adulto": {
        "label": "Conteúdo Adulto",
        "icon": "eye-slash",
        "domains": [
            "pornhub.com", "www.pornhub.com",
            "xvideos.com", "www.xvideos.com",
            "xnxx.com", "www.xnxx.com",
            "redtube.com", "www.redtube.com",
            "xhamster.com", "www.xhamster.com",
            "youporn.com", "www.youporn.com",
            "spankbang.com", "www.spankbang.com",
            "tube8.com", "www.tube8.com",
            "chaturbate.com", "www.chaturbate.com",
            "stripchat.com", "www.stripchat.com",
            "onlyfans.com", "www.onlyfans.com",
            "brazzers.com", "www.brazzers.com",
            "livejasmin.com", "www.livejasmin.com",
            "cam4.com", "www.cam4.com",
            "bongacams.com", "www.bongacams.com",
        ],
    },
    "downloads_conversores": {
        "label": "Downloads e Conversores",
        "icon": "arrow-down-tray",
        "domains": [
            # Conversores de vídeo YouTube/online
            "y2mate.com", "www.y2mate.com", "y2mate.is",
            "savefrom.net", "www.savefrom.net", "en.savefrom.net",
            "ssyoutube.com", "www.ssyoutube.com",
            "snaptik.app", "www.snaptik.app",
            "ssstik.io", "www.ssstik.io",
            "9xbuddy.com", "www.9xbuddy.com",
            "clipconverter.cc", "www.clipconverter.cc",
            "onlinevideoconverter.com", "www.onlinevideoconverter.com",
            "flvto.biz", "www.flvto.biz",
            "ytmp3.cc", "www.ytmp3.cc",
            "ytmp3.nu", "www.ytmp3.nu",
            "yt1s.com", "www.yt1s.com",
            "yt5s.com", "www.yt5s.com",
            "loader.to", "www.loader.to",
            "mp3juices.cc", "www.mp3juices.cc",
            "mp3download.to", "www.mp3download.to",
            "convertio.co", "www.convertio.co",
            "online-convert.com", "www.online-convert.com",
            "anyconv.com", "www.anyconv.com",
            "keepvid.com", "www.keepvid.com",
            "videodownloaderpro.net",
            "tubemate.cc", "www.tubemate.cc",
            "4kdownload.com", "www.4kdownload.com",
            "addoncrop.com",
            # Sites de download de software/torrent
            "torrentz2.eu", "thepiratebay.org", "www.thepiratebay.org",
            "1337x.to", "www.1337x.to",
            "rarbg.to", "yts.mx", "www.yts.mx",
            "nyaa.si", "fitgirl-repacks.site",
            "kickasstorrents.to", "limetorrents.info",
            "baixaki.com.br", "www.baixaki.com.br",
            "superdownloads.com.br", "www.superdownloads.com.br",
            "mediafire.com", "www.mediafire.com",
            "mega.nz", "mega.io",
            "zippyshare.com", "www.zippyshare.com",
            "wetransfer.com", "www.wetransfer.com",
            "sendspace.com", "www.sendspace.com",
            "4shared.com", "www.4shared.com",
            "uploaded.net", "rapidgator.net",
        ],
    },
    "entretenimento": {
        "label": "Entretenimento e Fofoca",
        "icon": "face-smile",
        "domains": [
            # Fofoca e notícias de celebridades
            "buzzfeed.com", "www.buzzfeed.com",
            "boredpanda.com", "www.boredpanda.com",
            "9gag.com", "www.9gag.com",
            "imgur.com", "www.imgur.com", "i.imgur.com",
            "giphy.com", "www.giphy.com",
            "knowyourmeme.com",
            "memedroid.com", "www.memedroid.com",
            "ifunny.co", "www.ifunny.co",
            # Quiz e testes online
            "playbuzz.com", "www.playbuzz.com",
            # Horóscopo e astrologia
            "astro.com", "www.astro.com",
            "personare.com.br", "www.personare.com.br",
            # Receitas e culinária (distração)
            "tudogostoso.com.br", "www.tudogostoso.com.br",
            "receitasnestle.com.br",
            # Compras online
            "shopee.com.br", "www.shopee.com.br",
            "shein.com", "www.shein.com", "br.shein.com",
            "aliexpress.com", "www.aliexpress.com", "pt.aliexpress.com",
            "temu.com", "www.temu.com",
            "wish.com", "www.wish.com",
            "amazon.com.br", "www.amazon.com.br",
            "mercadolivre.com.br", "www.mercadolivre.com.br",
            "magazineluiza.com.br", "www.magazineluiza.com.br",
            "americanas.com.br", "www.americanas.com.br",
            "casasbahia.com.br", "www.casasbahia.com.br",
            "olx.com.br", "www.olx.com.br",
        ],
    },
}


def category_label(key: str) -> str:
    return SITE_CATEGORIES.get(key, {}).get("label", key or "Individual")
