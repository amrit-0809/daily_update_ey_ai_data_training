// import { useEffect, useState } from "react"
 
// function App() {
//   const [products, setProducts] = useState([])
 
//   useEffect(() => {
//     fetch("http://127.0.0.1:8000/products")
//       .then((response) => response.json())
//       .then((data) => {
//         setProducts(data)
//       })
//       .catch((error) => {
//         console.error("Error fetching products:", error)
//       })
//   }, [])
 
//   return (
//     <div>
//       <h1>Product Store</h1>
 
//       {products.map((product) => (
//         <div key={product.id}>
//           <img
//             src={product.image}
//             alt={product.name}
//             width="180"
//           />
 
//           <h2>{product.name}</h2>
 
//           <p>Price: ₹{product.price}</p>
 
//           <hr />
//         </div>
//       ))}
//     </div>
//   )
// }
 
// export default App










import { useEffect, useState } from "react";

function App() {
  const [products, setProducts] = useState([]);

  const [id, setId] = useState("");
  const [name, setName] = useState("");
  const [price, setPrice] = useState("");
  const [image, setImage] = useState("");

  useEffect(() => {
    fetch("http://127.0.0.1:8000/products")
      .then((response) => response.json())
      .then((data) => setProducts(data))
      .catch((error) => console.log(error));
  }, []);

  const addProduct = async () => {
    const product = {
      id: Number(id),
      name: name,
      price: Number(price),
      image: image
    };

    const response = await fetch("http://127.0.0.1:8000/products", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify(product)
    });

    const data = await response.json();
    console.log(data);

    setProducts([...products, product]);

    setId("");
    setName("");
    setPrice("");
    setImage("");
  };

  return (
    <div>
      <h1>Product Store</h1>

      <h2>Add Product</h2>

      <input
        type="number"
        placeholder="ID"
        value={id}
        onChange={(e) => setId(e.target.value)}
      />

      <br /><br />

      <input
        type="text"
        placeholder="Name"
        value={name}
        onChange={(e) => setName(e.target.value)}
      />

      <br /><br />

      <input
        type="number"
        placeholder="Price"
        value={price}
        onChange={(e) => setPrice(e.target.value)}
      />

      <br /><br />

      <input
        type="text"
        placeholder="Image URL"
        value={image}
        onChange={(e) => setImage(e.target.value)}
      />

      <br /><br />

      <button onClick={addProduct}>
        Add Product
      </button>

      <hr />

      {products.map((product) => (
        <div key={product.id}>
          <img
            src={product.image}
            alt={product.name}
            width="180"
          />

          <h2>{product.name}</h2>

          <p>Price: ₹{product.price}</p>

          <hr />
        </div>
      ))}
    </div>
  );
}

export default App;