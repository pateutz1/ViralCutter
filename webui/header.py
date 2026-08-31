import os
import sys

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
WORKING_DIR = os.path.dirname(CURRENT_DIR)
sys.path.append(WORKING_DIR)

from i18n.i18n import I18nAuto
i18n = I18nAuto()


def brand_html():
    tagline = i18n("Turn long videos into short reels.")
    return f"""
<a class="vc-skip-link" href="#vc-workspace">Skip to workspace</a>
<div class="vc-brand" aria-label="ViralCutter home">
  <span class="vc-brand-symbol" aria-hidden="true">
    <svg viewBox="0 0 32 32" role="img">
      <path d="M8 7.5h7.5L24 16l-8.5 8.5H8l8.5-8.5L8 7.5Z" />
      <path d="M17.5 7.5H24v6.5" />
    </svg>
  </span>
  <span class="vc-brand-copy">
    <span class="vc-mark">ViralCutter</span>
    <span class="vc-tagline">{tagline}</span>
  </span>
  <span class="vc-local-badge"><i></i>Local workspace</span>
</div>
"""
