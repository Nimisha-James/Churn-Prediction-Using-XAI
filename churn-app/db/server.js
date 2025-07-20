const express = require("express");
const mongoose = require("mongoose");
const cors = require("cors");
const dotenv = require("dotenv");
const axios = require("axios");
const { exec } = require("child_process");
const path = require("path");

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

// Define Mongoose Schemas
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
  customer_id: { type: Number, unique: true },
  coupons: Number,
  cashback: Number,
  predicted_output: Number,
  actual_output: Number,
});

const wrongPredictionSchema = new mongoose.Schema({
  customer_id: Number,
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
  predicted_output: Number,
  actual_output: Number,
  coupons: Number,  // Add this
  cashback: Number, // Add this
  timestamp: { type: Date, default: Date.now },
});

const ChurnData = mongoose.model("customer_rs", churnSchema);
const WrongPrediction = mongoose.model("wrong_predictions", wrongPredictionSchema);

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

// API to Record Actual Churn and Check for RL
app.post("/record-actual-churn", async (req, res) => {
  try {
    const { customer_id, actual_output } = req.body;
    console.log(`Received request for customer_id: ${customer_id}, actual_output: ${actual_output}`);

    const customer = await ChurnData.findOne({ customer_id });
    if (!customer) {
      console.log(`Customer ${customer_id} not found in customer_rs`);
      return res.status(404).json({ message: "Data for this customer ID does not exist in the database." });
    }

    // Check if actual_output already exists
    console.log(`Current customer data:`, customer);
    if (customer.actual_output !== undefined && customer.actual_output !== null) {
      console.log(`Actual output already exists for customer ${customer_id}: ${customer.actual_output}`);
      return res.json({
        message: "Actual output for customer already registered.",
        wrongCount: await WrongPrediction.countDocuments(),
      });
    }

    // Only proceed if actual_output is not yet set
    console.log(`Setting actual_output for customer ${customer_id} to ${actual_output}`);
    customer.actual_output = actual_output;
    await customer.save();
    console.log(`Updated customer ${customer_id} with actual_output: ${actual_output}`);

    const predicted_output = customer.predicted_output;
    let wrongCount = await WrongPrediction.countDocuments();
    console.log(`Initial wrongCount before processing: ${wrongCount}`);

    if (predicted_output !== undefined && parseInt(actual_output) !== parseInt(predicted_output)) {
      console.log(`Prediction differs: predicted_output=${predicted_output}, actual_output=${actual_output}`);
      // Check if this wrong prediction already exists for this customer_id
      const existingWrong = await WrongPrediction.findOne({ customer_id });
      if (!existingWrong) {
        console.log(`No existing wrong prediction for ${customer_id}, adding new entry`);
        const { _id, ...customerData } = customer.toObject();
        const wrongEntry = new WrongPrediction({
          ...customerData,
          actual_output: parseInt(actual_output),
          predicted_output: parseInt(predicted_output),
        });
        await wrongEntry.save();
        console.log(`Saved new wrong prediction for customer ${customer_id}`);
      } else {
        console.log(`Wrong prediction already exists for customer ${customer_id}, skipping insert`);
      }

      wrongCount = await WrongPrediction.countDocuments();
      console.log(`Updated wrong predictions count after processing: ${wrongCount}`);

      // Check if 3 wrong predictions have been reached
      console.log(`Checking RL trigger condition: wrongCount (${wrongCount}) >= 3`);
      
      if (wrongCount >= 5) {
        console.log("Triggering RL retraining...");
        const scriptPath = "D:\\Churn-Prediction-Using-XAI\\churn-app\\backend\\retrain_with_rl.py";
        const command = `python "${scriptPath}"`;
        console.log(`Executing command: ${command}`);
        exec(command, (error, stdout, stderr) => {
          if (error) {
            console.error(`Error executing RL script: ${error.message}`);
            console.error(`Error details: ${stderr}`);
            return;
          }
          console.log(`RL retraining stdout: ${stdout}`);
          if (stderr) console.error(`RL retraining stderr: ${stderr}`);
          else console.log("RL retraining completed successfully");
        });
        res.json({
          message: "Actual churn recorded. Total 5 wrong predictions reached, applying Q-learning.",
          wrongCount,
        });
      } else {
        console.log(`RL not triggered: wrongCount (${wrongCount}) < 3`);
        res.json({
          message: `Actual churn recorded. ${wrongCount} wrongly predicted output(s).`,
          wrongCount,
        });
      }
    } else {
      console.log(`Prediction matches or no prediction available for customer ${customer_id}`);
      res.json({
        message: "Actual churn recorded successfully. Prediction was correct.",
        wrongCount,
      });
    }
  } catch (error) {
    console.error("Error recording actual churn:", error);
    res.status(500).json({ error: "Internal Server Error" });
  }
});

// API to Get Wrong Prediction Count (for frontend display)
app.get("/wrong-prediction-count", async (req, res) => {
  try {
    const wrongCount = await WrongPrediction.countDocuments();
    console.log(`Fetched wrong prediction count for frontend: ${wrongCount}`);
    res.json({ wrongCount });
  } catch (error) {
    console.error("Error fetching wrong prediction count:", error);
    res.status(500).json({ error: "Internal Server Error" });
  }
});

app.listen(PORT, () => console.log(`Server running on port ${PORT}`));