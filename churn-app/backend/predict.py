from flask import Flask, request, jsonify
from flask_cors import CORS
import joblib
import numpy as np
import shap
import pymongo
import os
from pathlib import Path
from dotenv import load_dotenv

import lime
import lime.lime_tabular
import matplotlib.pyplot as plt
import io
import base64

# Ensure non-interactive matplotlib backend
plt.switch_backend('Agg')

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "http://localhost:3000"}})

# --------------------- Load Environment ---------------------
load_dotenv()
mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")

# --------------------- Feature Names ---------------------
FEATURE_NAMES = [
    "Tenure", "City Tier", "Warehouse to Home", "Gender", "Hours Spent on App",
    "Devices Registered", "Preferred Order Category", "Satisfaction Score", 
    "Marital Status", "Number of Addresses", "Complaints", "Order Amount Hike", 
    "Days Since Last Order"
]

# --------------------- Load Models ---------------------
churn_model = None
rewards_model = None
try:
    churn_model = joblib.load("model_churn.pkl")
    print("✅ Churn model loaded")
except Exception as e:
    print(f"❌ Failed to load churn model: {e}")

try:
    rewards_model = joblib.load("rewards_model.pkl")
    print("✅ Rewards model loaded")
except Exception as e:
    print(f"❌ Failed to load rewards model: {e}")

# --------------------- SHAP & LIME Setup ---------------------
X_train_background = np.random.rand(100, len(FEATURE_NAMES))
shap_explainer = None
lime_explainer = None

if churn_model:
    try:
        shap_explainer = shap.Explainer(churn_model, X_train_background)
        print("✅ SHAP explainer initialized")
    except Exception as e:
        print(f"❌ SHAP error: {e}")

    try:
        lime_explainer = lime.lime_tabular.LimeTabularExplainer(
            training_data=X_train_background,
            feature_names=FEATURE_NAMES,
            class_names=['No Churn', 'Churn'],
            mode='classification'
        )
        print("✅ LIME explainer initialized")
    except Exception as e:
        print(f"❌ LIME error: {e}")

# --------------------- MongoDB Setup ---------------------
client = pymongo.MongoClient(mongo_uri)
db = client["churn_prediction"]
collection = db["customer_rs"]

# --------------------- Helper Functions ---------------------
def generate_shap_summary_plot(explainer, X_data, feature_names):
    try:
        shap_values_full = explainer(X_data)
        shap_values = shap_values_full.values
        if isinstance(shap_values, list):  # Handle multi-class
            shap_values = shap_values[1]

        shap.summary_plot(shap_values, X_data, feature_names=feature_names, show=False)
        plt.title("SHAP Summary Plot - Model Behavior")
        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight')
        buf.seek(0)
        plot_base64 = base64.b64encode(buf.read()).decode('utf-8')
        buf.close()
        plt.close()
        return plot_base64
    except Exception as e:
        print(f"❌ SHAP plot error: {e}")
        return None

def create_lime_plot(model, explainer, features):
    try:
        predict_fn = lambda x: model.predict_proba(x)
        explanation = explainer.explain_instance(
            features[0],
            predict_fn,
            num_features=len(FEATURE_NAMES)
        )
        fig = explanation.as_pyplot_figure()
        fig.tight_layout()
        buf = io.BytesIO()
        fig.savefig(buf, format="png", bbox_inches="tight")
        buf.seek(0)
        plot_base64 = base64.b64encode(buf.read()).decode("utf-8")
        plt.close(fig)
        return plot_base64
    except Exception as e:
        print(f"❌ LIME plot error: {e}")
        return None

# --------------------- Flask Routes ---------------------
@app.route('/')
def home():
    return "✅ Flask Server is Running"

@app.route('/save-churn-data', methods=['POST'])
def save_churn_data():
    data = request.json or {}
    print("📩 save-churn-data:", data)
    return jsonify({"status": "saved", "data": data}), 200

@app.route("/wrong-prediction-count", methods=["GET"])
def get_wrong_prediction_count():
    try:
        count = collection.count_documents({"predicted_output": 1})
        return jsonify({"count": count})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/model-summary", methods=["GET"])
def get_model_summary():
    if not shap_explainer:
        return jsonify({"error": "SHAP explainer not initialized"}), 500
    try:
        summary_plot = generate_shap_summary_plot(shap_explainer, X_train_background, FEATURE_NAMES)
        if summary_plot:
            return jsonify({"shap_summary_plot": summary_plot})
        else:
            return jsonify({"error": "Failed to generate summary plot"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/predict", methods=["POST"])
def predict():
    try:
        data = request.json
        if not data:
            return jsonify({"error": "No data provided"}), 400

        required_fields = [
            "tenure", "cityTier", "warehouseToHome", "gender",
            "hoursSpentOnApp", "devicesRegistered", "preferredOrderCategory",
            "satisfactionScore", "maritalStatus", "numberOfAddresses",
            "complaints", "orderAmountHike", "daysSinceLastOrder"
        ]
        missing_fields = [f for f in required_fields if f not in data]
        if missing_fields:
            return jsonify({"error": f"Missing fields: {', '.join(missing_fields)}"}), 400

        features = np.array([[int(data[f]) for f in required_fields]])
        customer_id = data.get("customer_id")
        if churn_model is None:
            return jsonify({"error": "Churn model not loaded"}), 500

        churn_prediction = int(churn_model.predict(features)[0])
        print("🔮 Churn Prediction:", churn_prediction)

        explanation_data, shap_plot_base64, lime_plot_base64 = None, None, None
        coupons, cashback = 0, 0
        message = "No Churning"

        if churn_prediction == 1:
            message = "Churning Possible"

            if shap_explainer:
                try:
                    shap_values_full = shap_explainer(features)
                    shap_values = shap_values_full.values
                    if isinstance(shap_values, list):
                        shap_values = shap_values[1]
                    explanation_data = [
                        {"feature": FEATURE_NAMES[i], "shap_value": round(shap_values[0][i], 4)}
                        for i in range(len(FEATURE_NAMES))
                    ]
                    shap_plot_base64 = generate_shap_summary_plot(
                        shap_explainer, features, FEATURE_NAMES
                    )
                except Exception as e:
                    print(f"❌ SHAP explanation error: {e}")

            if lime_explainer:
                lime_plot_base64 = create_lime_plot(churn_model, lime_explainer, features)

            if rewards_model:
                try:
                    rewards_prediction = rewards_model.predict(features)
                    if rewards_prediction.ndim > 1 and rewards_prediction.shape[1] == 2:
                        coupons, cashback = [int(round(v)) for v in rewards_prediction[0]]
                except Exception as e:
                    print(f"❌ Rewards model error: {e}")

        if customer_id:
            try:
                update_result = collection.update_one(
                    {"customer_id": int(customer_id)},
                    {"$set": {
                        "predicted_output": churn_prediction,
                        "coupons": coupons,
                        "cashback": cashback
                    }},
                    upsert=True
                )
                print(f"✅ MongoDB updated for customer_id {customer_id}")
            except Exception as e:
                print(f"❌ MongoDB update error: {e}")

        return jsonify({
            "message": message,
            "prediction": churn_prediction,
            "explanation": explanation_data,
            "shap_plot": shap_plot_base64,
            "lime_plot": lime_plot_base64,
            "coupons": coupons,
            "cashback": cashback
        })

    except Exception as e:
        print(f"❌ Prediction error: {e}")
        return jsonify({"error": str(e)}), 500

# --------------------- Run Server ---------------------
if __name__ == "__main__":
    app.run(debug=True, port=5000)
