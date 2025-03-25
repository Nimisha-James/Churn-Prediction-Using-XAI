const express = require("express");
const mongoose = require("mongoose");
const cors = require("cors");
const dotenv = require("dotenv");
const axios = require("axios");

dotenv.config();
const app = express();

app.use(cors());
app.use(express.json());

const PORT = process.env.PORT || 5000;

// Connect to MongoDB
mongoose
  .connect(process.env.MONGO_URI, { useNewUrlParser: true, useUnifiedTopology: true })
  .then(() => console.log("MongoDB Connected"))
  .catch((err) => console.error("MongoDB Connection Error:", err));

// Define Mongoose Schema
const churnSchema = new mongoose.Schema({
  tenure: Number,
  cityTier: Number,
  warehouseToHome: Number,
  gender: Number,
  hoursSpentOnApp: Number,
  devicesRegistered: Number,
  preferredOrderCategory: Number,
  satisfactionScore: Number,
  maritalStatus: Number,
  numberOfAddresses: Number,
  complaints: Number,
  orderAmountHike: Number,
  daysSinceLastOrder: Number,
  customer_id: { type: Number, unique: true }, // Ensure customer_id is unique
  coupons: Number,
  cashback: Number,
  predicted_output: Number,
  actual_output: Number,
});

const ChurnData = mongoose.model("customer_rs", churnSchema);

// API to Save Churn Prediction Data
app.post("/save-churn-data", async (req, res) => {
  try {
    const newEntry = new ChurnData(req.body);
    await newEntry.save();
    res.json({ message: "Data Saved Successfully!" });
  } catch (error) {
    console.error("Error saving data:", error);
    res.status(500).json({ error: "Internal Server Error" });
  }
});

// Proxy to Prediction Service
app.post("/predict", async (req, res) => {
  try {
    console.log("📥 Received data in server.js:", req.body);
    const predictionResponse = await axios.post("http://localhost:5001/predict", req.body);
    console.log("📤 Prediction response from predict.py:", predictionResponse.data);

    // Optionally save prediction result to database
    const { customer_id } = req.body;
    const { prediction, explanation, coupons, cashback } = predictionResponse.data;
    await ChurnData.updateOne(
      { customer_id },
      { $set: { predicted_output: prediction, coupons, cashback } },
      { upsert: true }
    );

    res.json(predictionResponse.data);
  } catch (error) {
    console.error("❌ Error fetching prediction:", error.message);
    if (error.response) {
      console.error("Response data:", error.response.data);
      console.error("Response status:", error.response.status);
    }
    res.status(500).json({ error: "Prediction failed" });
  }
});

// API to Check if Customer Exists
app.post("/check-customer", async (req, res) => {
  try {
    const { customer_id } = req.body;
    const customer = await ChurnData.findOne({ customer_id });
    res.json({ exists: !!customer });
  } catch (error) {
    console.error("Error checking customer:", error);
    res.status(500).json({ error: "Internal Server Error" });
  }
});

// API to Update Actual Output (for "Check Customer" feature)
app.post("/update-actual-output", async (req, res) => {
  try {
    const { customer_id, actual_output } = req.body;
    const customer = await ChurnData.findOne({ customer_id });
    if (!customer) {
      return res.status(404).json({ error: "Customer not found" });
    }
    customer.actual_output = actual_output;
    await customer.save();
    res.json({ message: "Actual output updated successfully" });
  } catch (error) {
    console.error("Error updating actual output:", error);
    res.status(500).json({ error: "Internal Server Error" });
  }
});

// API to Record Actual Churn (for "Record Actual Churn" feature)
app.post("/record-actual-churn", async (req, res) => {
  try {
    const { customer_id, actual_output } = req.body;
    console.log("Received data to record:", { customer_id, actual_output }); // Debug log

    // Update existing record or create new one if it doesn't exist
    const result = await ChurnData.updateOne(
      { customer_id },
      { $set: { actual_output } },
      { upsert: true } // Insert if not found
    );

    if (result.matchedCount > 0) {
      res.json({ message: "Actual churn updated successfully" });
    } else {
      res.json({ message: "New customer churn recorded successfully" });
    }
  } catch (error) {
    console.error("Error recording actual churn:", error);
    res.status(500).json({ error: "Internal Server Error" });
  }
});

app.listen(PORT, () => console.log(`Server running on port ${PORT}`));