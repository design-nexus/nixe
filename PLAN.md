# Theater

Online Accounts (GOA/EDS, Settings) is documented in [`docs/online-accounts/PLAN.md`](docs/online-accounts/PLAN.md), not here.

## Current status — 2026-10-19

The requested foundation, Plex integration, unified library and Jellyfin feature
implementation is present. Remaining live-server and GUI validation is deferred at
Ken's request; the milestone notes below record the implementation history.

Latest additions:

- [x] Multipart Direct Play, resume, cross-part seeking and sequential transitions.
- [x] Plex and Jellyfin conversion with per-part offsets and whole-title progress.
- [x] Automatic conversion and alternate-copy retry within the selected edition.
- [x] Jellyfin collection views and provider-wide episode search/indexing.
- [x] Jellyfin bitmap subtitle burn-in, Off and choice preservation through seeks.
- [x] Opt-in, per-conflict watch-state review with fresh-state conflict checks;
  synchronization remains disabled by default, with no automatic offline writes.
- [x] Session cleanup for cancelled and stale playback resolutions.

Targeted provider/model fixtures and the release build pass. Installed the updated
binary, launcher and icon without opening or restarting Theater.


## Inspection and architecture

The workspace discovers `apps/*` and `crates/*`. Theater is `apps/theater`, binary
`nixe-theater`, app ID `io.github.design_nexus.nixe.Theater`. Follow `STYLE.md`:
Music's sidebar/head, non-expanding navigation, allocated-width resize probe,
shared settings card, status gear, native widgets and semantic palette tokens.
Cinematic artwork must fit that flat surface, typography and spacing.

Reuse `nixe-core` (identity, XDG paths, preferences, background jobs), `nixe-theme`
(live Omarchy and suite themes), `nixe-ui` (chrome, keys, settings, palette), and
`nixe-icons`. Media Player's `player/mpv.rs` and `player/video.rs` contain independent
client/render layers; its queue, resume policy, equalizer, MPRIS, local database,
scrub thumbnails and UI remain in Media Player. Its artwork downloader and SQLite
store are local-library-specific: use their worker/channel pattern, not their schema.
Git's `apps/git/src/providers/credentials.rs` already wraps `secret-tool` and redacts
secrets: reuse that approach for provider credentials, with Theater-specific keys.

- `nixe-playback`: extracted libmpv client and GTK/GDK OpenGL paintable renderer.
  Keep Media Player import paths via re-exports. One renderer/player per process;
  initialize on realization, free renderer before destroying mpv. No native child
  windows or X11 window IDs; preserve Wayland display sharing for VA-API.
- `nixe-media-model`: provider/server-scoped identities, external IDs, hierarchy,
  edition/version sources, watch state and object-safe asynchronous provider contract.
  Opaque server IDs never stand alone as library keys. No title-only deduplication.
- `nixe-media-cache`: SQLite versioned metadata snapshots and artwork index. Owned
  by background workers, transactional per-library refresh, preserve offline data
  when refresh fails. Persist only metadata and credential-free artwork keys/paths;
  obtain authenticated stream URLs at playback time, never cache tokens.
- `nixe-plex` (Phase 2), `nixe-jellyfin` (Phase 4): HTTP adapters under the same
  contract. One configured server each initially. Use worker threads plus bounded
  async channels as existing apps do; GTK never waits for HTTP or SQLite.
- `nixe-theater`: view state, provider orchestration, cached browsing, playback
  session/reporting; separate app directories, no changes to Media Player data.

## Milestones and tasks

### Phase 1 — foundation (this iteration)

- [x] Inspect style, Music, shared UI/theme/settings and Media Player libmpv.
- [x] Extract client/render layers and retain Media Player compatibility imports.
- [x] Establish unified models/provider contract without fake adapter implementations.
- [x] Add transactional SQLite metadata/artwork indexing and focused isolation tests.
- [x] Build a separate GTK shell: Home, Movies, TV, Collections, Now playing;
  responsive sidebar, search, window settings, shortcuts and offline/empty states.
