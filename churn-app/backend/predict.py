from flask import Flask, request, jsonify
from flask_cors import CORS
import joblib
import numpy as np
import shap
import pymongo
import os
from bson.objectid import ObjectId  # Import for MongoDB ObjectId conversion
from pathlib import Path
from dotenv import load_dotenv

app = Flask(__name__)
CORS(app)  # Enable CORS for React integration

# Load trained ML models
churn_model = joblib.load("model_churn.pkl")  # Churn Prediction Model
rewards_model = joblib.load("rewards_model.pkl")  # Coupon & Cashback Model

# Connect to MongoDB


dotenv_path = Path(__file__).resolve().parent / "db" / ".env"
load_dotenv(dotenv_path)
mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")  # Update if needed
client = pymongo.MongoClient(mongo_uri)
db = client["churn"]  # Database name
collection = db["customer_rs"]  # Collection name
print(f"Connected to database: {db.name}")
print(f"Connected to collection: {collection.name}")


@app.route("/latest-churn-data", methods=["GET"])
def get_latest_customer():
    """Fetch the latest customer record from MongoDB."""
    try:
        latest_customer = collection.find_one({}, sort=[("_id", pymongo.DESCENDING)])  # Fetch latest entry
        if latest_customer:
            print("Latest customer data:", latest_customer)

            latest_customer["_id"] = str(latest_customer["_id"])  # Convert ObjectId to string
            return jsonify(latest_customer)
        else:
            return jsonify({"error": "No customer data found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/predict", methods=["POST"])
def predict():
    """Predict customer churn and recommend rewards."""
    try:
        data = request.json  # Get JSON data from request

        # Convert "_id" to ObjectId for MongoDB update
        customer_id = ObjectId(data["_id"]) if "_id" in data else None

        # Prepare features array
        features = np.array([[ 
            data["Tenure"], data["CityTier"], data["WarehouseToHome"],
            data["Gender"], data["HourSpendOnApp"], data["NumberOfDeviceRegistered"],
            data["PreferedOrderCat"], data["SatisfactionScore"], data["MaritalStatus"],
            data["NumberOfAddress"], data["Complain"], data["OrderAmountHikeFromlastYear"],
            data["DaySinceLastOrder"]
        ]])

        # Predict churn
        churn_prediction = churn_model.predict(features)[0]

        # Initialize update_data dictionary
        update_data = {"predicted_output": int(churn_prediction)}

        if churn_prediction == 1:
            message = "No Churning"
            update_data["coupons"] = 0
            update_data["cashback"] = 0
        else:
            message = "Churning Possible"

            # SHAP Explainability
            explainer = shap.Explainer(churn_model, features)  # Better compatibility
            shap_values = explainer(features).values.tolist()  # Convert to list for JSON serialization
            update_data["explanation"] = shap_values

            # Predict coupon & cashback using rewards model
            rewards_prediction = rewards_model.predict(features)
            if len(rewards_prediction[0]) == 2:
                coupons, cashback = rewards_prediction[0]  # Extract values
            else:
                coupons, cashback = 0, 0  # Default values if the model is incorrect

            update_data["coupons"] = int(coupons)
            update_data["cashback"] = int(cashback)

        # Update MongoDB record
        if customer_id:
            collection.update_one({"_id": customer_id}, {"$set": update_data}, upsert=True)

        return jsonify({
            "message": message,
            "prediction": int(churn_prediction),
            "explanation": update_data.get("explanation", None),
            "coupons": update_data.get("coupons", 0),
            "cashback": update_data.get("cashback", 0)
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True, port=5000)
