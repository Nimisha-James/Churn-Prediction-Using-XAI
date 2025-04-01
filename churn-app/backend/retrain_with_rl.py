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

# Suppress joblib warning by setting LOKY_MAX_CPU_COUNT
os.environ["LOKY_MAX_CPU_COUNT"] = "4"  # Adjust based on your CPU cores

# Load environment variables
dotenv_path = Path(__file__).resolve().parent / "db" / ".env"
load_dotenv(dotenv_path)
mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")

# Connect to MongoDB
client = pymongo.MongoClient(mongo_uri)
db = client["churn_prediction"]
wrong_collection = db["wrong_predictions"]

# Define the path to the models (same directory as this script)
models_dir = Path(__file__).resolve().parent  # Points to D:\Churn-Prediction-Using-XAI\churn-app\backend
churn_model_path = models_dir / "model_churn.pkl"
rewards_model_path = models_dir / "rewards_model.pkl"

# Load original models
print(f"Loading churn model from: {churn_model_path}")
churn_model = joblib.load(churn_model_path)
print(f"Loading rewards model from: {rewards_model_path}")
rewards_model = joblib.load(rewards_model_path)

# Q-Learning Parameters
alpha = 0.1  # Learning rate
gamma = 0.9  # Discount factor
epsilon = 0.1  # Exploration rate
n_episodes = 100  # Number of episodes

# Define state and action space
# States: Difference between predicted and actual (0 or 1)
# Actions: Adjust prediction (0 or 1), adjust rewards (increase/decrease coupons and cashback)
q_table_churn = np.zeros((2, 2))  # 2 states (correct/wrong), 2 actions (keep/adjust)
q_table_rewards = np.zeros((2, 3))  # 2 states, 3 actions (no change, increase, decrease)

# Load wrong predictions data
wrong_data = list(wrong_collection.find())
df_wrong = pd.DataFrame(wrong_data)

# Debug: Print number of records and columns
print(f"Number of records in wrong_predictions: {len(df_wrong)}")
print("Columns in df_wrong:", df_wrong.columns.tolist())

# Check if there's enough data
if len(df_wrong) < 5:
    print("Warning: Not enough data in wrong_predictions to retrain effectively. Need at least 5 records.")
    print("Proceeding with Q-learning adjustments only, skipping retraining.")
    # Save the models as-is (or you can skip saving if you don't want to overwrite)
    joblib.dump(churn_model, models_dir / "new_model_churn.pkl")
    joblib.dump(rewards_model, models_dir / "new_rewards_model.pkl")
    print("Models saved without retraining due to insufficient data.")
    exit()

# Features for churn and rewards
X = df_wrong[["tenure", "cityTier", "warehouseToHome", "gender", "hoursSpentOnApp",
              "devicesRegistered", "preferredOrderCategory", "satisfactionScore",
              "maritalStatus", "numberOfAddresses", "complaints", "orderAmountHike",
              "daysSinceLastOrder"]]
y_churn = df_wrong["actual_output"]

# Ensure coupons and cashback columns exist, fill with 0 if missing
if 'coupons' not in df_wrong.columns:
    df_wrong['coupons'] = 0
if 'cashback' not in df_wrong.columns:
    df_wrong['cashback'] = 0

y_rewards = df_wrong[["coupons", "cashback"]]

# Debug: Check feature variance
print("Feature summary:")
print(X.describe())

# Q-Learning for Churn Model
for episode in range(n_episodes):
    for i in range(len(X)):
        state = 1 if y_churn.iloc[i] != churn_model.predict(X.iloc[[i]])[0] else 0
        if np.random.uniform(0, 1) < epsilon:
            action = np.random.randint(0, 2)  # Explore
        else:
            action = np.argmax(q_table_churn[state])  # Exploit

        # Execute action
        current_pred = churn_model.predict(X.iloc[[i]])[0]
        new_pred = action  # 0 or 1
        reward = 1 if new_pred == y_churn.iloc[i] else -1

        # Update Q-table
        next_state = 1 if new_pred != y_churn.iloc[i] else 0
        q_table_churn[state, action] = q_table_churn[state, action] + alpha * (
            reward + gamma * np.max(q_table_churn[next_state]) - q_table_churn[state, action]
        )

# Q-Learning for Rewards Model
for episode in range(n_episodes):
    for i in range(len(X)):
        state = 1 if y_churn.iloc[i] == 1 else 0  # Only adjust rewards if churned
        if state == 0:
            continue
        if np.random.uniform(0, 1) < epsilon:
            action = np.random.randint(0, 3)  # Explore
        else:
            action = np.argmax(q_table_rewards[state])  # Exploit

        # Execute action
        current_rewards = rewards_model.predict(X.iloc[[i]])[0]
        if action == 0:  # No change
            new_rewards = current_rewards
        elif action == 1:  # Increase
            new_rewards = current_rewards + np.array([1, 10])  # +1 coupon, +10 cashback
        else:  # Decrease
            new_rewards = current_rewards - np.array([1, 10])  # -1 coupon, -10 cashback
            new_rewards = np.maximum(new_rewards, [0, 0])  # Ensure non-negative

        # Reward: Higher reward if churned customer gets more incentives
        reward = np.sum(new_rewards) - np.sum(current_rewards) if y_churn.iloc[i] == 1 else 0

        # Update Q-table
        q_table_rewards[state, action] = q_table_rewards[state, action] + alpha * (
            reward + gamma * np.max(q_table_rewards[state]) - q_table_rewards[state, action]
        )

# Retrain models with data from wrong_predictions
X_train, X_test, y_train_churn, y_test_churn = train_test_split(X, y_churn, test_size=0.2, random_state=42)
X_train_r, X_test_r, y_train_rewards, y_test_rewards = train_test_split(X, y_rewards, test_size=0.2, random_state=42)

# Retrain churn model with adjusted parameters
new_churn_model = LGBMClassifier(
    n_estimators=100,  # Reduced to avoid overfitting on small data
    learning_rate=0.1,
    max_depth=-1,  # No limit on depth
    min_child_samples=5,  # Reduced to allow splits with fewer samples
    num_leaves=20  # Reduced to avoid overfitting
)
new_churn_model.fit(X_train, y_train_churn)

# Retrain rewards model with adjusted parameters
new_rewards_model = MultiOutputRegressor(
    LGBMRegressor(
        n_estimators=100,
        learning_rate=0.1,
        max_depth=-1,
        min_child_samples=5,
        num_leaves=20
    )
)
new_rewards_model.fit(X_train_r, y_train_rewards)

# Save updated models
joblib.dump(new_churn_model, models_dir / "new_model_churn.pkl")
joblib.dump(new_rewards_model, models_dir / "new_rewards_model.pkl")

print("Models retrained and saved successfully with Q-learning adjustments.")