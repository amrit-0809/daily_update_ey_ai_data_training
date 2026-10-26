
import ProductCard from "../components/ProductCard";

export default function Home({ products, addToCart, query }) {
  return (
    <main className="container">
      <section className="hero">
        <h1>Welcome to Amazon Clone</h1>
        <p>Discover great products at great prices.</p>
      </section>

      <h2>
        {query ? `Results for "${query}"` : "Featured Products"}
      </h2>

      {products.length > 0 ? (
        <div className="products">
          {products.map((product) => (
            <ProductCard
              key={product.id}
              product={product}
              addToCart={addToCart}
            />
          ))}
        </div>
      ) : (
        <p>No products found. Try another search.</p>
      )}
    </main>
  );
}
