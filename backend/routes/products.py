"""
Product management routes for the ADM Platform.
CRUD for insurance products that agents sell.
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from database import get_db
from models import Product
from schemas import ProductCreate, ProductUpdate, ProductResponse

router = APIRouter(prefix="/products", tags=["Products"])


@router.get("/", response_model=List[ProductResponse])
def list_products(
    category: Optional[str] = None,
    active_only: bool = True,
    db: Session = Depends(get_db),
):
    """List all products, optionally filtered by category."""
    query = db.query(Product)
    if category:
        query = query.filter(Product.category == category)
    if active_only:
        query = query.filter(Product.active == True)
    return query.order_by(Product.category, Product.name).all()


@router.get("/categories")
def get_product_categories(db: Session = Depends(get_db)):
    """Get product counts by category."""
    results = (
        db.query(Product.category, func.count(Product.id))
        .filter(Product.active == True)
        .group_by(Product.category)
        .all()
    )
    return {cat: count for cat, count in results}


@router.get("/{product_id}", response_model=ProductResponse)
def get_product(product_id: int, db: Session = Depends(get_db)):
    """Get a single product by ID."""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.post("/", response_model=ProductResponse)
def create_product(data: ProductCreate, db: Session = Depends(get_db)):
    """Create a new product."""
    product = Product(**data.model_dump())
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


@router.put("/{product_id}", response_model=ProductResponse)
def update_product(product_id: int, data: ProductUpdate, db: Session = Depends(get_db)):
    """Update an existing product."""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(product, field, value)

    db.commit()
    db.refresh(product)
    return product


@router.delete("/{product_id}")
def delete_product(product_id: int, db: Session = Depends(get_db)):
    """Soft-delete a product (sets active=False)."""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    product.active = False
    db.commit()
    return {"message": "Product deactivated"}
