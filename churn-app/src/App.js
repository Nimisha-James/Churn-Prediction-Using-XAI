
import './App.css';
import React, { useState } from "react"; 
import { useNavigate } from "react-router-dom"; // Import navigation

function App() {
  const [formData, setFormData] = useState({
   
    tenure: "",
    cityTier: "",
    warehouseToHome: "",
    gender: "",
    hoursSpentOnApp: "",
    devicesRegistered: "",
    preferredOrderCategory: "",
    satisfactionScore: "",
    maritalStatus: "",
    numberOfAddresses: "",
    complaints: "",
    orderAmountHike: "",
    daysSinceLastOrder: "",
    customer_id:"",
  });


  const navigate = useNavigate(); // Navigation hook

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const response = await fetch("http://localhost:5000/save-churn-data", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(formData)
      });
      const result = await response.json();
      alert(result.message);
      navigate("/predict", { state: { formData } }); // Pass formData to Predict page
    } catch (error) {
      console.error("Error submitting form:", error);
      alert("Error saving data.");
    }
  };

   // **Encoding mappings**
   const labelMappings = {
    Gender: { "Female": 0, "Male": 1 },
    PreferedOrderCat: { "Fashion": 0, "Grocery": 1, "Laptop & Accessory": 2, "Mobile": 3, "Mobile Phone": 4, "Others": 5 },
    MaritalStatus: { "Divorced": 0, "Married": 1, "Single": 2 }
  };

  return (
    <div className="main-container">
      {/* Form Section */}
      <div className="container">
        <h2>Churn Prediction</h2>
        <form onSubmit={handleSubmit}>
          <div className="form-row">
            <div className="form-group">
              <label>Tenure (Months)</label>
              <input type="number" name="tenure" value={formData.tenure} onChange={handleChange} required />
            </div>
            <div className="form-group">
              <label>City Tier</label>
              <input type="number" name="cityTier" value={formData.cityTier} onChange={handleChange} required />
            </div>
          </div>

          <div className="form-row">
            <div className="form-group">
              <label>Warehouse to Home (km)</label>
              <input type="number" name="warehouseToHome" value={formData.warehouseToHome} onChange={handleChange} required />
            </div>
            <div className="form-group">
              <label>Gender</label>
              <input type="number" name="gender" value={formData.gender} onChange={handleChange} required />
            </div>
          </div>

          <div className="form-row">
            <div className="form-group">
              <label>Hours Spent on App</label>
              <input type="number" name="hoursSpentOnApp" value={formData.hoursSpentOnApp} onChange={handleChange} required />
            </div>
            <div className="form-group">
              <label>Devices Registered</label>
              <input type="number" name="devicesRegistered" value={formData.devicesRegistered} onChange={handleChange} required />
            </div>
          </div>

          <div className="form-row">
            <div className="form-group">
              <label>Preferred Order Category</label>
              <input type="number" name="preferredOrderCategory" value={formData.preferredOrderCategory} onChange={handleChange} required />
            </div>
            <div className="form-group">
              <label>Satisfaction Score</label>
              <input type="number" name="satisfactionScore" value={formData.satisfactionScore} onChange={handleChange} required />
            </div>
          </div>

          <div className="form-row">
            <div className="form-group">
              <label>Marital Status</label>
              <input type="number" name="maritalStatus" value={formData.maritalStatus} onChange={handleChange} required />
            </div>
            <div className="form-group">
              <label>Number of Addresses</label>
              <input type="number" name="numberOfAddresses" value={formData.numberOfAddresses} onChange={handleChange} required />
            </div>
          </div>

          <div className="form-row">
            <div className="form-group">
              <label>Complaints</label>
              <input type="number" name="complaints" value={formData.complaints} onChange={handleChange} required />
            </div>
            <div className="form-group">
              <label>Order Amount Hike (%)</label>
              <input type="number" name="orderAmountHike" value={formData.orderAmountHike} onChange={handleChange} required />
            </div>
          </div>

          <div className="form-row">
            <div className="form-group">
              <label>Days Since Last Order</label>
              <input type="number" name="daysSinceLastOrder" value={formData.daysSinceLastOrder} onChange={handleChange} required />
            </div>
            <div className="form-group">
              <label>Customer ID</label>
              <input type="number" name="customer_id" value={formData.customer_id} onChange={handleChange} required />
            </div>
          </div>

          <button type="submit">Predict</button>
        </form>
      </div>

      {/* Sidebar Section */}
      <div className="sidebar">
        <h3>Encoding Reference</h3>
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
  );
}

export default App;