import json
import os
from pathlib import Path

class ConfigManager:
    PATH = Path("setting.json")
    SETTINGS_DIR = Path("settings")
    
    _config = None
    _profile_missing_alert = False

    @classmethod
    def load(cls, force=False) -> dict:
        if cls._config is None or force:
            cls._profile_missing_alert = False
            
            # Ensure settings directory exists
            if not cls.SETTINGS_DIR.exists():
                cls.SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
            if cls.PATH.exists():
                try:
                    with open(cls.PATH, 'r', encoding='utf-8') as f:
                        cls._config = json.load(f)
                except Exception as e:
                    print(f"Failed to load config: {e}")
                    cls._config = cls.default_app_config()
            else:
                cls._config = cls.default_app_config()
                
            # Handle Profile / Keys
            last_profile = cls._config.get("last_profile", "settings/default.json")
            profile_path = Path(last_profile)
            
            profile_version = 1
            if profile_path.exists():
                try:
                    with open(profile_path, 'r', encoding='utf-8') as f:
                        profile_data = json.load(f)
                        cls._config["keys"] = profile_data.get("keys", [])
                        profile_version = profile_data.get("version", 1)
                except Exception:
                    cls._config["keys"] = cls.default_keys()
            else:
                # Profile is missing
                # Check if there are any other profiles
                available_profiles = list(cls.SETTINGS_DIR.glob("*.json"))
                if not available_profiles:
                    # Create default profile
                    default_profile = cls.SETTINGS_DIR / "default.json"
                    cls._config["last_profile"] = "settings/default.json"
                    cls._config["keys"] = cls.default_keys()
                    profile_version = 2
                    # Will be saved in cls.save() later, but let's save the profile explicitly here
                    with open(default_profile, 'w', encoding='utf-8') as f:
                        json.dump({"version": 2, "keys": cls._config["keys"]}, f, indent=2, ensure_ascii=False)
                else:
                    # Alert user to select a new one
                    cls._profile_missing_alert = True
                    cls._config["keys"] = []
            
            # Convert pixel coordinates to grid index if needed
            grid_size = cls._config.setdefault("display_window", {}).setdefault("grid_size", 2)
            if grid_size > 50:
                grid_size = 2
                cls._config["display_window"]["grid_size"] = 2
            
            if profile_version < 2:
                for k in cls._config.get("keys", []):
                    # If coordinate is likely a pixel value (> 30), convert it to grid index
                    if grid_size > 0 and (k.get("x", 0) > 30 or k.get("y", 0) > 30):
                        k["x"] = int(round(k.get("x", 0) / (60 / grid_size)))
                        k["y"] = int(round(k.get("y", 0) / (60 / grid_size)))
            else:
                # Fix corrupted version 2 profiles that have the default key's pixel coordinates
                for k in cls._config.get("keys", []):
                    if grid_size > 0 and k.get("x", 0) == 50 and k.get("y", 0) == 200:
                        k["x"] = int(round(50 / (60 / grid_size)))
                        k["y"] = int(round(200 / (60 / grid_size)))
            
            cls._config["profile_version"] = 2
            
            # Always save app config to ensure it's up to date
            cls.save(cls._config, save_profile=True)
                
            # Set language
            from core.i18n import Trans
            Trans.set_language(cls._config.get("language", "zh_CN"))
            
        return cls._config
    
    @classmethod
    def save(cls, config: dict = None, save_profile: bool = True):
        if config is not None:
            cls._config = config
        if cls._config is None:
            cls._config = cls.default_app_config()
            cls._config["keys"] = cls.default_keys()
            
        # Split configs
        app_config = {k: v for k, v in cls._config.items() if k not in ("keys", "profile_version")}
        keys_config = {
            "version": cls._config.get("profile_version", 2),
            "keys": cls._config.get("keys", [])
        }
        
        # Save App Config
        try:
            with open(cls.PATH, 'w', encoding='utf-8') as f:
                json.dump(app_config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Failed to save app config: {e}")
            
        # Save Profile Config
        if save_profile:
            profile_path = Path(app_config.get("last_profile", "settings/default.json"))
            try:
                # Ensure directory exists just in case
                profile_path.parent.mkdir(parents=True, exist_ok=True)
                with open(profile_path, 'w', encoding='utf-8') as f:
                    json.dump(keys_config, f, indent=2, ensure_ascii=False)
            except Exception as e:
                print(f"Failed to save profile config: {e}")

    @classmethod
    def default_app_config(cls) -> dict:
        return {
            "version": "1.0",
            "language": "zh_CN",
            "display_window": {
                "x": 100, "y": 100,
                "width": 600, "height": 400,
                "monitor": 0,
                "background_color": [0, 0, 0, 0],
                "grid_visible": True,
                "grid_size": 2,
                "grid_color": [255, 255, 255, 26],
                "text_offset_y": 0,
                "counter_offset_y": 20,
                "editor_key_size": 60
            },
            "rain": {
                "enabled": True,
                "speed_up": 6,
                "grow_speed": 6,
                "fade_speed": 0.018,
                "fade_enabled": True,
                "color_link": True
            },
            "associated_startup_enabled": False,
            "associated_app_path": "",
            "last_profile": "settings/default.json"
        }
        
    @classmethod
    def default_keys(cls) -> list:
        return [
            {
                "id": "key_001",
                "key_code": "a",
                "display_name": "A",
                "x": 2, "y": 7,
                "width": 60, "height": 60,
                "bg_color": [240, 240, 245, 60],
                "border_color": [255, 255, 255, 255],
                "border_width": 2,
                "text_color": [255, 255, 255, 220],
                "font_size": 16,
                "font_bold": True,
                "corner_radius": 10,
                "press_scale": 0.92,
                "show_counter": False,
                "counter_size": 14,
                "counter_offset_x": 0,
                "counter_offset_y": 20,
                "text_offset_y": 0,
                "counter": 0,
                "counter_autofit": False,
                "rain_color": [255, 255, 255, 160]
            }
        ]