- [x] Wire local-file playback through shared libmpv as a foundation smoke path.
- [x] Complete targeted build/tests and document results.

### Phase 2 — Plex MVP (in progress)

1. Verify current Plex APIs against primary documentation and fixtures. Implement
   PIN authentication and manual server connection; store tokens in Secret Service,
   never TOML, SQLite, command lines or logs. Handle locked/missing keyrings explicitly.
2. Implement timeouts, cancellation, bounded pagination, retry/offline states and
   library/metadata/collections/children endpoints; persist successful snapshots.
3. Populate Home (featured, Continue Watching, Recently Added), poster grids,
   sorting, provider filters, search and detail/season/episode views from cached data.
4. Download authenticated artwork on workers with concurrency limits, atomic files,
   size limits and an LRU disk budget; GTK loads cached scaled images lazily.
5. Resolve server parts to Direct Play, resume after FileLoaded, audio/subtitle
   choices, timeline updates including pause/stop/seek and session teardown.
6. Negotiate transcoding only when Direct Play fails or is unsuitable; explicit
   session IDs, bitrate/device profile and cleanup. Never silently loop retries.
7. Validate with Ken's Plex server after connection details are supplied in-app.

### Phase 3 — unified index

Match movies only with compatible TMDB/IMDb IDs and kind; series with reliable
provider IDs; episodes with parent series identity plus season/episode or episode
IDs. Retain edition/cut, media/part/version and source identities. Ambiguous matches
remain separate. Store logical groups separately from original records. Add manual
source/version picker and automatic policy (availability, preference, compatibility).
Filtering must retain source provenance. Never delete or modify media files.

### Phase 4 — Jellyfin and reconciliation

Implement Jellyfin auth, libraries, metadata, artwork, playback negotiation/session
reporting using the same contract. Exercise both providers concurrently. Watch state
stays server-local by default. Add opt-in reconciliation only after timestamp,
partial-progress, watched/unwatched conflicts and offline queues have reliable tests;
retain origin, revision and explicit user resolution, never silently overwrite.

## Decisions before further refactoring

No clarification is needed for this extraction: preserve the client/render behavior
and Media Player policy. Before multi-window playback, replace the inherited singleton
renderer with an owned session and verify texture/callback teardown. Before Plex live
testing, obtain server address and preferred login route through the app. Confirm the
preferred automatic source policy and edition grouping before Phase 3; default to
keeping ambiguous editions separate. Confirm reconciliation conflict policy before
enabling any cross-provider writes (disabled by default).

## Risks and validation

- Raw FFI callback and GL lifetimes: keep extraction mechanical, build both consumers,
  run the existing headless libmpv/equalizer check, and manually validate Wayland
  rendering on real media. A successful compile cannot prove GPU presentation.
- Providers have changing APIs and servers can be unavailable: fixtures and bounded
  network errors first, live Plex check later. No server credentials are assumed.
- IDs/editions are lossy if flattened: keep source-scoped keys and all variants;
  test cache isolation and snapshot atomicity. No filename/title fuzzy auto-merges.
- Existing applications: no new database migrations or settings changes for them;
  no broad suite runs. Build only Theater and Media Player plus focused model/cache
  tests. Install updated binaries and launcher assets as part of completion; avoid service, desktop config and default-handler changes.

## Foundation validation results

`cargo build -p nixe-theater -p nixe-media-player` passed.
`cargo test -p nixe-media-cache -p nixe-media-model --lib` passed (one cache test;
model crate has no independent tests yet). The cache test verifies server/provider
isolation, transaction rollback after a partial failed insert, mixed-server rejection,
and reconciliation disabled by default.
`cargo test -p nixe-media-player mpv_takes_the_equalizer -- --exact player::tests::mpv_takes_the_equalizer`
passed against the extracted libmpv implementation.

