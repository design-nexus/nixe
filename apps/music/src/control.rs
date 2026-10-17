//! Music's tools on the control interface (`nixe_core::control`), for Nixe Assistant: find
//! and play from the library, queue, and read what's playing, without the window.

use crate::library::{store, Track};
use crate::player::{self, queue::Repeat, State};
use nixe_core::control::{text, Reply};
use serde_json::{json, Value};
use std::path::PathBuf;
use std::rc::Rc;

pub fn tools() -> Value {
    let what = json!({"enum": ["track", "album", "artist", "playlist"]});
    json!([
        {"name": "music.search", "description": "Search the music library: tracks, albums, artists and playlists matching the words.", "inputSchema": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}},
        {"name": "music.play", "description": "Play a track, album, artist or playlist from the library (by name), optionally shuffled.", "inputSchema": {"type": "object", "properties": {"what": what, "name": {"type": "string"}, "shuffle": {"type": "boolean"}}, "required": ["what", "name"]}},
        {"name": "music.queue", "description": "Add a track, album, artist or playlist to the queue: next, or at the end.", "inputSchema": {"type": "object", "properties": {"what": what, "name": {"type": "string"}, "next": {"type": "boolean"}}, "required": ["what", "name"]}},
        {"name": "music.status", "description": "What Music is playing: track, artist, album, playing or paused, shuffle, repeat, what's next.", "inputSchema": {"type": "object", "properties": {}}},
        {"name": "music.control", "description": "Play, pause, toggle, next, previous or stop in Music; or set shuffle on/off.", "inputSchema": {"type": "object", "properties": {"action": {"enum": ["play", "pause", "toggle", "next", "previous", "stop", "shuffle_on", "shuffle_off"]}}, "required": ["action"]}},
    ])
}

fn track(t: &Track) -> Value {
    json!({"title": t.title, "artist": t.artist, "album": t.album, "seconds": t.duration.round()})
}

/// How well `name` fits `query`: 3 the same, 2 starts with it, 1 contains it.
fn fit(name: &str, query: &str) -> u8 {
    let (n, q) = (name.to_lowercase(), query.trim().to_lowercase());
    if q.is_empty() {
        0
    } else if n == q {
        3
    } else if n.starts_with(&q) {
        2
    } else if n.contains(&q) {
        1
    } else {
        0
    }
}

/// The one best match among `items`, or an error naming the candidates.
fn best<T>(items: Vec<T>, name: &str, label: impl Fn(&T) -> String) -> Result<T, String> {
    let top = items.iter().map(|i| fit(&label(i), name)).max().unwrap_or(0);
    if top == 0 {
        return Err(format!("nothing in the library matches “{name}”"));
    }
    let mut found: Vec<T> = items.into_iter().filter(|i| fit(&label(i), name) == top).collect();
    if found.len() > 1 {
        let names: Vec<String> = found.iter().take(5).map(&label).collect();
        let mut unique = names.clone();
        unique.dedup();
        if unique.len() > 1 {
            return Err(format!("several match: {}", names.join("; ")));
        }
    }
    Ok(found.remove(0))
}

fn paths(tracks: &[Rc<Track>]) -> Vec<PathBuf> {
    tracks.iter().map(|t| t.path.clone()).collect()
}

/// The tracks `what`/`name` names, handed to `then` (a playlist is read from the database).
fn resolve(args: &Value, then: impl FnOnce(Result<(String, Vec<Rc<Track>>), String>) + 'static) {
    let (what, name) = match (text(args, "what"), text(args, "name")) {
        (Ok(w), Ok(n)) => (w, n),
        (Err(e), _) | (_, Err(e)) => return then(Err(e)),
    };
    let found = match what.as_str() {
        "track" => best(store::tracks(), &name, |t| t.title.clone()).map(|t| (format!("{} by {}", t.title, t.artist), vec![t])),
        "album" => best(store::albums(), &name, |a| a.title.clone()).map(|a| (format!("{} by {}", a.title, a.artist), a.tracks.clone())),
        "artist" => best(store::artists(), &name, |b| b.name.clone()).map(|b| (b.name.clone(), b.albums.iter().flat_map(|a| a.tracks.clone()).collect())),
        "playlist" => match best(store::playlists(), &name, |p| p.name.clone()) {
            Ok(p) => {
                let label = p.name.clone();
                return store::playlist_tracks(p.id, move |tracks| then(Ok((label, tracks))));
            }
            Err(e) => Err(e),
        },
        other => Err(format!("unknown kind {other}")),
    };
    then(found)
}

