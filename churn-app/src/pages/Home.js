import '../App.css';
import './Home.css';
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

function Home() {
  const [formData, setFormData] = useState({
    tenure: '',
    cityTier: '',
    warehouseToHome: '',
    gender: '',
    hoursSpentOnApp: '',
    devicesRegistered: '',
    preferredOrderCategory: '',
    satisfactionScore: '',
    maritalStatus: '',
    numberOfAddresses: '',
    complaints: '',
    orderAmountHike: '',
    daysSinceLastOrder: '',
    customer_id: '',
  });

  const [actualData, setActualData] = useState({
    customer_id: '',
    actual_output: '',
  });

  const [actualMessage, setActualMessage] = useState('');
  const [wrongPredictionInfo, setWrongPredictionInfo] = useState({ wrongCount: 0, message: '' });

  const navigate = useNavigate();

  useEffect(() => {
    fetchWrongPredictionCount();
  }, []);

  const fetchWrongPredictionCount = async () => {
    try {
      const response = await fetch('http://localhost:5000/wrong-prediction-count');
      const data = await response.json();
      setWrongPredictionInfo({
        wrongCount: data.wrongCount,
        message: data.wrongCount >= 5 
          ? "Total 5 wrong predictions reached, applying Q-learning."
          : `${data.wrongCount} wrongly predicted output(s).`
      });
    } catch (error) {
      console.error('Error fetching wrong prediction count:', error);
    }
  };

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const response = await fetch('http://localhost:5000/save-churn-data', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData),
      });
      const result = await response.json();
      alert(result.message);
      navigate('/predict', { state: { formData } });
    } catch (error) {
      console.error('Error submitting form:', error);
      alert('Error saving data.');
    }
  };

  const handleActualChange = (e) => {
    setActualData({ ...actualData, [e.target.name]: e.target.value });
    setActualMessage('');
  };

  const handleRecordActualChurn = async (e) => {
    e.preventDefault();
    console.log('Sending actual churn data:', actualData);

    try {
      const response = await fetch('http://localhost:5000/record-actual-churn', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(actualData),
      });

      if (!response.ok) {
        const errorData = await response.json();
        if (response.status === 404) {
          setActualMessage("Data doesn’t exist for this Customer ID.");
        } else {
          throw new Error(`HTTP error! Status: ${response.status}`);
        }
      } else {
        const result = await response.json();
        console.log('Server response:', result);
        setActualMessage(result.message || 'Actual churn recorded successfully.');
        // Only reset form if actual_output was newly recorded, not if it already exists or doesn’t exist
        if (!result.message.includes("already registered") && !result.message.includes("does not exist")) {
          setActualData({ customer_id: '', actual_output: '' });
        }
        // Update wrong prediction count and message after recording
        fetchWrongPredictionCount();
      }
    } catch (error) {
      console.error('Error recording actual churn:', error);
      setActualMessage('Error recording actual churn: ' + error.message);
    }
  };

  const labelMappings = {
    Gender: { Female: 0, Male: 1 },
    PreferedOrderCat: {
      Fashion: 0,
      Grocery: 1,
      'Laptop & Accessory': 2,
      Mobile: 3,
      'Mobile Phone': 4,
      Others: 5,
    },
    MaritalStatus: { Divorced: 0, Married: 1, Single: 2 },
  };

  return (
    <div className="main-container">
      <div className="container">
        <h2>Churn Prediction</h2>
        <form onSubmit={handleSubmit}>
          <div className="form-row">
            <div className="form-group">
              <label>Tenure (Months)</label>
              <input
                type="number"
                name="tenure"
                value={formData.tenure}
                onChange={handleChange}
                required
              />
            </div>
            <div className="form-group">
              <label>City Tier</label>
              <input
                type="number"
                name="cityTier"
                value={formData.cityTier}
                onChange={handleChange}
                required
              />
            </div>
          </div>
          <div className="form-row">
            <div className="form-group">
              <label>Warehouse to Home (km)</label>
              <input
                type="number"
                name="warehouseToHome"
                value={formData.warehouseToHome}
                onChange={handleChange}
                required
              />
            </div>
            <div className="form-group">
              <label>Gender</label>
              <input
                type="number"
                name="gender"
                value={formData.gender}
                onChange={handleChange}
                required
              />
            </div>
          </div>
          <div className="form-row">
            <div className="form-group">
              <label>Hours Spent on App</label>
              <input
                type="number"
                name="hoursSpentOnApp"
                value={formData.hoursSpentOnApp}
                onChange={handleChange}
                required
              />
            </div>
            <div className="form-group">
              <label>Devices Registered</label>
              <input
                type="number"
                name="devicesRegistered"
                value={formData.devicesRegistered}
                onChange={handleChange}
                required
              />
            </div>
          </div>
          <div className="form-row">
            <div className="form-group">
              <label>Preferred Order Category</label>
              <input
                type="number"
                name="preferredOrderCategory"
                value={formData.preferredOrderCategory}
                onChange={handleChange}
                required
              />
            </div>
            <div className="form-group">
              <label>Satisfaction Score</label>
              <input
                type="number"
                name="satisfactionScore"
                value={formData.satisfactionScore}
                onChange={handleChange}
                required
              />
            </div>
          </div>
          <div className="form-row">
            <div className="form-group">
              <label>Marital Status</label>
              <input
                type="number"
                name="maritalStatus"
                value={formData.maritalStatus}
                onChange={handleChange}
                required
              />
            </div>
            <div className="form-group">
              <label>Number of Addresses</label>
              <input
                type="number"
                name="numberOfAddresses"
                value={formData.numberOfAddresses}
                onChange={handleChange}
                required
              />
            </div>
          </div>
          <div className="form-row">
            <div className="form-group">
              <label>Complaints</label>
              <input
                type="number"
                name="complaints"
                value={formData.complaints}
                onChange={handleChange}
                required
              />
            </div>
            <div className="form-group">
              <label>Order Amount Hike (%)</label>
              <input
                type="number"
                name="orderAmountHike"
                value={formData.orderAmountHike}
                onChange={handleChange}
                required
              />
            </div>
          </div>
          <div className="form-row">
            <div className="form-group">
              <label>Days Since Last Order</label>
              <input
                type="number"
                name="daysSinceLastOrder"
                value={formData.daysSinceLastOrder}
                onChange={handleChange}
                required
              />
            </div>
            <div className="form-group">
              <label>Customer ID</label>
              <input
                type="number"
                name="customer_id"
                value={formData.customer_id}
                onChange={handleChange}
                required
              />
            </div>
          </div>
          <button type="submit">Predict</button>
        </form>
        <div className="wrong-prediction-info">
          <p>{wrongPredictionInfo.message}</p>
        </div>
      </div>

      <div className="sidebar">
        <div className="sidebar-content">
          <div className="actual-churn-container">
            <h3>Update Churn</h3>
            <form onSubmit={handleRecordActualChurn}>
              <div className="form-group">
                <label>Customer ID</label>
                <input
                  type="number"
                  name="customer_id"
                  value={actualData.customer_id}
                  onChange={handleActualChange}
                  required
                />
              </div>
              <div className="form-group">
                <label>Actual Output (0 or 1)</label>
                <input
                  type="number"
                  name="actual_output"
                  value={actualData.actual_output}
                  onChange={handleActualChange}
                  min="0"
                  max="1"
                  required
                />
              </div>
              <button type="submit">Record</button>
              <div className="message-container">
                {actualMessage && (
                  <p className={actualMessage.includes('Error') || actualMessage.includes('doesn’t exist') || actualMessage.includes('already registered') ? 'error-message' : 'success-message'}>
                    {actualMessage}
                  </p>
                )}
              </div>
            </form>
          </div>

          <div className="encoding-reference">
            <h3>Encoding</h3>
            {Object.entries(labelMappings).map(([category, mapping]) => (
              <div key={category} className="mapping">
                <strong>{category}:</strong>
                <ul>
                  {Object.entries(mapping).map(([label, value]) => (
                    <li key={value}>
                      {label}: {value}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

export default Home;