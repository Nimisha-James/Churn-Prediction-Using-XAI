from flask import Flask, request, jsonify
from flask_cors import CORS
import joblib
import numpy as np
import shap
import pymongo
import os
from pathlib import Path
from dotenv import load_dotenv

app = Flask(__name__)
CORS(app)

# Load trained ML models with error handling
try:
    churn_model = joblib.load("model_churn.pkl")
    print("✅ Churn model loaded successfully")
except Exception as e:
    print(f"❌ Error loading churn model: {str(e)}")
    churn_model = None

try:
    rewards_model = joblib.load("rewards_model.pkl")
    print("✅ Rewards model loaded successfully")
except Exception as e:
    print(f"❌ Error loading rewards model: {str(e)}")
    rewards_model = None

# Define Feature Names
FEATURE_NAMES = [
    "Tenure", "City Tier", "Warehouse to Home", "Gender", "Hours Spent on App",
    "Devices Registered", "Preferred Order Category", "Satisfaction Score", 
    "Marital Status", "Number of Addresses", "Complaints", "Order Amount Hike", 
    "Days Since Last Order"
]

# Connect to MongoDB
dotenv_path = Path(__file__).resolve().parent / "db" / ".env"
load_dotenv(dotenv_path)
mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
client = pymongo.MongoClient(mongo_uri)
db = client["churn_prediction"]
collection = db["customer_rs"]

@app.route("/predict", methods=["POST"])
def predict():
    try:
        data = request.json
        print("📥 Received Data:", data)

        if not data:
            return jsonify({"error": "No data provided"}), 400

        # Ensure all required fields are present
        required_fields = [
            "tenure", "cityTier", "warehouseToHome", "gender",
            "hoursSpentOnApp", "devicesRegistered", "preferredOrderCategory",
            "satisfactionScore", "maritalStatus", "numberOfAddresses",
            "complaints", "orderAmountHike", "daysSinceLastOrder"
        ]

        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            return jsonify({"error": f"Missing fields: {', '.join(missing_fields)}"}), 400

        customer_id = data.get("customer_id")

        # Validate and convert data to integers
        try:
            features = np.array([[
                int(data["tenure"]), int(data["cityTier"]), int(data["warehouseToHome"]),
                int(data["gender"]), int(data["hoursSpentOnApp"]), int(data["devicesRegistered"]),
                int(data["preferredOrderCategory"]), int(data["satisfactionScore"]), int(data["maritalStatus"]),
                int(data["numberOfAddresses"]), int(data["complaints"]), int(data["orderAmountHike"]),
                int(data["daysSinceLastOrder"])
            ]])
        except ValueError as ve:
            print(f"❌ Error converting data to integers: {str(ve)}")
            return jsonify({"error": "Invalid data format: all fields must be numeric"}), 400

        print("🧩 Extracted Features:", features)

        # Check if models are loaded
        if churn_model is None:
            return jsonify({"error": "Churn model not loaded"}), 500

        # Make churn prediction
        try:
            churn_prediction = churn_model.predict(features)[0]
            print("🔮 Churn Prediction:", churn_prediction)
        except Exception as e:
            print(f"❌ Error during churn prediction: {str(e)}")
            return jsonify({"error": "Churn prediction failed"}), 500

        if churn_prediction == 0:
            message = "No Churning"
            coupons, cashback = 0, 0
            explanation = None
        else:
            message = "Churning Possible"

            # SHAP Explanation (only for response, not database)
            try:
                explainer = shap.Explainer(churn_model, np.zeros((1, features.shape[1])))
                shap_values = explainer(features).values.tolist()[0]

                explanation = [
                    {"feature": FEATURE_NAMES[i], "shap_value": round(shap_values[i], 4)}
                    for i in range(len(FEATURE_NAMES))
                ]
            except Exception as e:
                print(f"❌ Error computing SHAP values: {str(e)}")
                explanation = None

            # Rewards Prediction
            if rewards_model is None:
                print("⚠️ Rewards model not loaded, skipping rewards prediction")
                coupons, cashback = 0, 0
            else:
                try:
                    rewards_prediction = rewards_model.predict(features)
                    print("🎁 Rewards Prediction:", rewards_prediction)
                    if rewards_prediction.shape[1] == 2:
                        coupons, cashback = [round(value) for value in rewards_prediction[0]]
                    else:
                        coupons, cashback = 0, 0
                except Exception as e:
                    print(f"❌ Error during rewards prediction: {str(e)}")
                    coupons, cashback = 0, 0

        # Update MongoDB with only predicted_output, coupons, and cashback
        if customer_id:
            try:
                update_result = collection.update_one(
                    {"customer_id": int(customer_id)},  # Match by customer_id
                    {"$set": {
                        "predicted_output": int(churn_prediction),
                        "coupons": int(coupons),
                        "cashback": int(cashback)
                    }},
                    upsert=True  # Create new document if it doesn't exist
                )
                print(f"✅ MongoDB updated for customer_id: {customer_id}, matched: {update_result.matched_count}, modified: {update_result.modified_count}")
            except Exception as e:
                print(f"❌ Error updating MongoDB: {str(e)}")

        # Return response including explanation for frontend
        return jsonify({
            "message": message,
            "prediction": int(churn_prediction),
            "explanation": explanation,
            "coupons": int(coupons),
            "cashback": int(cashback)
        })

    except Exception as e:
        print(f"❌ General Error in Prediction: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True, port=5001)