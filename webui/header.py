import os
import sys

# Necessary if this file is imported from app.py which is in the same dir but we need root for i18n
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
WORKING_DIR = os.path.dirname(CURRENT_DIR)
sys.path.append(WORKING_DIR)

from i18n.i18n import I18nAuto
i18n = I18nAuto()

badges = """
<div style="display: flex; align-items: center; justify-content: center;">
<span style="margin-right: 5px;"> 

[ ![GitHub](https://img.shields.io/badge/github-%23121011.svg?style=for-the-badge&logo=github&logoColor=white) ](https://github.com/rafaelGodoyEbert)
 
</span>
<span style="margin-right: 5px;"> 

[ ![X](https://img.shields.io/badge/X-%23000000.svg?style=for-the-badge&logo=X&logoColor=white) ](https://twitter.com/GodoyEbert)
 
</span>
<span style="margin-right: 5px;"> 

[ ![Instagram](https://img.shields.io/badge/Instagram-%23E4405F.svg?style=for-the-badge&logo=Instagram&logoColor=white) ](https://www.instagram.com/rafael.godoy.ebert)
 
</span>

<!-- COLAB ICON ADDED HERE -->
<span style="margin-right: 5px;">

[ ![Open In Colab](https://img.shields.io/badge/Open%20in%20Colab-%23F9AB00.svg?style=for-the-badge&logo=googlecolab&logoColor=white) ]("https://colab.research.google.com/drive/1UZKzeqjIeEyvq9nPx7s_4mU6xlkZQn_R")

</span>
<!-- END OF ADDITION -->

<span>

[![](https://dcbadge.limes.pink/api/server/tAdPHFAbud)](https://discord.gg/tAdPHFAbud)

</span>
</div>
"""

description = f"""
<div style="text-align: center;">

<h1>ViralCutter</h1>
<p style="font-size: 1.1em; margin-bottom: 20px;">{i18n('Welcome to ViralCutter! The ultimate tool to transform long videos into viral clips with the power of AI.')}</p>

<div style="display: inline-block; text-align: left; background: rgba(255, 255, 255, 0.05); padding: 20px; border-radius: 10px; margin-bottom: 20px;">
<p style="margin-bottom: 10px;"><strong>{i18n('Here you can:')}</strong></p>
<ul style="margin: 0; padding-left: 20px;">
<li>✂️ <strong>{i18n('Automatic Cuts')}</strong>: {i18n('Identify and cut the best moments based on virality.')}</li>
<li>📝 <strong>{i18n('Dynamic Subtitles')}</strong>: {i18n('Create aesthetic subtitles (Hormozi Style) automatically.')}</li>
<li>🤖 <strong>{i18n('Advanced AI')}</strong>: {i18n('Integrated support for')} <strong>Gemini</strong> and <strong>G4F</strong>.</li>
<li>📱 <strong>{i18n('Vertical Focus')}</strong>: {i18n('Smart face detection for vertical videos (TikTok/Shorts/Reels).')}</li>
</ul>
</div>

<br>
<div style="display: flex; align-items: center; justify-content: center; gap: 10px;">
    <a href='https://www.youtube.com/@aihubbrasil' target='_blank'>
        <img src="https://img.shields.io/badge/AI_HUB_Brasil-FF0000?style=for-the-badge&logo=youtube&logoColor=white" alt="AI HUB Brasil YouTube">
    </a>
    <a href='https://www.youtube.com/@godoyy' target='_blank'>
        <img src="https://img.shields.io/badge/Godoyy_Personal_Channel-FF0000?style=for-the-badge&logo=youtube&logoColor=white" alt="Godoyy Personal Channel">
    </a>
</div>
<br>{i18n('This project was developed for the AI HUB Brazil community.')}
</div>
"""