"""Application configuration management."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=False)

    # Application
    app_name: str = "DispatchGrid"
    app_version: str = "1.0.0"
    debug: bool = True

    # Database
    database_url: str = "sqlite:///./dispatchgrid.db"

    # Scheduling Algorithm
    schedule_time_slot_interval_minutes: int = 15
    schedule_local_search_iterations: int = 10

    # Objective Function Weights
    weight_sla_penalty: float = 100.0
    weight_travel_time: float = 1.0
    weight_unassigned_priority: float = 50.0
    weight_overtime: float = 10.0
    weight_churn: float = 20.0
    weight_workload_imbalance: float = 5.0

    # SLA Policy
    sla_is_hard_constraint: bool = False

Config = Settings
# Global settings instance
settings = Settings()
