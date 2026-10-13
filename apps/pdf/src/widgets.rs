//! Nexus-style building blocks: pages, groups and option rows.

pub use nixe_ui::widgets::*;

use gtk::prelude::*;
use std::rc::Rc;

// ---------- Page / group ----------

pub struct Page {
    pub root: gtk::ScrolledWindow,
    pub body: gtk::Box,
}

/// A page. Its name shows in the top bar (or the settings dialog's header), so
/// the page itself starts straight with its content.
pub fn page(section: &str) -> Page {
    let body = gtk::Box::new(gtk::Orientation::Vertical, 0);
    body.add_css_class("settings-page");
    body.add_css_class(&format!("page-{section}"));

    body.set_hexpand(true);

    let root = gtk::ScrolledWindow::builder()
        .hscrollbar_policy(gtk::PolicyType::Never)
        // Scrolls with wheel, trackpad and keyboard; no visible scrollbar.
        .vscrollbar_policy(gtk::PolicyType::External)
        .child(&body)
        .vexpand(true)
        .build();
    Page { root, body }
}

impl Page {
    /// For pages whose content scrolls itself (tables): the page stops scrolling
    /// and hands its height to the last child.
    pub fn fill(&self) {
        self.root.set_vscrollbar_policy(gtk::PolicyType::Never);
        self.body.set_vexpand(true);
        self.body.add_css_class("fill");
    }

    /// No header and no padding: the page is all content (the player).
    pub fn bare(&self) {
        self.body.add_css_class("bare");
    }

    pub fn group(&self, title: &str) -> Group {
        let wrapper = gtk::Box::new(gtk::Orientation::Vertical, 0);
        wrapper.add_css_class("settings-group");
        // The settings dialog lists groups by this name.
        wrapper.set_widget_name(title);
        if !title.is_empty() {
            let l = gtk::Label::new(Some(&title.to_uppercase()));
            l.add_css_class("group-title");
            l.set_xalign(0.0);
            wrapper.append(&l);
        }
        // Rows join into one card, split by hairlines.
        let list = gtk::Box::new(gtk::Orientation::Vertical, 0);
        list.add_css_class("group-list");
        wrapper.append(&list);
        self.body.append(&wrapper);
        Group { wrapper, list }
    }
}

#[derive(Clone)]
pub struct Group {
    pub wrapper: gtk::Box,
    pub list: gtk::Box,
}

impl Group {
    pub fn add(&self, w: &impl IsA<gtk::Widget>) {
        self.list.append(w);
    }

    pub fn note(&self, text: &str) {
        let l = gtk::Label::new(None);
        l.set_markup(text);
        l.add_css_class("group-note");
        l.set_xalign(0.0);
        l.set_wrap(true);
        // Notes sit just under the group title.
        self.wrapper.insert_child_after(&l, self.wrapper.first_child().as_ref());
    }
}

// ---------- Config files and bar buttons ----------

// ---------- Rows ----------

/// Ask for a line of text in a small dialog ("Cancel" first, then the action).
pub fn ask_text(title: &str, desc: &str, initial: &str, confirm: &str, on_ok: impl Fn(String) + 'static) -> gtk::Box {
    let (dialog, card) = dialog(title, 420);
    if !desc.is_empty() {
        let d = label(desc, "dim");
        d.set_wrap(true);
        card.append(&d);
    }
    let entry = gtk::Entry::new();
    entry.set_text(initial);
    entry.set_activates_default(false);
    card.append(&entry);
    let extra = vbox(6);
    card.append(&extra);
    let buttons = hbox(8);
    buttons.set_halign(gtk::Align::End);
    buttons.set_margin_top(6);
    let cancel = gtk::Button::with_label("Cancel");
    let ok = gtk::Button::with_label(confirm);
    ok.add_css_class("suggested-action");
    buttons.append(&cancel);
    buttons.append(&ok);
    card.append(&buttons);
    let d = dialog.clone();
    cancel.connect_clicked(move |_| d.close());
    let on_ok = Rc::new(on_ok);
    let submit = {
        let (d, e) = (dialog.clone(), entry.clone());
        move || {
            let text = e.text().trim().to_string();
            if text.is_empty() {
                e.add_css_class("error");
                return;
            }
            d.close();
            on_ok(text);
        }
    };
    let s2 = submit.clone();
    ok.connect_clicked(move |_| s2());
    entry.connect_activate(move |_| submit());
    dialog.present();
    entry.grab_focus();
    entry.select_region(0, -1);
    extra
}

/// Pack a flow box's children tightly: as many columns as fit `scroll`'s width, each
/// `cell_w` pixels wide, left-aligned, re-flowed whenever the window is resized.
pub fn pack_flow(flow: &gtk::FlowBox, scroll: &gtk::ScrolledWindow, cell_w: i32) {
    flow.set_halign(gtk::Align::Start);
    flow.set_homogeneous(true);
    let fit = {
        let flow = flow.clone();
        move |width: f64| {
            let cols = ((width / f64::from(cell_w)).floor() as u32).clamp(1, 24);
            flow.set_min_children_per_line(cols);
            flow.set_max_children_per_line(cols);
        }
    };
    fit(900.0);
    let f = fit.clone();
    scroll.hadjustment().connect_page_size_notify(move |a| {
        if a.page_size() > 1.0 {
            f(a.page_size());
        }
    });
}
