//! PDF's tools on the control interface (`nixe_core::control`), for Nixe Assistant: open a
//! document, read its text, find words in it, and turn to a page. Nothing is edited.

use crate::{doc, viewer};
use nixe_core::control::{self, text};
use serde_json::{json, Value};

pub fn tools() -> Value {
    json!([
        {"name": "pdf.open", "description": "Open a PDF (inside the home folder) in the PDF window, optionally at a page (from 1).", "inputSchema": {"type": "object", "properties": {"path": {"type": "string"}, "page": {"type": "integer", "minimum": 1}}, "required": ["path"]}},
        {"name": "pdf.read", "description": "Read the text of the open PDF: a page (from 1; the one showing if none) and up to 4 after it.", "inputSchema": {"type": "object", "properties": {"page": {"type": "integer", "minimum": 1}, "pages": {"type": "integer", "minimum": 1, "maximum": 5}}}},
        {"name": "pdf.search", "description": "Find words in the open PDF: the pages they're on and how often.", "inputSchema": {"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]}},
        {"name": "pdf.go_to", "description": "Turn the open PDF to a page (from 1).", "inputSchema": {"type": "object", "properties": {"page": {"type": "integer", "minimum": 1}}, "required": ["page"]}},
    ])
}

fn current() -> Result<std::rc::Rc<doc::Doc>, String> {
    doc::current().ok_or_else(|| "no PDF is open".into())
}

fn state(d: &doc::Doc) -> Value {
    json!({"title": d.title(), "path": d.path(), "pages": d.n_pages(), "showing": d.page() + 1})
}

/// A page number from 1 as an index, checked against the document.
fn index(d: &doc::Doc, page: Option<i64>) -> Result<usize, String> {
    let i = match page {
        Some(p) if p >= 1 => (p - 1) as usize,
        Some(_) => return Err("pages start at 1".into()),
        None => d.page(),
    };
    if i >= d.n_pages() {
        return Err(format!("it has {} pages", d.n_pages()));
    }
    Ok(i)
}

pub fn handle(name: &str, args: Value) -> Result<Value, String> {
    match name {
        "pdf.open" => {
            let path = control::home_path(&text(&args, "path")?)?;
            if !path.is_file() {
                return Err("no such file".into());
            }
            let page = args["page"].as_u64().map(|p| p.saturating_sub(1) as usize);
            doc::open(&path, page);
            let d = current()?;
            if d.path() != path {
                return Err("couldn't open it".into());
            }
            Ok(json!({"document": state(&d)}))
        }
        "pdf.read" => {
            let d = current()?;
            let first = index(&d, args["page"].as_i64())?;
            let count = args["pages"].as_u64().unwrap_or(1).clamp(1, 5) as usize;
            let pdf = d.pdf();
            let pages: Vec<Value> = (first..(first + count).min(d.n_pages()))
                .map(|i| json!({"page": i + 1, "text": pdf.page(i as i32).and_then(|p| p.text()).map(|t| t.to_string()).unwrap_or_default()}))
                .collect();
            Ok(json!({"document": state(&d), "pages": pages, "untrusted_content": true}))
        }
        "pdf.search" => {
            let words = text(&args, "text")?;
            if words.trim().is_empty() {
                return Err("text is empty".into());
            }
            let d = current()?;
            let pdf = d.pdf();
            let mut hits = Vec::new();
            let mut total = 0;
            for i in 0..d.n_pages() {
                let n = pdf.page(i as i32).map(|p| p.find_text(&words).len()).unwrap_or(0);
                if n > 0 {
                    total += n;
                    if hits.len() < 50 {
                        hits.push(json!({"page": i + 1, "matches": n}));
                    }
                }
            }
            Ok(json!({"document": state(&d), "matches": total, "pages": hits}))
        }
        "pdf.go_to" => {
            let d = current()?;
            let i = index(&d, args["page"].as_i64())?;
            viewer::jump(i);
            Ok(json!({"document": state(&d)}))
        }
        _ => Err(format!("unknown tool {name}")),
    }
}
