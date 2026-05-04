"""Configuration package for Ken."""

from ken.config.modes import MODE_PROFILES, ModeName, ModeProfile
from ken.config.modes import get_mode_profile as _get_mode_profile
from ken.config.modes import resolve_model_name as _resolve_model_name
from ken.config.settings import KenConfig, config


def get_mode_profile(mode: str | None) -> ModeProfile:
	return _get_mode_profile(mode, config.default_mode)


def resolve_model_name(model_name: str | None) -> str:
	return _resolve_model_name(model_name, config.model)


__all__ = [
	"MODE_PROFILES",
	"ModeName",
	"ModeProfile",
	"KenConfig",
	"config",
	"get_mode_profile",
	"resolve_model_name",
]
