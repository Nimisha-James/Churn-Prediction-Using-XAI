from flask import Flask, request, jsonify
from flask_cors import CORS
import joblib
import numpy as np
import shap
import pymongo
import os
from bson.objectid import ObjectId
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

# Connect to MongoDB
dotenv_path = Path(__file__).resolve().parent / "db" / ".env"
load_dotenv(dotenv_path)
mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
client = pymongo.MongoClient(mongo_uri)
db = client["churn"]
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

        update_data = {"predicted_output": int(churn_prediction)}

        if churn_prediction == 1:
            message = "No Churning"
            update_data["coupons"] = 0
            update_data["cashback"] = 0
        else:
            message = "Churning Possible"

            # SHAP Explanation
            try:
                explainer = shap.Explainer(churn_model, np.zeros((1, features.shape[1])))
                shap_values = explainer(features).values.tolist()
                update_data["explanation"] = shap_values
                print("📊 SHAP Explanation:", shap_values)
            except Exception as e:
                print(f"❌ Error computing SHAP values: {str(e)}")
                update_data["explanation"] = None  # Proceed without SHAP if it fails

            # Rewards Prediction
            if rewards_model is None:
                print("⚠️ Rewards model not loaded, skipping rewards prediction")
                coupons, cashback = 0, 0
            else:
                try:
                    rewards_prediction = rewards_model.predict(features)
                    print("🎁 Rewards Prediction:", rewards_prediction)
                    if rewards_prediction.shape[1] == 2:
                        coupons, cashback = rewards_prediction[0]
                    else:
                        coupons, cashback = 0, 0
                except Exception as e:
                    print(f"❌ Error during rewards prediction: {str(e)}")
                    coupons, cashback = 0, 0

            update_data["coupons"] = int(coupons)
            update_data["cashback"] = int(cashback)

        # Update MongoDB
        if customer_id:
            try:
                collection.update_one({"customer_id": customer_id}, {"$set": update_data}, upsert=True)
            except Exception as e:
                print(f"❌ Error updating MongoDB: {str(e)}")

        return jsonify({
            "message": message,
            "prediction": int(churn_prediction),
            "explanation": update_data.get("explanation"),
            "coupons": update_data.get("coupons"),
            "cashback": update_data.get("cashback")
        })

    except Exception as e:
        print(f"❌ General Error in Prediction: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True, port=5001)