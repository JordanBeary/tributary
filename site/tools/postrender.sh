#!/bin/sh
# Quarto post-render hook: strip the bootstrap-icons stylesheet link. Quarto
# emits it unconditionally, but no page uses an icon glyph (the navbar link
# is text by design), so the tag is a pure render-blocking cost.
set -eu

find _site -name '*.html' -exec sed -i.bak '/bootstrap-icons\.css/d' {} \;
find _site -name '*.html.bak' -delete
