import { useState, useEffect } from 'react';
import './Predict.css';
import axios from 'axios';
import { useLocation } from 'react-router-dom';

const Predict = () => {
  const [loading, setLoading] = useState(true);
  const [result, setResult] = useState(null);
  const [showExplanation, setShowExplanation] = useState(false);
  const location = useLocation();

  useEffect(() => {
    const fetchPrediction = async () => {
      try {
        const formData = location.state?.formData;
        if (!formData) {
          setResult({ error: 'No form data provided' });
          setLoading(false);
          return;
        }

        console.log('📤 Sending form data to server:', formData); // Log form data
        const predictionResponse = await axios.post('http://localhost:5000/predict', formData);
        setResult(predictionResponse.data);
      } catch (error) {
        console.error('❌ Error fetching prediction:', error);
        console.error('Error response:', error.response?.data); // Log the error response
        setResult({ error: 'Error getting prediction' });
      } finally {
        setLoading(false);
      }
    };

    fetchPrediction();
  }, [location]);

  const toggleExplanation = () => {
    setShowExplanation(!showExplanation);
  };

  return (
    <div className="predict-container">
      <h2>Prediction Result</h2>
      {loading ? (
        <p>Predicting... ⏳</p>
      ) : result?.error ? (
        <p className="error-message">Error: {result.error}</p>
      ) : (
        <>
          <p className="result-message">Result: {result?.message}</p>
          {result?.prediction === 1 && result?.explanation && (
            <button className="explain-button" onClick={toggleExplanation}>
              {showExplanation ? 'Hide Explanation' : 'Explain'}
            </button>
          )}
          {result?.prediction === 1 && showExplanation && result?.explanation && (
            <div className="shap-explanation">
              <h3>Why Churning is Possible (SHAP Explanation)</h3>
              <ul>
                {result.explanation.map((item, index) => (
                  <li key={index}>
                    <strong>{item.feature}</strong>: {item.shap_value}
                    {item.shap_value > 0 ? ' (Increases churn risk)' : ' (Decreases churn risk)'}
                  </li>
                ))}
              </ul>
              {result?.coupons !== undefined && result?.cashback !== undefined && (
                <p className="rewards">
                  Recommended: {result.coupons} Coupons, ${result.cashback} Cashback
                </p>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
};

export default Predict;