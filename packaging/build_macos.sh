#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
version="$(tr -d '\r\n' < "$root/VERSION")"
architecture="$(uname -m)"
output_dir="${1:-$root/dist/release-assets}"
dist_dir="$root/dist/macos"
stage_dir="$root/build/macos-dmg"
dmg_path="$output_dir/3D-Print-Uploader-$version-macOS-$architecture.dmg"

mkdir -p "$output_dir"
python3 -m PyInstaller --noconfirm --clean --distpath "$dist_dir" \
    --workpath "$root/build/pyinstaller-macos" "$root/packaging/macos.spec"

# Ad-hoc signing keeps the nested bundle internally consistent. Public builds
# can replace this with Developer ID signing and Apple notarization later.
codesign --deep --force --sign - "$dist_dir/3D Print Uploader.app"

rm -rf "$stage_dir"
mkdir -p "$stage_dir"
cp -R "$dist_dir/3D Print Uploader.app" "$stage_dir/"
ln -s /Applications "$stage_dir/Applications"
rm -f "$dmg_path"
hdiutil create -volname "3D Print Uploader $version" -srcfolder "$stage_dir" \
    -ov -format UDZO "$dmg_path"

echo "macOS release file created: $dmg_path"
