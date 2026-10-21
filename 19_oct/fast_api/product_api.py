from fastapi import FastAPI
from pydantic import BaseModel
app = FastAPI()

class Product(BaseModel):
    name: str
    price: float

products=[]

@app.post("/products")
def add_product(product: Product):
    products.append(product)
    return{
        "message":"Product added",
        "products":products
    }