No live server authentication, GPU video presentation, or visual sizing check has
been performed. The optimized Theater binary, launcher entry and icon are installed for Ken. The foundation has empty library pages,
not functional Plex/Jellyfin browsing; local-file playback is the initial shared
engine integration. Plex MVP remains the next milestone.

## Plex iteration — implemented

- Added `nixe-plex`, implementing the shared provider contract with worker-backed
  futures, redacted errors, no credential redirects, numeric item IDs, bounded
  response bodies and pagination, library/collection/child/detail metadata parsing.
- Browser PIN sign-in per Plex's published native-client flow, optional manual
  token, stable persisted client identifier, and a dedicated Secret Service entry.
- Cached Plex movie/series/collection grids, library filter, sort, local search,
  series/season/episode detail navigation and version/edition selection.
- Featured/Continue Watching/Recently Added Home, three artwork workers, server
  scaling, atomic local cache writes, artwork indexing and 512 MiB eviction budget.
- Extracted existing Media Player artwork/card construction and CSS into
  `nixe-ui::media`; both consumers share the implementation without changing Media
  Player's library/artwork loading policy. F1 and video controls remain shared.
- Direct Play with URL-scoped ephemeral authentication, resume after FileLoaded,
  serialized progress reporting on a worker, stop/error cleanup and graceful final
  report lifetime. No cross-provider reconciliation is enabled.
- Targeted Plex HTTP fixtures pass for auth headers, pagination, edition/version
  metadata, Direct Play resolution, timeline POSTs, URL restrictions and safe errors.

Next: live Plex account/server verification through the app, transcoding fallback,
multi-part playback, server discovery, stale watch-state refresh and child caches.
Jellyfin and reliable duplicate grouping remain later phases. The current provider
pagination limit is 50,000 supported titles per library; failed snapshots do not
replace that library's previous offline data. Per-library snapshots are committed
independently, not as an all-server transaction. No authenticated live-server or
GPU stream playback claim is made from the HTTP fixture checks.

## Plex web-login correction

Web login is the default and requires no server address. After the PIN is claimed,
Theater fetches Plex account resources, filters to accessible media servers, and
uses each resource's server-specific access token. One server connects automatically;
multiple servers expose a server-name picker. Candidate connections prefer local,
then remote, with relay last; equivalent candidates are probed concurrently with
short timeouts and machine-identity confirmation. HTTPS-only resources reject HTTP.
Manual address/token entry remains available in a collapsed optional section.
A targeted resource fixture checks server filtering, scoped tokens, endpoint ordering,
invalid endpoint rejection and HTTPS-only handling. Live account verification remains.

## Plex playback fallback

Ken confirmed that web sign-in succeeded and content gradually appeared. Added
Automatic/Direct Play/Transcode choices without changing the shared controls.
Automatic playback makes one conversion attempt after a Direct Play failure.
Plex negotiation uses the selected media index, playback UUID, offset and Generic
profile augmented with progressive Matroska/H.264/AAC (1080p, 8 Mbps, stereo).
Server decision errors are reported without raw response text. Stream credentials
remain URL-scoped and ephemeral; no global FFmpeg authentication headers are used.

Converted streams map their time to the absolute item offset and retain full-item
duration. Seeking restarts conversion at the desired offset, preserving pause state.
The serialized reporting worker stops its own conversion UUID after the final
progress report. Closed/replaced sessions reject delayed conversion results.
The HTTP fixture now checks selected-version indices, offsets, explicit profile,
matching session UUIDs, denial handling and idempotent stop of an ended session.
Real server conversion/seek behavior and advanced server-side track selection
still need verification; multi-part queues and Jellyfin remain outstanding.


## Playback watch-state updates

Playback now updates Theater's in-memory resume position immediately and writes
an ordered SQLite overlay on the reporting worker. Movie/episode progress survives
restart, including episodes reached through series details. Home, grids and playable
details refresh when returning from playback. Existing Media Player controls stay
shared. Plex metadata is fetched after a successful stop report to obtain its own
watched status; Theater does not invent completion thresholds.

