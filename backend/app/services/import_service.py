import csv
import io
import uuid

from fastapi import UploadFile
from openpyxl import load_workbook
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Product


class ImportError(Exception):
    pass


async def import_products_from_file(
    db: AsyncSession,
    user_id: uuid.UUID,
    file: UploadFile,
    category_id: uuid.UUID | None = None,
):
    content = await file.read()
    filename = file.filename or ""

    if filename.endswith(".csv"):
        rows = _parse_csv(content)
    elif filename.endswith((".xlsx", ".xls")):
        rows = _parse_excel(content)
    else:
        raise ImportError("Unsupported file format. Use .csv or .xlsx")

    products = []
    errors = []
    for i, row in enumerate(rows, start=2):
        try:
            name = row.get("name") or row.get("Name")
            price = row.get("price") or row.get("Price")
            description = row.get("description") or row.get("Description", "")
            stock = row.get("stock_quantity") or row.get("Stock", 0)
            image_url = row.get("image_url") or row.get("Image URL", "")

            if not name or not price:
                errors.append(f"Row {i}: name and price are required")
                continue

            product = Product(
                user_id=user_id,
                category_id=category_id,
                name=str(name).strip(),
                price=float(price),
                description=str(description).strip() if description else None,
                stock_quantity=int(float(stock)) if stock else 0,
                image_url=str(image_url).strip() if image_url else None,
            )
            products.append(product)
        except (ValueError, TypeError) as e:
            errors.append(f"Row {i}: invalid data - {e}")

    if products:
        db.add_all(products)
        await db.commit()

    return {"imported": len(products), "errors": errors}


def _parse_csv(content: bytes):
    text = content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    return list(reader)


def _parse_excel(content: bytes):
    wb = load_workbook(io.BytesIO(content), read_only=True)
    ws = wb.active
    rows = ws.iter_rows(values_only=True)
    headers = [str(h).strip().lower().replace(" ", "_") if h else "" for h in next(rows)]
    result = []
    for row in rows:
        if any(cell is not None for cell in row):
            result.append(dict(zip(headers, [str(c) if c is not None else "" for c in row], strict=False)))
    return result
