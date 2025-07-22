# This is only backend work for SHAP and LIME
# If using change the necessary paths. I am adding the new.csv in the Data prep folder

import joblib
import numpy as np
import shap
import lime
import lime.lime_tabular
import matplotlib.pyplot as plt
from matplotlib import cm
from IPython.display import Image, display
import pandas as pd

plt.switch_backend("agg")  

FEATURE_NAMES = [
    "Tenure", "CityTier", "WarehouseToHome", "Gender", "HourSpendOnApp",
    "NumberOfDeviceRegistered", "PreferedOrderCat", "SatisfactionScore", 
    "MaritalStatus", "NumberOfAddress", "Complain", "OrderAmountHikeFromlastYear", 
    "DaySinceLastOrder"
]

df = pd.read_csv("/kaggle/input/nemozzz/new.csv")
df = df.applymap(lambda x: int(x) if isinstance(x, float) and x.is_integer() else x)
df = df.head(200)
X = df[FEATURE_NAMES].values

churn_model = joblib.load("/kaggle/input/churn/pytorch/default/1/model_churn.pkl")
rewards_model = joblib.load("/kaggle/input/churn/pytorch/default/1/rewards_model.pkl")

churn_preds = churn_model.predict(X)
rewards_preds = rewards_model.predict(X)

df["Churn_Prediction"] = churn_preds
df["Coupons"] = np.round(rewards_preds[:, 0])
df["Cashback"] = np.round(rewards_preds[:, 1])

print("🔮 Predictions completed!")
display(df.head())

background_data = shap.utils.sample(X, 100, random_state=42)
explainer_shap = shap.Explainer(churn_model, background_data)
shap_values = explainer_shap(X)


plt.figure()
shap.summary_plot(
    shap_values.values, 
    df[FEATURE_NAMES], 
    feature_names=FEATURE_NAMES, 
    show=False
)
plt.title("SHAP Summary - Dot Plot")
plt.tight_layout()
plt.savefig("shap_summary_dot_all.png")
display(Image("shap_summary_dot_all.png"))


plt.figure()
shap.summary_plot(
    shap_values.values, 
    df[FEATURE_NAMES], 
    feature_names=FEATURE_NAMES, 
    plot_type="bar", 
    show=False
)
plt.title("SHAP Summary - Bar Plot")
plt.tight_layout()
plt.savefig("shap_summary_bar_all.png")
display(Image("shap_summary_bar_all.png"))


lime_explainer = lime.lime_tabular.LimeTabularExplainer(
    training_data=background_data,
    feature_names=FEATURE_NAMES,
    class_names=["No Churn", "Churn"],
    mode="classification"
)


idx_churn_0 = df[df["Churn_Prediction"] == 0].index[0] if (df["Churn_Prediction"] == 0).any() else 0
idx_churn_1 = df[df["Churn_Prediction"] == 1].index[0] if (df["Churn_Prediction"] == 1).any() else 0


for idx, label in zip([idx_churn_0, idx_churn_1], ["no_churn", "churn"]):
    explanation = lime_explainer.explain_instance(
        X[idx],
        churn_model.predict_proba,
        num_features=len(FEATURE_NAMES)
    )
    fig = explanation.as_pyplot_figure()
    fig.tight_layout()
    filename = f"lime_instance_{label}.png"
    fig.savefig(filename)
    display(Image(filename))
