import numpy as np
import pandas as pd
import joblib
import pymongo
from sklearn.model_selection import train_test_split
from lightgbm import LGBMClassifier, LGBMRegressor
from sklearn.multioutput import MultiOutputRegressor
from dotenv import load_dotenv
from pathlib import Path
import os
import matplotlib.pyplot as plt

# Set CPU limit
os.environ["LOKY_MAX_CPU_COUNT"] = "4"

# Load Mongo URI
dotenv_path = Path(__file__).resolve().parent / "db" / ".env"
load_dotenv(dotenv_path)
mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")

# MongoDB connection
client = pymongo.MongoClient(mongo_uri)
db = client["churn_prediction"]
wrong_collection = db["wrong_predictions"]
original_collection = db["original_rec"]

# Load models
models_dir = Path(__file__).resolve().parent
churn_model = joblib.load(models_dir / "model_churn.pkl")
rewards_model = joblib.load(models_dir / "rewards_model.pkl")

# Q-learning parameters
alpha, gamma, epsilon, n_episodes = 0.1, 0.9, 0.1, 50
q_table_churn = np.zeros((2, 2))
q_table_rewards = np.zeros((2, 3))

# Load wrong + original predictions
df_wrong = pd.DataFrame(list(wrong_collection.find()))
df_original = pd.DataFrame(list(original_collection.find()))

if len(df_wrong) < 5 or df_original.empty:
    print("\u26a0\ufe0f Not enough data for RL.")
    joblib.dump(churn_model, models_dir / "new_model_churn.pkl")
    joblib.dump(rewards_model, models_dir / "new_rewards_model.pkl")
    exit()

# Rename columns to lowercase
df_original = df_original.rename(columns={
    "Tenure": "tenure", "CityTier": "cityTier", "WarehouseToHome": "warehouseToHome",
    "Gender": "gender", "HourSpendOnApp": "hoursSpentOnApp", "NumberOfDeviceRegistered": "devicesRegistered",
    "PreferedOrderCat": "preferredOrderCategory", "SatisfactionScore": "satisfactionScore",
    "MaritalStatus": "maritalStatus", "NumberOfAddress": "numberOfAddresses", "Complain": "complaints",
    "OrderAmountHikeFromlastYear": "orderAmountHike", "DaySinceLastOrder": "daysSinceLastOrder",
    "CouponUsed": "coupons", "CashbackAmount": "cashback", "Churn": "actual_output"
})

required = [
    "tenure", "cityTier", "warehouseToHome", "gender", "hoursSpentOnApp",
    "devicesRegistered", "preferredOrderCategory", "satisfactionScore",
    "maritalStatus", "numberOfAddresses", "complaints", "orderAmountHike",
    "daysSinceLastOrder", "actual_output", "coupons", "cashback"
]

df_original = df_original[[c for c in required if c in df_original.columns]]
df_wrong = df_wrong[[c for c in required if c in df_wrong.columns]]

# Combine and deduplicate
df_combined = pd.concat([df_original, df_wrong], ignore_index=True)
df_combined.drop_duplicates(subset=required[:-3], inplace=True)

# Prepare features
X = df_combined[required[:-3]]
y_churn = df_combined["actual_output"]
y_rewards = df_combined[["coupons", "cashback"]]

# === Q-learning for churn model ===
for _ in range(n_episodes):
    for _, row in df_combined.iterrows():
        xi = row[X.columns].values.reshape(1, -1)
        actual = row["actual_output"]
        state = 1 if churn_model.predict(xi)[0] != actual else 0
        action = np.random.randint(0, 2) if np.random.rand() < epsilon else np.argmax(q_table_churn[state])
        reward = 1 if action == actual else -1
        next_state = 1 if action != actual else 0
        q_table_churn[state, action] += alpha * (reward + gamma * np.max(q_table_churn[next_state]) - q_table_churn[state, action])

# === Q-learning for rewards model ===
for _ in range(n_episodes):
    for _, row in df_combined.iterrows():
        if row["actual_output"] != 1:
            continue
        xi = row[X.columns].values.reshape(1, -1)
        action = np.random.randint(0, 3) if np.random.rand() < epsilon else np.argmax(q_table_rewards[1])
        current_rewards = rewards_model.predict(xi)[0]
        if action == 0:
            new_rewards = current_rewards
        elif action == 1:
            new_rewards = current_rewards + np.array([1, 10])
        else:
            new_rewards = np.maximum(current_rewards - np.array([1, 10]), [0, 0])
        reward = np.sum(new_rewards) - np.sum(current_rewards)
        q_table_rewards[1, action] += alpha * (reward + gamma * np.max(q_table_rewards[1]) - q_table_rewards[1, action])

# === Retrain models ===
X_train, X_test, y_train_c, y_test_c = train_test_split(X, y_churn, test_size=0.2, random_state=42)
X_train_r, X_test_r, y_train_r, y_test_r = train_test_split(X, y_rewards, test_size=0.2, random_state=42)

new_churn_model = LGBMClassifier(n_estimators=100, learning_rate=0.1)
new_churn_model.fit(X_train, y_train_c)

new_rewards_model = MultiOutputRegressor(LGBMRegressor(n_estimators=100, learning_rate=0.1))
new_rewards_model.fit(X_train_r, y_train_r)

# Save updated models
joblib.dump(new_churn_model, models_dir / "new_model_churn.pkl")
joblib.dump(new_rewards_model, models_dir / "new_rewards_model.pkl")

# === Visualizations ===
output_dir = Path("../outputs")
output_dir.mkdir(exist_ok=True)

# 1. Q-table churn
import seaborn as sns
sns.heatmap(q_table_churn, annot=True, cmap="YlGnBu", xticklabels=["Pred 0", "Pred 1"], yticklabels=["Correct", "Wrong"])
plt.title("Q-Table (Churn)")
plt.savefig(output_dir / "q_table_churn.png")
plt.clf()

# 2. Rewards comparison with Matplotlib line plot style
before = rewards_model.predict(X_test_r)
after = new_rewards_model.predict(X_test_r)

sample_range = range(10)
plt.plot(sample_range, before[:10, 0], label="Coupons Before", marker='o', color='orange')
plt.plot(sample_range, after[:10, 0], label="Coupons After", marker='o', color='red')
plt.plot(sample_range, before[:10, 1], label="Cashback Before", linestyle='--', color='hotpink')
plt.plot(sample_range, after[:10, 1], label="Cashback After", linestyle='--', color='deeppink')

plt.title("Reward Predictions Before vs After RL")
plt.xlabel("Sample Index")
plt.ylabel("Reward Value")
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.savefig(output_dir / "rewards_comparison.png")

print("\u2705 RL retraining complete. Visuals saved to 'outputs/' folder.")
