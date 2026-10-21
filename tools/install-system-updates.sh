#!/usr/bin/env bash
# Install only the reviewed, checksummed local migration artifacts.
set -euo pipefail
[[ $EUID == 0 ]] || { echo 'Administrator authorization is required.' >&2; exit 1; }
sha256sum --check <<'CHECKSUMS'
0520be8841102c2dac6df096b7f332b8871ad48c707043f0ebae0d179a6c81b6  /home/ken/Projects/nixe/target/packages/nixe-git-0.1.0-1-x86_64.pkg.tar.zst
a09738b80f7534996959952ec5061ac41d1ca6dfe745693abc80a01d84b87915  /home/ken/Projects/nixe/target/release/nixe-store-helper
1f37a28ffb8b0bd96c09afa4916ed9d5006f5d6498923edb82afd08b587f8832  /home/ken/Projects/nixe-migration-97c1899-apps-complete/nixe-store/apps/store/data/io.github.design_nexus.nixe.store.policy
e408cc20e5819205752e77bf4ad8851929a895de1bb961b4b3119deebd2c408a  /home/ken/Projects/nixe/apps/assistant/target/release/nixe-assistant-helper
5eda9d600fbbd5566ca3a104b00bdfb735b04f0f295bb890636770066feba32a  /home/ken/Projects/nixe-migration-97c1899-apps-complete/nixe-assistant/apps/assistant/crates/assistant-privileged/data/io.github.design_nexus.nixe.assistant.policy
CHECKSUMS
pacman -U --noconfirm /home/ken/Projects/nixe/target/packages/nixe-git-0.1.0-1-x86_64.pkg.tar.zst
install -d -m 755 /usr/local/lib/nixe-store /var/lib/nixe-store /usr/local/lib/nixe-assistant
install -m 755 /home/ken/Projects/nixe/target/release/nixe-store-helper /usr/local/lib/nixe-store/nixe-store-helper
install -m 644 /home/ken/Projects/nixe-migration-97c1899-apps-complete/nixe-store/apps/store/data/io.github.design_nexus.nixe.store.policy /usr/share/polkit-1/actions/io.github.design_nexus.nixe.store.policy
install -m 755 /home/ken/Projects/nixe/apps/assistant/target/release/nixe-assistant-helper /usr/local/lib/nixe-assistant/nixe-assistant-helper
install -m 644 /home/ken/Projects/nixe-migration-97c1899-apps-complete/nixe-assistant/apps/assistant/crates/assistant-privileged/data/io.github.design_nexus.nixe.assistant.policy /usr/share/polkit-1/actions/io.github.design_nexus.nixe.assistant.policy
echo "Installed Git package and Store/Assistant helpers; no applications or services restarted."
