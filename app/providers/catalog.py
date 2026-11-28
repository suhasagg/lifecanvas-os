"""Provider catalogue: every external system LifeCanvasOS can read from, write to or hand off to."""
from __future__ import annotations

from app.providers.base import ProviderSpec as P

R, W, H = "read", "write", "handoff"

SPECS: list[P] = [
    # ---- credential-free public data
    P("open_meteo", "Open-Meteo", "travel", ("geocoding", "weather"), ("open-meteo.com",), docs="https://open-meteo.com/en/docs", attribution="Weather data by Open-Meteo.com (CC BY 4.0)", rate_per_min=120),
    P("met_norway", "MET Norway", "travel", ("weather",), ("api.met.no",), docs="https://api.met.no/weatherapi/locationforecast/2.0/documentation", attribution="Weather data from MET Norway (CC BY 4.0)"),
    P("nominatim", "OpenStreetMap Nominatim", "dining", ("places", "geocoding"), ("nominatim.openstreetmap.org",), docs="https://nominatim.org/release-docs/latest/api/Search/", attribution="© OpenStreetMap contributors (ODbL)", rate_per_min=50, concurrency=1, cache_ttl_s=3600),
    P("overpass", "OpenStreetMap Overpass", "dining", ("places",), ("overpass-api.de", "overpass.private.coffee", "overpass.kumi.systems"), docs="https://wiki.openstreetmap.org/wiki/Overpass_API", attribution="© OpenStreetMap contributors (ODbL)", rate_per_min=30, concurrency=2, timeout_s=4.5, retries=0, cache_ttl_s=1800),
    P("itunes", "Apple iTunes Search", "entertainment", ("music", "movies"), ("itunes.apple.com",), docs="https://performance-partners.apple.com/search-api", attribution="Apple iTunes Search API", rate_per_min=20),
    P("musicbrainz", "MusicBrainz", "entertainment", ("artists", "events"), ("musicbrainz.org",), docs="https://musicbrainz.org/doc/MusicBrainz_API", attribution="MusicBrainz (CC0)", rate_per_min=50, concurrency=1),
    P("thesportsdb", "TheSportsDB", "entertainment", ("fixtures", "teams"), ("www.thesportsdb.com",), docs="https://www.thesportsdb.com/documentation", attribution="TheSportsDB free tier", rate_per_min=30, concurrency=2),
    P("tvmaze", "TVmaze", "entertainment", ("shows",), ("api.tvmaze.com",), docs="https://www.tvmaze.com/api", attribution="TVmaze (CC BY-SA)"),
    P("openlibrary", "Open Library", "culture", ("books",), ("openlibrary.org",), docs="https://openlibrary.org/developers/api", attribution="Open Library / Internet Archive"),
    P("artic", "Art Institute of Chicago", "culture", ("artworks",), ("api.artic.edu",), docs="https://api.artic.edu/docs/", attribution="Art Institute of Chicago API"),
    P("met_museum", "The Metropolitan Museum of Art", "culture", ("artworks",), ("collectionapi.metmuseum.org",), docs="https://metmuseum.github.io/", attribution="The Met Open Access (CC0)", rate_per_min=70),
    P("wikipedia", "Wikipedia", "research", ("search", "summary", "nearby"), ("en.wikipedia.org",), docs="https://www.mediawiki.org/wiki/API:Main_page", attribution="Wikipedia (CC BY-SA 4.0)", rate_per_min=120),
    P("wikivoyage", "Wikivoyage", "travel", ("destinations",), ("en.wikivoyage.org",), docs="https://www.mediawiki.org/wiki/API:Main_page", attribution="Wikivoyage (CC BY-SA 4.0)"),
    P("commons", "Wikimedia Commons", "culture", ("images",), ("commons.wikimedia.org",), docs="https://commons.wikimedia.org/wiki/Commons:API", attribution="Wikimedia Commons contributors"),
    P("duckduckgo", "DuckDuckGo Instant Answers", "research", ("answers",), ("api.duckduckgo.com",), docs="https://duckduckgo.com/duckduckgo-help-pages/open-source/instant-answer-interface", attribution="DuckDuckGo Instant Answer API"),
    # ---- credentialed read providers
    P("ticketmaster", "Ticketmaster Discovery", "entertainment", ("events",), ("app.ticketmaster.com",), ("TICKETMASTER_API_KEY",), docs="https://developer.ticketmaster.com/products-and-docs/apis/discovery-api/v2/", attribution="Ticketmaster Discovery API"),
    P("tmdb", "TMDB", "entertainment", ("movies",), ("api.themoviedb.org",), ("TMDB_READ_TOKEN",), docs="https://developer.themoviedb.org/docs", attribution="This product uses the TMDB API but is not endorsed or certified by TMDB."),
    P("spotify", "Spotify Web API", "entertainment", ("music", "artists"), ("api.spotify.com", "accounts.spotify.com"), ("SPOTIFY_CLIENT_ID", "SPOTIFY_CLIENT_SECRET"), docs="https://developer.spotify.com/documentation/web-api", attribution="Spotify"),
    P("youtube", "YouTube Data API", "entertainment", ("videos",), ("www.googleapis.com",), ("YOUTUBE_API_KEY",), docs="https://developers.google.com/youtube/v3", attribution="YouTube"),
    P("lastfm", "Last.fm", "entertainment", ("artists", "music"), ("ws.audioscrobbler.com",), ("LASTFM_API_KEY",), docs="https://www.last.fm/api", attribution="Last.fm"),
    P("google_places", "Google Places", "dining", ("places",), ("places.googleapis.com",), ("GOOGLE_PLACES_KEY",), docs="https://developers.google.com/maps/documentation/places/web-service", attribution="Google Places"),
    P("foursquare", "Foursquare Places", "dining", ("places",), ("places-api.foursquare.com",), ("FOURSQUARE_API_KEY",), docs="https://docs.foursquare.com/developer/reference/place-search", attribution="Foursquare"),
    P("amadeus", "Amadeus Self-Service", "travel", ("flights",), ("test.api.amadeus.com", "api.amadeus.com"), ("AMADEUS_CLIENT_ID", "AMADEUS_CLIENT_SECRET"), docs="https://developers.amadeus.com/self-service", attribution="Amadeus for Developers", cache_ttl_s=120),
    P("geonames", "GeoNames", "travel", ("geocoding",), ("secure.geonames.org",), ("GEONAMES_USERNAME",), docs="https://www.geonames.org/export/web-services.html", attribution="GeoNames (CC BY 4.0)"),
    P("opentripmap", "OpenTripMap", "travel", ("attractions",), ("api.opentripmap.com",), ("OPENTRIPMAP_API_KEY",), docs="https://dev.opentripmap.org/docs", attribution="OpenTripMap (ODbL)"),
    P("google_books", "Google Books", "culture", ("books",), ("www.googleapis.com",), ("GOOGLE_BOOKS_KEY",), docs="https://developers.google.com/books/docs/v1/using", attribution="Google Books"),
    P("strava", "Strava", "culture", ("fitness",), ("www.strava.com",), ("STRAVA_ACCESS_TOKEN",), docs="https://developers.strava.com/docs/reference/", attribution="Powered by Strava", scopes=("activity:read",)),
    P("tavily", "Tavily Search", "research", ("web_search",), ("api.tavily.com",), ("TAVILY_API_KEY",), docs="https://docs.tavily.com/", attribution="Tavily"),
    P("google_calendar_read", "Google Calendar (availability)", "productivity", ("calendar_read",), ("www.googleapis.com",), ("GOOGLE_CALENDAR_ACCESS_TOKEN",), docs="https://developers.google.com/calendar/api/v3/reference/freebusy", attribution="Google Calendar", scopes=("calendar.readonly",)),
    # ---- authenticated write adapters (approval required)
    P("x", "X", "social", ("post",), ("api.x.com",), ("X_USER_ACCESS_TOKEN",), W, "https://docs.x.com/x-api/posts/create-post", scopes=("tweet.write",)),
    P("linkedin", "LinkedIn", "social", ("post",), ("api.linkedin.com",), ("LINKEDIN_ACCESS_TOKEN", "LINKEDIN_AUTHOR_URN"), W, "https://learn.microsoft.com/linkedin/marketing/community-management/shares/posts-api", scopes=("w_member_social",)),
    P("instagram", "Instagram", "social", ("post",), ("graph.facebook.com",), ("INSTAGRAM_USER_ID", "INSTAGRAM_ACCESS_TOKEN"), W, "https://developers.facebook.com/docs/instagram-platform/content-publishing", scopes=("instagram_content_publish",)),
    P("facebook", "Facebook Pages", "social", ("post",), ("graph.facebook.com",), ("FACEBOOK_PAGE_ID", "FACEBOOK_PAGE_TOKEN"), W, "https://developers.facebook.com/docs/pages-api/posts", scopes=("pages_manage_posts",)),
    P("bluesky", "Bluesky", "social", ("post",), ("bsky.social",), ("BLUESKY_HANDLE", "BLUESKY_APP_PASSWORD"), W, "https://docs.bsky.app/docs/api/com-atproto-repo-create-record"),
    P("mastodon", "Mastodon", "social", ("post",), (), ("MASTODON_BASE_URL", "MASTODON_ACCESS_TOKEN"), W, "https://docs.joinmastodon.org/methods/statuses/", scopes=("write:statuses",)),
    P("wordpress", "WordPress", "social", ("blog",), (), ("WORDPRESS_BASE_URL", "WORDPRESS_USER", "WORDPRESS_APP_PASSWORD"), W, "https://developer.wordpress.org/rest-api/reference/posts/"),
    P("telegram", "Telegram", "social", ("message",), ("api.telegram.org",), ("TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"), W, "https://core.telegram.org/bots/api#sendmessage"),
    P("discord", "Discord", "social", ("message",), ("discord.com",), ("DISCORD_WEBHOOK_URL",), W, "https://discord.com/developers/docs/resources/webhook"),
    P("slack", "Slack", "social", ("message",), ("slack.com",), ("SLACK_BOT_TOKEN",), W, "https://api.slack.com/methods/chat.postMessage", scopes=("chat:write",)),
    P("gmail", "Gmail", "productivity", ("email",), ("gmail.googleapis.com",), ("GMAIL_ACCESS_TOKEN",), W, "https://developers.google.com/gmail/api/reference/rest/v1/users.messages/send", scopes=("gmail.send",)),
    P("google_calendar", "Google Calendar", "productivity", ("calendar_event",), ("www.googleapis.com",), ("GOOGLE_CALENDAR_ACCESS_TOKEN",), W, "https://developers.google.com/calendar/api/v3/reference/events/insert", scopes=("calendar.events",)),
    P("google_tasks", "Google Tasks", "productivity", ("task",), ("tasks.googleapis.com",), ("GOOGLE_TASKS_ACCESS_TOKEN",), W, "https://developers.google.com/tasks/reference/rest/v1/tasks/insert", scopes=("tasks",)),
    P("google_drive", "Google Drive", "productivity", ("document",), ("www.googleapis.com",), ("GOOGLE_DRIVE_ACCESS_TOKEN",), W, "https://developers.google.com/drive/api/reference/rest/v3/files/create", scopes=("drive.file",)),
    P("notion", "Notion", "productivity", ("note",), ("api.notion.com",), ("NOTION_TOKEN",), W, "https://developers.notion.com/reference/patch-block-children"),
    P("todoist", "Todoist", "productivity", ("task",), ("api.todoist.com",), ("TODOIST_API_TOKEN",), W, "https://developer.todoist.com/api/v1/"),
    P("ms_graph", "Microsoft Graph", "productivity", ("task",), ("graph.microsoft.com",), ("MS_GRAPH_ACCESS_TOKEN",), W, "https://learn.microsoft.com/graph/api/todotasklist-post-tasks", scopes=("Tasks.ReadWrite",)),
    P("amadeus_flight_order", "Amadeus flight booking", "travel", ("booking",), ("test.api.amadeus.com", "api.amadeus.com"), ("AMADEUS_CLIENT_ID", "AMADEUS_CLIENT_SECRET"), W, "https://developers.amadeus.com/self-service/category/flights/api-doc/flight-create-orders"),
    P("spotify_playlist", "Spotify playlists", "entertainment", ("playlist",), ("api.spotify.com",), ("SPOTIFY_USER_ACCESS_TOKEN",), W, "https://developer.spotify.com/documentation/web-api/reference/create-playlist", scopes=("playlist-modify-private",)),
    # ---- language models
    P("openai", "OpenAI", "llm", ("chat",), ("api.openai.com",), ("OPENAI_API_KEY",), "llm", "https://platform.openai.com/docs/api-reference/chat", timeout_s=40, retries=1, cache_ttl_s=0),
    P("anthropic", "Anthropic Claude", "llm", ("chat",), ("api.anthropic.com",), ("ANTHROPIC_API_KEY",), "llm", "https://docs.anthropic.com/en/api/messages", timeout_s=40, retries=1, cache_ttl_s=0),
    P("gemini", "Google Gemini", "llm", ("chat",), ("generativelanguage.googleapis.com",), ("GEMINI_API_KEY",), "llm", "https://ai.google.dev/api/generate-content", timeout_s=40, retries=1, cache_ttl_s=0),
    P("openrouter", "OpenRouter", "llm", ("chat",), ("openrouter.ai",), ("OPENROUTER_API_KEY",), "llm", "https://openrouter.ai/docs/api-reference/overview", timeout_s=40, retries=1, cache_ttl_s=0),
    P("groq", "Groq", "llm", ("chat",), ("api.groq.com",), ("GROQ_API_KEY",), "llm", "https://console.groq.com/docs/api-reference", timeout_s=30, retries=1, cache_ttl_s=0),
    P("ollama", "Ollama", "llm", ("chat",), (), ("OLLAMA_BASE_URL",), "llm", "https://github.com/ollama/ollama/blob/main/docs/api.md", timeout_s=60, retries=0, cache_ttl_s=0),
]

