from fastapi import HTTPException, status
from typing import Optional


class ProductService:
    def __init__(self, db):
        self.db = db

    async def get_products(self, page: int, page_size: int, sort_by: str, order_by: str, search_query: Optional[str] = None):
        await self.db.connect()
        offset = (page - 1) * page_size

        query = """
        SELECT * FROM products
        """
        total_count_query = """
        SELECT COUNT(*) FROM products
        """

        if search_query:
            search_condition = f"""
            WHERE product_name ILIKE '%' || '%{search_query}' || '%' OR unique_code ILIKE '%' || '%{search_query}' || '%'
            """
            query += search_condition
            total_count_query += search_condition

        query += f" ORDER BY {sort_by} {order_by} LIMIT {page_size} OFFSET {offset}"
        products = await self.db.conn.fetch(query)
        total_count = await self.db.conn.fetchval(total_count_query)

        await self.db.close()

        return {
            "products": products,
            "total": total_count,
            "page": page,
            "page_size": page_size
        }

    async def create_product(self, product):
        await self.db.connect()
        existing_product = await self.db.conn.fetchrow(
            'SELECT id FROM products WHERE unique_code = $1',
            product.unique_code
        )
        if existing_product:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="この商品は既に入庫しました。"
            )

        new_product = await self.db.conn.fetchrow(
            '''
            INSERT INTO products (product_name, price, unique_code, product_info) 
            VALUES ($1, $2, $3, $4) 
            RETURNING *
            ''',
            product.product_name, product.price, product.unique_code, product.product_info,
        )
        await self.db.close()
        return {
            'id': str(new_product['id']),
            'product_name': new_product['product_name'],
        }

    async def update_product(self, product_id, data):
        await self.db.connect()
        update_fields = []
        update_values = []
        for key, value in data.dict(exclude_unset=True).items():
            if key in ['product_name', 'price', 'product_info', 'unique_code']:
                update_fields.append(f'{key}=${len(update_fields)+1}')
                update_values.append(value)

        if not update_fields:
            await self.db.close()
            return None

        update_values.append(product_id)
        updated_product = await self.db.conn.fetchrow(
            f'UPDATE products SET {", ".join(update_fields)} WHERE id = ${len(update_values)} RETURNING *',
            *update_values
        )

        await self.db.close()
        return {
            'id': str(updated_product['id']),
            'product_name': updated_product['product_name'],
        }
