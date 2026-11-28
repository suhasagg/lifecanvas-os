# Integrations

53 API providers and 14 app handoffs are registered in `app/providers/catalog.py`.

Status meanings: **connected** (a live probe succeeded), **ready** (no credentials needed or credentials set, not yet probed), **configuration required**, **authentication expired**, **rate limited**, **temporarily unavailable**, **external handoff**.

Live verification during development covered only the credential-free providers. Credentialed providers follow their documented APIs but were not called with real keys.

| Provider | Area | Access | Capabilities | Credentials | Verified live |
| --- | --- | --- | --- | --- | --- |
| [Open-Meteo](https://open-meteo.com/en/docs) | travel | read | geocoding, weather | none | yes |
| [MET Norway](https://api.met.no/weatherapi/locationforecast/2.0/documentation) | travel | read | weather | none | yes |
| [OpenStreetMap Nominatim](https://nominatim.org/release-docs/latest/api/Search/) | dining | read | places, geocoding | none | yes |
| [OpenStreetMap Overpass](https://wiki.openstreetmap.org/wiki/Overpass_API) | dining | read | places | none | yes |
| [Apple iTunes Search](https://performance-partners.apple.com/search-api) | entertainment | read | music, movies | none | yes |
| [MusicBrainz](https://musicbrainz.org/doc/MusicBrainz_API) | entertainment | read | artists, events | none | yes |
| [TheSportsDB](https://www.thesportsdb.com/documentation) | entertainment | read | fixtures, teams | none | yes |
| [TVmaze](https://www.tvmaze.com/api) | entertainment | read | shows | none | yes |
| [Open Library](https://openlibrary.org/developers/api) | culture | read | books | none | yes |
| [Art Institute of Chicago](https://api.artic.edu/docs/) | culture | read | artworks | none | yes |
| [The Metropolitan Museum of Art](https://metmuseum.github.io/) | culture | read | artworks | none | yes |
| [Wikipedia](https://www.mediawiki.org/wiki/API:Main_page) | research | read | search, summary, nearby | none | yes |
| [Wikivoyage](https://www.mediawiki.org/wiki/API:Main_page) | travel | read | destinations | none | yes |
| [Wikimedia Commons](https://commons.wikimedia.org/wiki/Commons:API) | culture | read | images | none | yes |
| [DuckDuckGo Instant Answers](https://duckduckgo.com/duckduckgo-help-pages/open-source/instant-answer-interface) | research | read | answers | none | yes |
| [Ticketmaster Discovery](https://developer.ticketmaster.com/products-and-docs/apis/discovery-api/v2/) | entertainment | read | events | `TICKETMASTER_API_KEY` | no |
| [TMDB](https://developer.themoviedb.org/docs) | entertainment | read | movies | `TMDB_READ_TOKEN` | no |
| [Spotify Web API](https://developer.spotify.com/documentation/web-api) | entertainment | read | music, artists | `SPOTIFY_CLIENT_ID`, `SPOTIFY_CLIENT_SECRET` | no |
| [YouTube Data API](https://developers.google.com/youtube/v3) | entertainment | read | videos | `YOUTUBE_API_KEY` | no |
| [Last.fm](https://www.last.fm/api) | entertainment | read | artists, music | `LASTFM_API_KEY` | no |
| [Google Places](https://developers.google.com/maps/documentation/places/web-service) | dining | read | places | `GOOGLE_PLACES_KEY` | no |
| [Foursquare Places](https://docs.foursquare.com/developer/reference/place-search) | dining | read | places | `FOURSQUARE_API_KEY` | no |
| [Amadeus Self-Service](https://developers.amadeus.com/self-service) | travel | read | flights | `AMADEUS_CLIENT_ID`, `AMADEUS_CLIENT_SECRET` | no |
| [GeoNames](https://www.geonames.org/export/web-services.html) | travel | read | geocoding | `GEONAMES_USERNAME` | no |
| [OpenTripMap](https://dev.opentripmap.org/docs) | travel | read | attractions | `OPENTRIPMAP_API_KEY` | no |
| [Google Books](https://developers.google.com/books/docs/v1/using) | culture | read | books | `GOOGLE_BOOKS_KEY` | no |
| [Strava](https://developers.strava.com/docs/reference/) | culture | read | fitness | `STRAVA_ACCESS_TOKEN` | no |
| [Tavily Search](https://docs.tavily.com/) | research | read | web_search | `TAVILY_API_KEY` | no |
| [Google Calendar (availability)](https://developers.google.com/calendar/api/v3/reference/freebusy) | productivity | read | calendar_read | `GOOGLE_CALENDAR_ACCESS_TOKEN` | no |
| [X](https://docs.x.com/x-api/posts/create-post) | social | write · approval | post | `X_USER_ACCESS_TOKEN` | no |
| [LinkedIn](https://learn.microsoft.com/linkedin/marketing/community-management/shares/posts-api) | social | write · approval | post | `LINKEDIN_ACCESS_TOKEN`, `LINKEDIN_AUTHOR_URN` | no |
| [Instagram](https://developers.facebook.com/docs/instagram-platform/content-publishing) | social | write · approval | post | `INSTAGRAM_USER_ID`, `INSTAGRAM_ACCESS_TOKEN` | no |
| [Facebook Pages](https://developers.facebook.com/docs/pages-api/posts) | social | write · approval | post | `FACEBOOK_PAGE_ID`, `FACEBOOK_PAGE_TOKEN` | no |
| [Bluesky](https://docs.bsky.app/docs/api/com-atproto-repo-create-record) | social | write · approval | post | `BLUESKY_HANDLE`, `BLUESKY_APP_PASSWORD` | no |
| [Mastodon](https://docs.joinmastodon.org/methods/statuses/) | social | write · approval | post | `MASTODON_BASE_URL`, `MASTODON_ACCESS_TOKEN` | no |
| [WordPress](https://developer.wordpress.org/rest-api/reference/posts/) | social | write · approval | blog | `WORDPRESS_BASE_URL`, `WORDPRESS_USER`, `WORDPRESS_APP_PASSWORD` | no |
| [Telegram](https://core.telegram.org/bots/api#sendmessage) | social | write · approval | message | `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` | no |
| [Discord](https://discord.com/developers/docs/resources/webhook) | social | write · approval | message | `DISCORD_WEBHOOK_URL` | no |
| [Slack](https://api.slack.com/methods/chat.postMessage) | social | write · approval | message | `SLACK_BOT_TOKEN` | no |
| [Gmail](https://developers.google.com/gmail/api/reference/rest/v1/users.messages/send) | productivity | write · approval | email | `GMAIL_ACCESS_TOKEN` | no |
| [Google Calendar](https://developers.google.com/calendar/api/v3/reference/events/insert) | productivity | write · approval | calendar_event | `GOOGLE_CALENDAR_ACCESS_TOKEN` | no |
| [Google Tasks](https://developers.google.com/tasks/reference/rest/v1/tasks/insert) | productivity | write · approval | task | `GOOGLE_TASKS_ACCESS_TOKEN` | no |
| [Google Drive](https://developers.google.com/drive/api/reference/rest/v3/files/create) | productivity | write · approval | document | `GOOGLE_DRIVE_ACCESS_TOKEN` | no |
| [Notion](https://developers.notion.com/reference/patch-block-children) | productivity | write · approval | note | `NOTION_TOKEN` | no |
| [Todoist](https://developer.todoist.com/api/v1/) | productivity | write · approval | task | `TODOIST_API_TOKEN` | no |
| [Microsoft Graph](https://learn.microsoft.com/graph/api/todotasklist-post-tasks) | productivity | write · approval | task | `MS_GRAPH_ACCESS_TOKEN` | no |
| [Spotify playlists](https://developer.spotify.com/documentation/web-api/reference/create-playlist) | entertainment | write · approval | playlist | `SPOTIFY_USER_ACCESS_TOKEN` | no |
| [OpenAI](https://platform.openai.com/docs/api-reference/chat) | llm | model | chat | `OPENAI_API_KEY` | no |
| [Anthropic Claude](https://docs.anthropic.com/en/api/messages) | llm | model | chat | `ANTHROPIC_API_KEY` | no |
| [Google Gemini](https://ai.google.dev/api/generate-content) | llm | model | chat | `GEMINI_API_KEY` | no |
| [OpenRouter](https://openrouter.ai/docs/api-reference/overview) | llm | model | chat | `OPENROUTER_API_KEY` | no |
| [Groq](https://console.groq.com/docs/api-reference) | llm | model | chat | `GROQ_API_KEY` | no |
| [Ollama](https://github.com/ollama/ollama/blob/main/docs/api.md) | llm | model | chat | `OLLAMA_BASE_URL` | no |

## App handoffs

These open the provider's site with your search. LifeCanvasOS does not book, pay or confirm availability.

| App | Area |
| --- | --- |
| [BookMyShow](https://in.bookmyshow.com/) | entertainment |
| [District](https://www.district.in/) | entertainment |
| [Zomato](https://www.zomato.com/) | dining |
| [Swiggy](https://www.swiggy.com/) | dining |
| [OpenTable](https://www.opentable.com/) | dining |
| [Google Maps](https://www.google.com/maps) | dining |
| [Airbnb](https://www.airbnb.com/) | travel |
| [MakeMyTrip](https://www.makemytrip.com/) | travel |
| [Booking.com](https://www.booking.com/) | travel |
| [Uber](https://m.uber.com/) | travel |
| [Klook](https://www.klook.com/) | travel |
| [GetYourGuide](https://www.getyourguide.com/) | travel |
| [Tripadvisor](https://www.tripadvisor.com/) | travel |
| [Google Flights](https://www.google.com/travel/flights) | travel |

## Gateway behaviour

- HTTPS only, per-provider host allowlist, no redirects.
- Reads: TTL cache, up to `retries` attempts with exponential backoff and jitter.
- Writes: exactly one attempt. A timeout or 5xx after sending is reported as outcome unknown.
- Circuit breaker opens after 4 consecutive transport failures for 30 s, per provider.
- Every call is logged to `provider_calls` (latency, retries, cache hit, error class).

## Adding a provider

1. Add a `ProviderSpec` to `catalog.py` and, if possible, a read-only probe to `registry.py`.
2. Write an adapter in `app/integrations/` that returns `card(...)` objects.
3. Register a tool in `app/tools/registry.py` and add it to the right agent allowlist.