Snapshot start revisions and per-library cache watermarks prevent delayed reports,
old sessions or an in-flight library scan from replacing newer progress. Overlays
are retired by later authoritative library snapshots. This is local caching and
normal Plex timeline reporting, with cross-provider reconciliation still disabled.
Targeted cache checks cover snapshot/report ordering, stale writes, source isolation
and episodes absent from the top-level library snapshot. Live playback completion
and Plex's server-side timing still need user verification.

Next: incremental library refresh and persistent child-page caches, followed by
multi-part playback and reliable provider-independent matching before Jellyfin.


## Incremental loading and cached details

Theater now shows cached titles before connecting and publishes the first Plex
page, followed by batches of up to 500 titles, while the remaining libraries load.
The provider client becomes usable as soon as connection succeeds. Continue Watching
is requested early. Complete library snapshots remain atomic per library; failures
keep both previously cached titles and any newly loaded titles visible.

Series, season, collection and movie details have separate SQLite snapshots.
Opening a previously viewed page shows cached metadata/children before refreshing;
offline pages retain cached seasons and episodes. Only a complete successful child
fetch replaces a snapshot. Navigation generations and server identity checks reject
old results. Episode progress survives top-level series refreshes, and fresh child
metadata updates the watch overlay without letting delayed reports overwrite it.
Existing shared cards, layouts and playback controls are unchanged.

Validation: targeted cache tests cover child snapshot isolation, complete empty
lists, stale snapshots/reports, watch overlays and library refresh interactions;
Theater release build. Large-server responsiveness and offline browsing still need
live use. Next: multi-part playback, then reliable unified source matching.


## Multi-part Direct Play

Plex resolution now returns every part of the selected version in server order,
with credentials scoped to each ephemeral URL. The shared playback crate builds
an in-memory mpv EDL timeline using byte-length escaping, keeping one duration,
seek bar, resume position and Plex watch session across all parts. No credential
URLs or generated playlists are written to disk. A malformed part invalidates the
whole version instead of silently dropping files; resolution caps versions at 64
parts. Single-part playback and the existing shared controls remain unchanged.

Validation: a headless libmpv fixture loads two PCM files, checks total duration,
and seeks across the boundary in both directions, including a filename containing
Unicode and EDL delimiters. Plex HTTP fixtures verify part order, per-URL auth,
selected versions and safe rejection of multi-part transcoding. Release build passed.
Installed binary, launcher and icon without opening or restarting Theater, per Ken.
Live multi-part video compatibility remains to be confirmed. Multi-part conversion
is explicitly unavailable pending per-part conversion/session handling.

Next: unified title matching and source selection, preserving distinct editions;
Jellyfin remains a later adapter behind the existing provider abstraction.

mpv EDL reference: https://github.com/mpv-player/mpv/blob/master/DOCS/edl-mpv.rst


## Logical title grouping and playback sources

Added a provider-independent index in nixe-media-model. Movies and series match on
validated TMDB/IMDb/TVDB identifiers; episodes can also match using a known series
identifier plus exact season/episode numbers, including specials. Identifier bridges
join compatible groups, while missing or conflicting IDs remain separate. No fuzzy
title/year matching is used. Original source records, versions, editions and watch
states stay independent; no media files or server metadata are changed.

Home, movie/TV grids and search show one representative per logical title. Library
filters still select the matching actual source. The existing playback version
selector now offers edition-specific automatic selection and explicit provider /
library / edition / resolution / codec choices. Automatic selection prefers an
in-progress source within the chosen edition, then the current source and its first
valid version. Resume and Start over reflect the selected source's own watch state.
Series expose a source selector for browsing that library's seasons. Long labels
use the same constrained native dropdown pattern as the library filter.

Targeted model checks pass for cross-provider identifier bridges, conflicts, missing
IDs, edition/watch preservation and reliable episode matching. Theater release build
passes. Installed binary, launcher and icon without opening or restarting the app.
Live source selection remains to be verified. Jellyfin networking, provider filters
in the live UI and automatic retry of a different copy after a stream failure remain
outstanding; only Plex is connected in this iteration. Multi-part conversion also
remains pending.


