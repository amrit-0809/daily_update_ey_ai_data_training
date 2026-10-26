
export default function ProductCard({ product, addToCart }) {
  return (
    <article className="product">
      <img src={product.image} alt={product.name} />

      <span className="category">{product.category}</span>
      <h3>{product.name}</h3>
      <p className="rating">★ {product.rating}</p>

      <strong>
        ₹{product.price.toLocaleString("en-IN")}
      </strong>

      <button onClick={() => addToCart(product)}>
        Add to Cart
      </button>
    </article>
  );
}
