SETTINGS_SCHEMA_VERSION = 2


FACE_PRESETS = {
    "Default (Balanced)": {"thresh": 0.30, "two_face": 0.60, "conf": 0.50, "dead_zone": 45},
    "Stable (Focus Main)": {"thresh": 0.45, "two_face": 0.75, "conf": 0.60, "dead_zone": 70},
    "Sensitive (Catch All)": {"thresh": 0.10, "two_face": 0.45, "conf": 0.35, "dead_zone": 25},
    "High Precision": {"thresh": 0.35, "two_face": 0.65, "conf": 0.75, "dead_zone": 45},
    "Action (Fast Movement)": {"thresh": 0.20, "two_face": 0.55, "conf": 0.45, "dead_zone": 35},
    "Two Person / Interview": {"thresh": 0.20, "two_face": 0.55, "conf": 0.50, "dead_zone": 45},
}


LEGACY_FACE_PRESETS = {
    "Default (Balanced)": {"thresh": 0.35, "two_face": 0.60, "conf": 0.40, "dead_zone": 150},
    "Stable (Focus Main)": {"thresh": 0.60, "two_face": 0.80, "conf": 0.60, "dead_zone": 200},
    "Sensitive (Catch All)": {"thresh": 0.10, "two_face": 0.40, "conf": 0.30, "dead_zone": 100},
    "High Precision": {"thresh": 0.40, "two_face": 0.65, "conf": 0.75, "dead_zone": 150},
}


GENERATION_PROFILES = {
    "Custom": None,
    "Human Action / Compilation": {
        "segments": 3,
        "min_duration": 6,
        "max_duration": 15,
        "face_mode": "auto",
        "face_detect_interval": "0.12,0.25",
        "no_face_mode": "zoom",
        "face_preset": "Action (Fast Movement)",
    },
    "Talking Head / Presenter": {
        "segments": 3,
        "min_duration": 20,
        "max_duration": 45,
        "face_mode": "1",
        "face_detect_interval": "0.17,0.35",
        "no_face_mode": "zoom",
        "face_preset": "Stable (Focus Main)",
    },
    "Interview / Podcast": {
        "segments": 3,
        "min_duration": 30,
        "max_duration": 60,
        "face_mode": "auto",
        "face_detect_interval": "0.17,0.30",
        "no_face_mode": "zoom",
        "face_preset": "Two Person / Interview",
    },
    "Two Person / Forced Split": {
        "segments": 3,
        "min_duration": 30,
        "max_duration": 60,
        "face_mode": "2",
        "face_detect_interval": "0.17,0.30",
        "no_face_mode": "zoom",
        "face_preset": "Two Person / Interview",
    },
    "Animals / Objects / Places": {
        "segments": 3,
        "min_duration": 10,
        "max_duration": 30,
        "face_mode": "fixed_center",
        "face_detect_interval": "0.17,0.35",
        "no_face_mode": "zoom",
        "face_preset": "Default (Balanced)",
    },
}


def resolve_generation_profile(profile_name):
    profile = GENERATION_PROFILES.get(profile_name)
    if not profile:
        return None
    result = dict(profile)
    result.update(FACE_PRESETS[result["face_preset"]])
    return result


def migrate_saved_settings(settings):
    """Migrate only known legacy defaults; preserve custom user values."""
    migrated = dict(settings or {})
    if int(migrated.get("settings_schema_version", 0) or 0) >= SETTINGS_SCHEMA_VERSION:
        return migrated

    selected = migrated.get("face_preset", "Default (Balanced)")
    legacy = LEGACY_FACE_PRESETS.get(selected)
    if legacy:
        current = {
            "thresh": migrated.get("face_filter_thresh"),
            "two_face": migrated.get("face_two_thresh"),
            "conf": migrated.get("face_conf_thresh"),
            "dead_zone": migrated.get("face_dead_zone"),
        }
        if current == legacy:
            replacement = FACE_PRESETS[selected]
            migrated.update({
                "face_filter_thresh": replacement["thresh"],
                "face_two_thresh": replacement["two_face"],
                "face_conf_thresh": replacement["conf"],
                "face_dead_zone": replacement["dead_zone"],
            })

    if migrated.get("face_detect_interval") == "0.17,1.0":
        migrated["face_detect_interval"] = "0.17,0.35"
    migrated.setdefault("generation_profile", "Custom")
    migrated["settings_schema_version"] = SETTINGS_SCHEMA_VERSION
    return migrated