## Jellyfin Direct Play MVP

Added nixe-jellyfin implementing the common MediaProvider interface: username /
password authentication, supported movie/TV views, paginated item and child lists,
resume items, provider IDs, artwork, per-version Direct Play and playback start /
progress / stop reports. Requests use bounded bodies, safe errors, disabled redirects
and the configured server's origin/base path. Passwords remain transient; only the
access token enters Secret Service. Stream credentials are URL-scoped and ephemeral.
Jellyfin server/cache identity includes its user ID so changing accounts cannot reuse
another account's watch data. Tokens retain the existing shared redacted Secret API.

Theater can now keep Plex and Jellyfin connected simultaneously. Shared provider
routing serves existing detail pages, artwork workers and libmpv controls. Provider
and library filters use scoped keys; logical grouping uses both catalogs. Source
selection prefers connected providers and keeps edition/version labels separate.
Watch overlays use shared Catalog policy, with independent server state and no
cross-provider reconciliation. Disconnecting a server cancels its pending playback
requests and stops only its own active session. Plex's browser login is retained.

Validation: Jellyfin HTTP fixtures cover login JSON and auth headers, reverse-proxy
base paths, paging, media metadata, URL-scoped stream credentials, session reports,
server identity checks and safe failure handling. Plex and cache targeted checks
pass; Theater release build passes. Installed binary, launcher and icon without
opening or restarting the application. No live Jellyfin server was supplied or
contacted. The API reference is https://api.jellyfin.org/ (stable OpenAPI schema).

Remaining: live Jellyfin verification; Jellyfin transcoding, external subtitles,
additional-part playback and dedicated collection views; automatic alternate-copy
retry; configurable watch reconciliation with conflict handling. Cross-server
watch-state synchronization remains disabled.


## Jellyfin progressive transcoding

Jellyfin now negotiates progressive HTTP Matroska/H.264/AAC conversion through
POST PlaybackInfo using the selected media source, resume offset and a 1080p /
8 Mbps video / stereo profile. Automatic Direct Play failure and the existing
Transcode selector use the shared playback restart/seek handling. Converted streams
retain whole-item progress while stream timestamps restart at the requested offset.
No new playback controls or persisted authenticated URLs are introduced.

Returned conversion URLs must target the selected item's progressive stream on the
configured origin/base path. Authentication, source/session IDs, offset, timestamp
handling and output bounds are replaced with the client's values. HLS and foreign
URLs are rejected. Playback reports distinguish DirectPlay and Transcode. Cleanup
uses DELETE Videos/ActiveEncodings with both device ID and play-session ID; an
already ended session is idempotent. No server-wide conversion stop is performed.

Targeted Jellyfin HTTP fixtures pass for profile negotiation, offsets, scoped URL
credentials, progress mode, safe denial messages, session cleanup, reverse-proxy
paths and rejection of foreign/incorrect-item/HLS URLs. Plex checks and the Theater
release build also pass. Installed binary, launcher and icon without opening or
restarting Theater. Live transcoding and seek behavior remain unverified; Jellyfin
multi-part playback, external subtitles and reliable watch reconciliation remain.

Primary API references:
https://github.com/jellyfin/jellyfin/blob/v10.11.0/Jellyfin.Api/Controllers/VideosController.cs
https://github.com/jellyfin/jellyfin/blob/v10.11.0/Jellyfin.Api/Controllers/HlsSegmentController.cs


## Jellyfin external text subtitles

Playback sources now carry ephemeral subtitle descriptors, separate from cached
media metadata. Jellyfin exposes SRT/ASS/VTT text sidecars and externally delivered
text tracks through the existing subtitle menu. Native embedded tracks and Off stay
in that same menu. The provider's explicit default/forced choice is respected for
external tracks; unsupported bitmap sidecars are not advertised as text subtitles.

