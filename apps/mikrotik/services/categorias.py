"""Catálogo de categorias de domínios bloqueáveis.

Portado do painel Laravel antigo (app/Models/SitePolicy.php). Cada categoria
tem um slug, label exibido na UI, ícone (Lucide), e lista curada de domínios
que cobrem o site, seus subdomínios principais, CDNs e auth domains conhecidos
(ex.: byteoversea.com pra TikTok, accountkit.com pra Facebook, etc).

Quando o operador clica numa categoria na UI, todos esses domínios são
inseridos como `RegraDominio` na política, com `categoria=<slug>` pra rastrear
origem. Toggle off da categoria apaga as regras correspondentes.
"""

CATEGORIAS = {
    "redes_sociais": {
        "label": "Redes Sociais",
        "icon": "lucide:users",
        "dominios": [
            # Facebook (Meta)
            "facebook.com", "www.facebook.com", "m.facebook.com",
            "web.facebook.com", "touch.facebook.com", "mobile.facebook.com",
            "fb.com", "www.fb.com", "fb.watch", "fb.me", "fb.gg",
            "facebook.net", "fbcdn.net", "fbsbx.com",
            "fbcdn.com", "fbpigeon.com", "accountkit.com",
            # Instagram
            "instagram.com", "www.instagram.com", "i.instagram.com",
            "l.instagram.com", "about.instagram.com",
            "ig.me", "ig.com", "cdninstagram.com",
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
            # Threads
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
        "icon": "lucide:play",
        "dominios": [
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
        "icon": "lucide:gamepad-2",
        "dominios": [
            "store.steampowered.com", "steampowered.com", "steamcommunity.com",
            "steamstatic.com", "steamcontent.com", "steamgames.com",
            "epicgames.com", "www.epicgames.com",
            "epicgames.dev", "unrealengine.com",
            "roblox.com", "www.roblox.com",
            "rbxcdn.com", "rbx.com",
            "miniclip.com", "www.miniclip.com",
            "friv.com", "www.friv.com",
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
        "icon": "lucide:message-circle",
        "dominios": [
            # WhatsApp
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
            # Messenger
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
        "icon": "lucide:dice-5",
        "dominios": [
            "bet365.com", "www.bet365.com", "members.bet365.com",
            "sportingbet.com", "www.sportingbet.com", "sportingbet.com.br",
            "betano.com", "www.betano.com", "betano.com.br", "br.betano.com",
            "pixbet.com", "www.pixbet.com", "pixbet.com.br",
            "estrelabet.com", "www.estrelabet.com",
            "blaze.com", "www.blaze.com", "blaze.bet", "blaze.ac",
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
        "icon": "lucide:eye-off",
        "dominios": [
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
        "icon": "lucide:download",
        "dominios": [
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
            # Torrents
            "torrentz2.eu", "thepiratebay.org", "www.thepiratebay.org",
            "1337x.to", "www.1337x.to",
            "rarbg.to", "yts.mx", "www.yts.mx",
            "nyaa.si", "fitgirl-repacks.site",
            "kickasstorrents.to", "limetorrents.info",
            # Sites de download BR
            "baixaki.com.br", "www.baixaki.com.br",
            "superdownloads.com.br", "www.superdownloads.com.br",
            # Hospedagem de arquivos
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
        "icon": "lucide:smile",
        "dominios": [
            # Memes / fofoca
            "buzzfeed.com", "www.buzzfeed.com",
            "boredpanda.com", "www.boredpanda.com",
            "9gag.com", "www.9gag.com",
            "imgur.com", "www.imgur.com", "i.imgur.com",
            "giphy.com", "www.giphy.com",
            "knowyourmeme.com",
            "memedroid.com", "www.memedroid.com",
            "ifunny.co", "www.ifunny.co",
            "playbuzz.com", "www.playbuzz.com",
            # Astrologia
            "astro.com", "www.astro.com",
            "personare.com.br", "www.personare.com.br",
            # Receitas (distração)
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


def listar_categorias() -> list[dict]:
    """Lista de cards de categoria pra UI: [{slug, label, icon, count}]."""
    return [
        {
            "slug": slug,
            "label": meta["label"],
            "icon": meta["icon"],
            "count": len(meta["dominios"]),
        }
        for slug, meta in CATEGORIAS.items()
    ]


def dominios_da_categoria(slug: str) -> list[str]:
    return CATEGORIAS.get(slug, {}).get("dominios", [])


def label_da_categoria(slug: str) -> str:
    return CATEGORIAS.get(slug, {}).get("label", slug)
