"""Configuration settings model."""

from typing import Optional

from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, ConfigCategory, TimestampMixin, UUIDMixin, ValueType


class ConfigurationSetting(Base, UUIDMixin, TimestampMixin):
    """System-wide configuration settings."""

    __tablename__ = "configuration_settings"

    category: Mapped[ConfigCategory] = mapped_column(String(50), nullable=False, index=True)
    key: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    value_type: Mapped[ValueType] = mapped_column(String(20), nullable=False, default=ValueType.STRING)
    default_value: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    is_sensitive: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    validation_regex: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    requires_restart: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    updated_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    def __repr__(self) -> str:
        return (
            f"<ConfigurationSetting(id={self.id}, "
            f"category={self.category}, "
            f"key={self.key}, "
            f"value_type={self.value_type})>"
        )

    @property
    def display_value(self) -> str:
        """Get display value (masked if sensitive)."""
        if self.is_sensitive and self.value:
            return "***MASKED***"
        return self.value

    def validate_value(self, value: str) -> bool:
        """Validate value against type and regex."""
        import json
        import re

        # Type validation
        try:
            if self.value_type == ValueType.INTEGER:
                int(value)
            elif self.value_type == ValueType.FLOAT:
                float(value)
            elif self.value_type == ValueType.BOOLEAN:
                if value.lower() not in ["true", "false", "1", "0"]:
                    return False
            elif self.value_type == ValueType.JSON:
                json.loads(value)
            elif self.value_type == ValueType.ARRAY:
                json.loads(value)
                if not isinstance(json.loads(value), list):
                    return False
        except (ValueError, json.JSONDecodeError):
            return False

        # Regex validation
        if self.validation_regex:
            if not re.match(self.validation_regex, value):
                return False

        return True