Only the selected subtitle downloads on a worker, bounded to 4 MiB and validated
UTF-8 without NULs. URLs are built against the configured origin/base path rather
than trusting DeliveryUrl. The downloaded content is passed to libmpv in memory;
no credentials or subtitle files are persisted. Stale download/default-selection
callbacks are rejected after replacement, cancellation or another subtitle choice.
External track choices and Off survive conversion seeks; the server trims subtitle
timestamps at the converted stream offset. Plex and local playback share the same
existing controls and retain their embedded track behavior.

Validation: Jellyfin HTTP fixtures check sidecar discovery, filtering unsupported
formats, scoped authentication, malicious DeliveryUrl avoidance, direct/conversion
offsets and lazy subtitle download. The headless shared libmpv fixture verifies
memory subtitle loading and Off. Release build passes. Installed binary, launcher
and icon without opening or restarting Theater. Live subtitle timing, non-UTF-8
sources and bitmap sidecars remain to be verified/implemented as applicable.

References: https://mpv.io/manual/stable/#command-interface-sub-add
https://github.com/jellyfin/jellyfin/blob/v10.11.0/Jellyfin.Api/Controllers/SubtitleController.cs

## Latest implementation notes

Multipart versions retain part durations in backward-compatible cached metadata.
Jellyfin AdditionalParts enriches source identities before resolution. One stream is
opened at a time, avoiding parallel transcoder sessions or eager EDL probing.
Source retries carry an ephemeral playback offset without synchronizing watch state
between providers. Episode indexing extends each provider's existing paged worker.

Reconciliation uses explicit user-selected direction rather than guessing the newest
state when timestamps are absent. A fresh source/target read must match the reviewed
states. Different or ambiguous editions retain their target offset. Jellyfin supports
UserData updates with older-server play-state endpoint fallback; Plex uses its
scrobble/unscrobble and timeline endpoints. Multi-part writes are sequential server
operations, so a network failure can leave a partial update; refresh/review is required
before retrying. These remote APIs do not offer an atomic compare-and-swap, so another
client can still change state after the final check. Automatic synchronization stays
disabled, and all live interoperability checks remain deferred.

## Responsiveness recovery and cinematic content

Implemented after the reported startup lag, inability to close, connection confusion
and visual mismatch. The previous build rebuilt Home plus every grid for every
provider batch on GTK, eagerly initialized libmpv/GL, scanned the artwork directory
after each image, and kept playback-report holds alive until network work finished.
These code paths are corrected; the original desktop freeze was not reproduced
because live/GUI checks remain deferred.

- [x] Lazy playback/renderer initialization; GTK-side renderer teardown followed by
  exclusive client destruction on a worker, leaving Media Player's default unchanged.
- [x] Latest-only catalog worker, revision/page guards, 250 ms coalescing, visible-page
  updates, incremental grid splices and retained Home row/card widgets.
- [x] Mapped-only artwork requests, deduplicated downloads, consumer/shutdown
  cancellation, offline-to-online retry and rate-limited cache trimming.
- [x] Separate connection/indexing states, Retry/Reconnect, bounded keyring lookup
  and short Plex startup probes. Preserve credentials and cached titles on failure.
- [x] Cancel/invalidate delayed callbacks on close; reporting holds expire after two
  seconds even when the server never replies.
- [x] Full-width backdrop hero, direct Play/Resume, separate recent movie/TV rows,
  backdrop-led details with secondary source options, native shared Nixe chrome,
  theme-derived readability shading and existing Media Player controls/F1.

Focused checks pass for request coalescing/cancellation, stale results, credential
process expiry/reaping, final reporting hold expiry, Plex HTTP reconnect and headless
libmpv teardown. Cached Home preparation: 3,577 records in ~28 ms. Synthetic view
preparation: 3,600 in ~14 ms; 20,000 in ~71 ms (debug tests, worker time only).
Theater release build and Media Player compatibility check pass. Live Plex connection,
GUI responsiveness, Wayland presentation and final visual layout remain unverified
under the instruction to defer live checks. Installed binary, launcher and icon
without opening or restarting the application.

