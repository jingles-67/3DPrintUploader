#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
version="$(tr -d '\r\n' < "$root/VERSION")"
output_dir="${1:-$root/dist/release-assets}"
architecture="$(dpkg --print-architecture 2>/dev/null || uname -m)"
package_root="$root/build/linux-deb"

mkdir -p "$output_dir"
python3 -m PyInstaller --noconfirm --clean --distpath "$root/dist/linux" \
    --workpath "$root/build/pyinstaller-linux" "$root/packaging/linux.spec"

rm -rf "$package_root"
mkdir -p \
    "$package_root/DEBIAN" \
    "$package_root/usr/bin" \
    "$package_root/usr/share/applications" \
    "$package_root/usr/share/icons/hicolor/256x256/apps" \
    "$package_root/usr/share/doc/3d-print-uploader"

install -m 755 "$root/dist/linux/3d-print-uploader" \
    "$package_root/usr/bin/3d-print-uploader"
install -m 644 "$root/packaging/linux/3d-print-uploader.desktop" \
    "$package_root/usr/share/applications/3d-print-uploader.desktop"
install -m 644 "$root/assets/icons/app_icon.png" \
    "$package_root/usr/share/icons/hicolor/256x256/apps/3d-print-uploader.png"
install -m 644 "$root/packaging/linux/README-Linux.txt" \
    "$package_root/usr/share/doc/3d-print-uploader/README"
sed -e "s/@VERSION@/$version/g" -e "s/@ARCH@/$architecture/g" \
    "$root/packaging/linux/control.in" > "$package_root/DEBIAN/control"

deb_name="3D-Print-Uploader-$version-Ubuntu-LinuxMint-$architecture.deb"
dpkg-deb --build --root-owner-group "$package_root" "$output_dir/$deb_name"

portable_root="$root/build/3D-Print-Uploader-$version-Linux-$architecture"
rm -rf "$portable_root"
mkdir -p "$portable_root"
install -m 755 "$root/dist/linux/3d-print-uploader" \
    "$portable_root/3d-print-uploader"
install -m 644 "$root/packaging/linux/README-Linux.txt" \
    "$portable_root/README.txt"
tar -C "$root/build" -czf \
    "$output_dir/3D-Print-Uploader-$version-Linux-Portable-$architecture.tar.gz" \
    "$(basename "$portable_root")"

echo "Linux release files created in $output_dir"