# Consumer apps without a public partner API available to this project: honest deep-link handoffs only.
HANDOFFS: list[P] = [
    P(i, n, c, ("handoff",), access=H, homepage=u)
    for i, n, c, u in [
        ("bookmyshow", "BookMyShow", "entertainment", "https://in.bookmyshow.com/"),
        ("district", "District", "entertainment", "https://www.district.in/"),
        ("zomato", "Zomato", "dining", "https://www.zomato.com/"),
        ("swiggy", "Swiggy", "dining", "https://www.swiggy.com/"),
        ("opentable", "OpenTable", "dining", "https://www.opentable.com/"),
        ("google_maps", "Google Maps", "dining", "https://www.google.com/maps"),
        ("airbnb", "Airbnb", "travel", "https://www.airbnb.com/"),
        ("makemytrip", "MakeMyTrip", "travel", "https://www.makemytrip.com/"),
        ("booking", "Booking.com", "travel", "https://www.booking.com/"),
        ("uber", "Uber", "travel", "https://m.uber.com/"),
        ("klook", "Klook", "travel", "https://www.klook.com/"),
        ("getyourguide", "GetYourGuide", "travel", "https://www.getyourguide.com/"),
        ("tripadvisor", "Tripadvisor", "travel", "https://www.tripadvisor.com/"),
        ("google_flights", "Google Flights", "travel", "https://www.google.com/travel/flights"),
    ]
]

ALL: dict[str, P] = {p.id: p for p in SPECS + HANDOFFS}