## Larger artwork, TV context, Discover and Playlists

- [x] Home hero 480 px / narrow 400 px, stronger title, default 180 px posters.
- [x] Persistent Small/Medium/Large poster size; resize existing native widgets.
- [x] Sidebar Discover and Playlists replace Now playing; active playback has a
  temporary status action and retains the exact shared Media Player controls.
- [x] Provider TV context and season indexing; show / episode / season+episode
  labels; season → series → placeholder artwork fallback, excluding screenshots.
- [x] Episode-based Recently Added TV, with a season card only for known complete
  batches of distinct episodes added within 24 hours. Unknown counts stay individual.
- [x] Library-only Discover with provider/library filters and stable daily choices.
- [x] Common paged playlist provider interfaces; read-only Plex/Jellyfin lists.
- [x] Durable local SQLite playlists spanning providers, ordered duplicate entries,
  transactional edits, create/rename/delete/add/remove/reorder and offline retention.
- [x] Virtualized entry view; ordered playback with shared Previous/Next, clean EOF
  advancement, multipart boundaries, unavailable-item skipping and cancellation guards.

Model/cache/provider/application targeted checks pass, including real HTTP fixtures
for each provider's playlist paging, duplicate entry order, server isolation and TV
artwork mapping. Live servers and GUI remain unchecked under the existing instruction.
The release build passes. Installed the binary, launcher and icon without opening
or restarting Theater.

## Poster grids and cache-first startup

- [x] Playlists use the shared resizable poster cards with titles beneath, native
  server artwork/composites, and virtualized grid activation.
- [x] Collections/playlists fall back to member-poster mosaics cached as PNGs;
  themed native monogram covers replace blank placeholders while images load.
- [x] Dedicated disk artwork readers operate independently of the bounded network
  queue; native cover cache hits also bypass downloads.
- [x] Prepared page snapshots restore before credential/network work; metadata
  batches update the current page without repeatedly invalidating its cached render.
- [x] View snapshots include provider identity and filter/sort scope. Empty pending
  or offline states retain saved content; ephemeral search queries are not persisted.
- [x] Last library page/filter/sort restore by default, with a settings switch to
  use the suite start behavior instead. Playback is never started automatically.
- [x] Existing metadata caches avoid schema writes on each connection.

Targeted application/provider/cache checks pass, including mosaic tile geometry,
snapshot isolation/restoration, poster/composite metadata and older saved records.
The shared workspace temporarily contains an incomplete Capture app; validation and
release compilation use an isolated copy of Theater and its shared crates, leaving
that concurrent work untouched. Live/GUI checks remain deferred. The release build passes. Installed the binary,
launcher and icon without opening or restarting Theater.

## Rich details and library queries

- [x] Optional shared metadata models and Plex/Jellyfin parsing for source-specific
  ratings, credits, genres, dates, certifications and per-version technical facets.
- [x] Background TMDB/MDBList enrichment with separate SQLite caching, bounded
  requests, refresh/retry windows, optional Secret Service credentials and attribution.
- [x] Cast/person pages, biographies, filmography, owned related titles/collections,
  TV facts/next unwatched, trailers and expandable source/media information.
- [x] Ascending/descending library sorts, stable shuffle, composable native facet
  panel, range presets, vote thresholds, removable chips and coverage counts.
- [x] Independent Movies/TV choices, durable local half-star personal ratings and
  named saved views. Technical facets require a matching real version.

External enrichment requires optional credentials in Settings → Metadata. Missing
fields remain absent; server metadata and cached pages work without those services.
No watch-state synchronization policy changed. Live checks remain deferred.

Rich-details/query validation: targeted Theater/provider fixtures pass, including
source-separated ratings, missing vote counts, same-version technical filtering,
legacy snapshot defaults and saved-query serialization. Release compilation passes.
Installed the binary, launcher and icon; did not open or restart Theater.
