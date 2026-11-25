#!/bin/zsh
# Double-click in Finder to review the electronics and enclosure together.
set -eu
project_dir=${0:A:h}

# Macs with KiCad 9 and 10 side by side can associate both with the same files.
kicad_app=""
for app in "/Applications/KiCad 10/KiCad.app" /Applications/KiCad/KiCad.app /Applications/KiCad.app; do
    [[ -d "$app" ]] || continue
    version=$(/usr/libexec/PlistBuddy -c 'Print :CFBundleShortVersionString' "$app/Contents/Info.plist")
    if [[ "$version" == 10.* ]]; then
        kicad_app="$app"
        break
    fi
done

/usr/bin/open -a FreeCAD "$project_dir/Mechanical/SignalStreamer-enclosure.FCStd"
if [[ -z "$kicad_app" ]]; then
    print -u2 "Open KiCad/SignalStreamer.kicad_pro with KiCad 10. No KiCad 10 installation was found in /Applications."
    exit 1
fi
/usr/bin/open -a "$kicad_app" "$project_dir/KiCad/SignalStreamer.kicad_pro"
