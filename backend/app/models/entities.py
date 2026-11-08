"""
SQLAlchemy 2.0 ORM Entities Module
Maps the Iranian e-commerce analytical schema initialized in PostgreSQL.
"""

from sqlalchemy import (
    Column,
    Integer,
    String,
    Numeric,
    DateTime,
    ForeignKey,
    Computed,
    func,
)
from sqlalchemy.orm import relationship
from app.core.database import Base


class Customer(Base):
    """
    Customer entity storing registration details, contact numbers, and geographic location.
    """
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(150), nullable=False)
    email = Column(String(150), unique=True, nullable=False, index=True)
    phone = Column(String(20), nullable=False)
    city = Column(String(100), nullable=False, index=True)
    registration_date = Column(DateTime, nullable=False, index=True)

    # Relationships
    orders = relationship("Order", back_populates="customer", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Customer(id={self.id}, full_name='{self.full_name}', city='{self.city}')>"


class Product(Base):
    """
    Product entity representing the e-commerce catalog with prices in Tomans.
    """
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    category = Column(String(100), nullable=False, index=True)
    price = Column(Numeric(14, 2), nullable=False, index=True)
    stock_quantity = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    # Relationships
    order_items = relationship("OrderItem", back_populates="product")

    def __repr__(self) -> str:
        return f"<Product(id={self.id}, name='{self.name}', price={self.price})>"


class Order(Base):
    """
    Order header transaction tracking purchasing customer, order date, status, and total amount.
    """
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False, index=True)
    order_date = Column(DateTime, nullable=False, index=True)
    status = Column(String(50), nullable=False, index=True)
    total_amount = Column(Numeric(16, 2), nullable=False, default=0)

    # Relationships
    customer = relationship("Customer", back_populates="orders")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Order(id={self.id}, customer_id={self.customer_id}, status='{self.status}', total={self.total_amount})>"


class OrderItem(Base):
    """
    Order line item detailing product selections, purchased quantity, and computed line totals.
    """
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="RESTRICT"), nullable=False, index=True)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Numeric(14, 2), nullable=False)
    line_total = Column(Numeric(16, 2), Computed("quantity * unit_price", persisted=True))

    # Relationships
    order = relationship("Order", back_populates="items")
    product = relationship("Product", back_populates="order_items")

    def __repr__(self) -> str:
        return f"<OrderItem(id={self.id}, order_id={self.order_id}, product_id={self.product_id}, qty={self.quantity})>"