fn status() -> Value {
    let state = match player::state() {
        State::Playing => "playing",
        State::Paused => "paused",
        State::Stopped => "stopped",
    };
    let repeat = match player::repeat() {
        Repeat::Off => "off",
        Repeat::All => "all",
        Repeat::One => "one",
    };
    let next: Vec<Value> = player::upcoming(5).iter().map(|p| track(&store::track_for(p))).collect();
    json!({
        "state": state,
        "track": player::current().map(|t| track(&t)),
        "position": player::position().round(),
        "shuffle": player::shuffle(),
        "repeat": repeat,
        "next": next,
    })
}

pub fn handle(name: &str, args: Value, reply: Reply) {
    match name {
        "music.search" => reply((|| {
            let q = text(&args, "query")?;
            let hit = |s: &str| fit(s, &q) > 0;
            let tracks: Vec<Value> = store::tracks().iter().filter(|t| hit(&t.title)).take(10).map(|t| track(t)).collect();
            let albums: Vec<Value> = store::albums().iter().filter(|a| hit(&a.title)).take(10).map(|a| json!({"title": a.title, "artist": a.artist, "year": a.year})).collect();
            let artists: Vec<String> = store::artists().into_iter().filter(|b| hit(&b.name)).take(10).map(|b| b.name).collect();
            let playlists: Vec<String> = store::playlists().into_iter().filter(|p| hit(&p.name)).take(10).map(|p| p.name).collect();
            Ok(json!({"tracks": tracks, "albums": albums, "artists": artists, "playlists": playlists}))
        })()),
        "music.play" => {
            let shuffle = args["shuffle"] == true;
            resolve(&args, move |found| {
                reply(found.and_then(|(label, tracks)| {
                    if tracks.is_empty() {
                        return Err(format!("{label} has no tracks"));
                    }
                    if shuffle {
                        player::shuffle_tracks(paths(&tracks));
                    } else {
                        player::play_tracks(paths(&tracks), 0);
                    }
                    Ok(json!({"playing": label, "tracks": tracks.len(), "shuffled": shuffle}))
                }))
            });
        }
        "music.queue" => {
            let next = args["next"] == true;
            resolve(&args, move |found| {
                reply(found.and_then(|(label, tracks)| {
                    if tracks.is_empty() {
                        return Err(format!("{label} has no tracks"));
                    }
                    if next {
                        player::play_next(paths(&tracks));
                    } else {
                        player::enqueue(paths(&tracks));
                    }
                    Ok(json!({"queued": label, "tracks": tracks.len(), "next": next}))
                }))
            });
        }
        "music.status" => reply(Ok(status())),
        "music.control" => reply((|| {
            match text(&args, "action")?.as_str() {
                "play" => player::play(),
                "pause" => player::pause(),
                "toggle" => player::toggle(),
                "next" => player::next(),
                "previous" => player::previous(),
                "stop" => player::stop(),
                "shuffle_on" => player::set_shuffle(true),
                "shuffle_off" => player::set_shuffle(false),
                other => return Err(format!("unknown action {other}")),
            }
            Ok(status())
        })()),
        _ => reply(Err(format!("unknown tool {name}"))),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn best_match_prefers_exact_then_start() {
        let names = || vec!["Blue Train".to_string(), "Blue".to_string(), "Kind of Blue".to_string()];
        assert_eq!(best(names(), "blue", |s| s.clone()).unwrap(), "Blue");
        assert_eq!(best(names(), "blue t", |s| s.clone()).unwrap(), "Blue Train");
        assert_eq!(best(names(), "kind", |s| s.clone()).unwrap(), "Kind of Blue");
        assert!(best(names(), "red", |s| s.clone()).is_err());
        let two = vec!["Live at Leeds".to_string(), "Live at Pompeii".to_string()];
        assert!(best(two, "live", |s| s.clone()).unwrap_err().starts_with("several match"));
    }
}
