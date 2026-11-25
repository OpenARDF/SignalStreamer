#!/usr/bin/env bash
set -euo pipefail

# Each signed release image includes the libraries and Python ABI for its CAD tool.
mount_release() {
    local name=$1 url=$2 sha=$3 image="$RUNNER_TEMP/$1.dmg" mount="$RUNNER_TEMP/$1"
    curl --fail --location --silent --show-error --retry 3 --output "$image" "$url" || return 1
    echo "$sha  $image" | shasum -a 256 --check --status || return 1
    mkdir -p "$mount" || return 1
    hdiutil attach "$image" -readonly -nobrowse -mountpoint "$mount" >/dev/null || return 1
    local app
    app=$(find "$mount" -maxdepth 3 -type d -name "$name.app" -print -quit)
    test -n "$app" && test -d "$app/Contents" || return 1
    echo "$app/Contents"
}

kicad=$(mount_release KiCad \
    https://github.com/KiCad/kicad-source-mirror/releases/download/10.0.8/kicad-unified-universal-10.0.8.dmg \
    501d3e2933a385f1833497469f55326662df7e5d40401239826c40d6fa583f16)
freecad=$(mount_release FreeCAD \
    https://github.com/FreeCAD/FreeCAD/releases/download/1.1.4/FreeCAD_1.1.4-macOS-arm64-py311.dmg \
    071343b4abb70492b75c973f41eaf1d2528f9b9c7ea018d22a4f46ae14d27ac0)

# Initialize the same global library tables the GUI installs on first launch.
config="$RUNNER_TEMP/kicad-config"
mkdir -p "$config/10.0"
cp "$kicad/SharedSupport/template/"{fp-lib-table,sym-lib-table} "$config/10.0/"
# The bundled Fontconfig predates some rules in Homebrew's global configuration.
# Use the host's installed fonts directly for both KiCad and the assembly renderer.
cat >"$RUNNER_TEMP/fonts.conf" <<'XML'
<?xml version="1.0"?>
<!DOCTYPE fontconfig SYSTEM "urn:fontconfig:fonts.dtd">
<fontconfig>
  <dir>/System/Library/Fonts</dir>
  <dir>/Library/Fonts</dir>
  <cachedir prefix="xdg">fontconfig</cachedir>
</fontconfig>
XML
command -v rsvg-convert >/dev/null || brew install librsvg
{
    echo "FONTCONFIG_FILE=$RUNNER_TEMP/fonts.conf"
    echo "KICAD_CONFIG_HOME=$config"
    echo "KICAD_CLI=$kicad/MacOS/kicad-cli"
    echo "KICAD_PYTHON=$kicad/Frameworks/Python.framework/Versions/Current/bin/python3"
    echo "FREECAD_PYTHON=$freecad/Resources/bin/python"
    echo "FREECAD_LIB=$freecad/Resources/lib"
} >>"$GITHUB_ENV"
