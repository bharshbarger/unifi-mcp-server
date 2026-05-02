"""Deep Packet Inspection (DPI) models."""

from pydantic import BaseModel, ConfigDict, Field, field_validator


class DPICategory(BaseModel):
    """DPI category model."""

    id: str = Field(..., alias="_id", description="Category identifier")
    name: str = Field(..., description="Category name")
    description: str | None = Field(None, description="Category description")

    # Application count
    app_count: int | None = Field(None, description="Number of applications in this category")

    @field_validator("id", mode="before")
    @classmethod
    def _coerce_int_id_to_str(cls, v: object) -> object:
        # Local controller returns numeric category ids (e.g. 0, 1, 2) as
        # bare ints; the model declares str so callers can treat all id
        # fields uniformly.
        if isinstance(v, int) and not isinstance(v, bool):
            return str(v)
        return v

    model_config = ConfigDict(populate_by_name=True, extra="allow")


class DPIApplication(BaseModel):
    """DPI application model."""

    id: str = Field(..., alias="_id", description="Application identifier")
    name: str = Field(..., description="Application name")
    category_id: str | None = Field(None, description="Category identifier")
    category_name: str | None = Field(None, description="Category name")

    # Application metadata
    enabled: bool = Field(True, description="Whether application detection is enabled")

    # Traffic classification
    protocols: list[str] = Field(
        default_factory=list, description="Protocols used by this application"
    )
    ports: list[int] = Field(default_factory=list, description="Common ports used")

    @field_validator("id", "category_id", mode="before")
    @classmethod
    def _coerce_int_id_to_str(cls, v: object) -> object:
        # Local controller returns numeric ids as bare ints (matches the
        # DPICategory fix above). Stringify to match the field type.
        if isinstance(v, int) and not isinstance(v, bool):
            return str(v)
        return v

    model_config = ConfigDict(populate_by_name=True, extra="allow")


class Country(BaseModel):
    """Country information model."""

    code: str = Field(..., description="ISO country code")
    name: str = Field(..., description="Country name")
    iso_code: str | None = Field(None, description="ISO 3166-1 alpha-2 code")
    iso3_code: str | None = Field(None, description="ISO 3166-1 alpha-3 code")

    # Regulatory information
    regulatory_domain: str | None = Field(None, description="Regulatory domain for wireless")

    model_config = ConfigDict(populate_by_name=True, extra="allow")
