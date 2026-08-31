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
<div class="vc-brand">
  <span class="vc-mark">ViralCutter</span>
  <span class="vc-tagline">{tagline}</span>
</div>
"""
