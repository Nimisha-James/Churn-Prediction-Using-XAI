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

        console.log('📤 Sending form data:', formData);

        const response = await axios.post('http://localhost:5000/predict', formData, {
          headers: {
            'Content-Type': 'application/json',
          }
        });

        setResult(response.data);
      } catch (error) {
        console.error('❌ Prediction error:', error);
        const errorMsg = error.response?.data?.error || 'Error getting prediction';
        setResult({ error: errorMsg });
      } finally {
        setLoading(false);
      }
    };

    fetchPrediction();
  }, [location]);

  const toggleExplanation = () => {
    setShowExplanation(prev => !prev);
  };

  return (
    <div className="predict-container">
      <h2>Prediction Result</h2>

      {loading ? (
        <p className="loading-message">Predicting... ⏳</p>
      ) : result?.error ? (
        <p className="error-message">Error: {result.error}</p>
      ) : (
        <>
          <p className="result-message">Result: <strong>{result.message}</strong></p>

          {result.prediction === 1 && (
            <>
              <button className="explain-button" onClick={toggleExplanation}>
                {showExplanation ? 'Hide Explanation' : 'Explain Why'}
              </button>

              {showExplanation && (
                <div className="explanation-section">
                  {result.coupons !== undefined && result.cashback !== undefined && (
                    <p className="rewards">
                      🎁 <strong>{result.coupons}</strong> Coupons & <strong>${result.cashback}</strong> Cashback suggested to retain the customer.
                    </p>
                  )}

                  {result.explanation && (
                    <div className="shap-explanation">
                      <h3>Why Churning is Possible (SHAP Values)</h3>
                      <p>
                        Positive SHAP values increase churn risk, negative values reduce it.
                      </p>
                      <ul>
                        {result.explanation.map((item, index) => (
                          <li
                            key={index}
                            className={item.shap_value > 0 ? 'increase-risk' : 'decrease-risk'}
                          >
                            <strong>{item.feature}</strong>: {item.shap_value.toFixed(4)}
                            {item.shap_value > 0
                              ? ' (↑ Increases Risk)'
                              : ' (↓ Decreases Risk)'}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {result.shap_plot && (
                    <div className="plot-container">
                      <h4>SHAP Summary Plot</h4>
                      <img
                        src={`data:image/png;base64,${result.shap_plot}`}
                        alt="SHAP Plot"
                        className="prediction-plot"
                      />
                    </div>
                  )}

                  {result.lime_plot && (
                    <div className="plot-container">
                      <h4>LIME Explanation</h4>
                      <img
                        src={`data:image/png;base64,${result.lime_plot}`}
                        alt="LIME Plot"
                        className="prediction-plot"
                      />
                    </div>
                  )}
                </div>
              )}
            </>
          )}
        </>
      )}
    </div>
  );
};

export default Predict;
