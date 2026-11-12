from datetime import datetime

from pydantic import BaseModel


class DateRangeParams(BaseModel):
    start_date: datetime | None = None
    end_date: datetime | None = None
    period: str = "day"  # day, week, month


class SalesMetrics(BaseModel):
    total_revenue: float
    total_orders: int
    avg_order_value: float
    revenue_change: float
    orders_change: float


class TopProduct(BaseModel):
    product_id: str
    name: str
    total_quantity: int
    total_revenue: float
    order_count: int


class OrderStatusDistribution(BaseModel):
    status: str
    count: int
    percentage: float


class FunnelData(BaseModel):
    conversations: int
    conversations_with_messages: int
    orders_created: int
    orders_completed: int
    conversion_rate: float


class CustomerMetrics(BaseModel):
    total_customers: int
    new_customers: int
    returning_customers: int
    avg_order_value: float


class RevenueSeriesPoint(BaseModel):
    date: str
    revenue: float
    orders: int


class AnalyticsResponse(BaseModel):
    sales: SalesMetrics
    top_products: list[TopProduct]
    status_distribution: list[OrderStatusDistribution]
    funnel: FunnelData
    customers: CustomerMetrics
    revenue_series: list[RevenueSeriesPoint]
    period: str
    date_range: dict
