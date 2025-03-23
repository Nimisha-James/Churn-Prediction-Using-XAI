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
  customer_id: Number,
  coupons: Number,
  cashback: Number,
  predicted_output: Number,
  actual_output: Number
});

const ChurnData = mongoose.model("customer_rs", churnSchema);

// API to Save Data
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

// API to Get Latest Customer Data
app.get("/latest-churn-data", async (req, res) => {
  try {
    const latestEntry = await ChurnData.findOne().sort({ _id: -1 });
    if (!latestEntry) {
      return res.status(404).json({ error: "No customer data found" });
    }
    res.json(latestEntry);
  } catch (error) {
    console.error("Error fetching latest data:", error);
    res.status(500).json({ error: "Internal Server Error" });
  }
});

// Proxy to Prediction Service
app.post("/predict", async (req, res) => {
  try {
    const predictionResponse = await axios.post("http://localhost:5000/predict", req.body);
    res.json(predictionResponse.data);
  } catch (error) {
    console.error("Error fetching prediction:", error);
    res.status(500).json({ error: "Prediction failed" });
  }
});

app.listen(PORT, () => console.log(`Server running on port ${PORT}`));
