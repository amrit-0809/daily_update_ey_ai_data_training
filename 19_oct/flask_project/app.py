from flask import Flask
from flask import jsonify

app = Flask(__name__)

@app.route("/products")
def get_products():
    products = [
        {"id": 1, "name": "Keyboard", "price": 2500},
        {"id": 2, "name": "Monitor", "price": 12000}
    ]

    return jsonify(products)


@app.route("/products/<int:product_id>")
def get_product(product_id):
    products = [
        {"id": 1, "name": "Keyboard", "price": 2500},
        {"id": 2, "name": "Monitor", "price": 12000}
    ]

    for product in products:
        if product["id"] == product_id:
            return jsonify(product)

    return jsonify({"message": "Product not found"}), 404


if __name__ == "__main__":
    app.run(debug=True)
