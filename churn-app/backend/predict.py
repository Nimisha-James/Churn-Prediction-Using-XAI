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

# Load trained ML models
churn_model = joblib.load("model_churn.pkl")
rewards_model = joblib.load("rewards_model.pkl")

# Connect to MongoDB
dotenv_path = Path(__file__).resolve().parent / "db" / ".env"
load_dotenv(dotenv_path)
mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
client = pymongo.MongoClient(mongo_uri)
db = client["churn"]
collection = db["customer_rs"]

@app.route("/latest-churn-data", methods=["GET"])
def get_latest_customer():
    try:
        latest_customer = collection.find_one({}, sort=[("_id", pymongo.DESCENDING)])
        if latest_customer:
            latest_customer["_id"] = str(latest_customer["_id"])
            return jsonify(latest_customer)
        else:
            return jsonify({"error": "No customer data found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/predict", methods=["POST"])
def predict():
    try:
        data = request.json
        print("📥 Received Data:", data)  # Debugging

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

        customer_id = ObjectId(data["_id"]) if "_id" in data else None

        features = np.array([[ 
            data["tenure"], data["cityTier"], data["warehouseToHome"],
            data["gender"], data["hoursSpentOnApp"], data["devicesRegistered"],
            data["preferredOrderCategory"], data["satisfactionScore"], data["maritalStatus"],
            data["numberOfAddresses"], data["complaints"], data["orderAmountHike"],
            data["daysSinceLastOrder"]
        ]])

        print("🧩 Extracted Features:", features)  # Debugging

        churn_prediction = churn_model.predict(features)[0]
        print("🔮 Churn Prediction:", churn_prediction)  # Debugging

        update_data = {"predicted_output": int(churn_prediction)}

        if churn_prediction == 1:
            message = "No Churning"
            update_data["coupons"] = 0
            update_data["cashback"] = 0
        else:
            message = "Churning Possible"

            # SHAP Explanation Fix
            explainer = shap.Explainer(churn_model, np.zeros((1, features.shape[1])))
            shap_values = explainer(features).values.tolist()
            update_data["explanation"] = shap_values
            print("📊 SHAP Explanation:", shap_values)  # Debugging

            # Rewards Model Fix
            rewards_prediction = rewards_model.predict(features)
            print("🎁 Rewards Prediction:", rewards_prediction)  # Debugging

            if rewards_prediction.shape[1] == 2:
                coupons, cashback = rewards_prediction[0]
            else:
                coupons, cashback = 0, 0  # Default values if shape mismatch

            update_data["coupons"] = int(coupons)
            update_data["cashback"] = int(cashback)

        if customer_id:
            collection.update_one({"_id": customer_id}, {"$set": update_data}, upsert=True)

        return jsonify({
            "message": message,
            "prediction": int(churn_prediction),
            "explanation": update_data.get("explanation"),
            "coupons": update_data.get("coupons"),
            "cashback": update_data.get("cashback")
        })

    except Exception as e:
        print("❌ Error in Prediction:", str(e))
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True, port=5000)
