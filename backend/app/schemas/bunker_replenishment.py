from pydantic import BaseModel, ConfigDict, computed_field


class BunkerReplenishmentLineCreate(BaseModel):
    fuel_grade: str
    quantity_mt: float
    price_per_mt: float


class BunkerReplenishmentLineRead(BunkerReplenishmentLineCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int

    @computed_field
    @property
    def total_cost(self) -> float:
        return round(self.quantity_mt * self.price_per_mt, 2)


class BunkerReplenishmentCreate(BaseModel):
    vessel_id: int
    replenishment_datetime: str
    port: str
    supplier: str
    invoice_number: str | None = None
    currency: str
    lines: list[BunkerReplenishmentLineCreate]


class BunkerReplenishmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    vessel_id: int
    replenishment_datetime: str
    port: str
    supplier: str
    invoice_number: str | None
    currency: str
    lines: list[BunkerReplenishmentLineRead]

    @computed_field
    @property
    def total_cost(self) -> float:
        return round(sum(line.total_cost for line in self.lines), 2)
