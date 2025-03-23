import { useState, useEffect } from "react";
import axios from "axios";

const Predict = () => {
  const [loading, setLoading] = useState(true);
  const [result, setResult] = useState(null);

  useEffect(() => {
    const fetchPrediction = async () => {
      try {
        // Fetch the latest customer data from MongoDB
        const latestDataResponse = await axios.get("http://localhost:5000/latest-churn-data");
        const latestCustomer = latestDataResponse.data;

        if (!latestCustomer || !latestCustomer._id) {
          setResult({ error: "No customer data found" });
          setLoading(false);
          return;
        }

        // Send the fetched data to the prediction endpoint
        const predictionResponse = await axios.post("http://localhost:5000/predict", latestCustomer);
        setResult(predictionResponse.data);
      } catch (error) {
        console.error("Error fetching prediction:", error);
        setResult({ error: "Error getting prediction" });
      } finally {
        setLoading(false);
      }
    };

    fetchPrediction();
  }, []);

  return (
    <div className="predict-container">
      <h2>Prediction Result</h2>
      {loading ? (
        <p>Predicting... ⏳</p>
      ) : result?.error ? (
        <p style={{ color: "red" }}>Error: {result.error}</p>
      ) : (
        <p>Result: {result?.message}</p>
      )}
    </div>
  );
};

export default Predict;
