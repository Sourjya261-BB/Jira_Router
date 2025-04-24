import streamlit as st
import pandas as pd
import random
from tests.eval_utils import load_sample_data, get_random_samples, evaluate_prediction

st.title("🧾 Ticket Routing - Team Predictor")

# Sidebar: Mode + Model Selection
mode = st.sidebar.radio("Select Mode", ["Prediction Mode", "Testing Mode"])
st.sidebar.header("Model Selection")
model_name = st.sidebar.selectbox("Choose a model", ("MBERT_base", "Qwen"))

if model_name == "MBERT_base":
    st.sidebar.info("Using MBERT_base model for team prediction.")
    from predictors.predictor_MBERT_base import predict_team
elif model_name == "Qwen":
    st.sidebar.info("Using Qwen model for team prediction.")
    # from predictors.predictor_qwen import predict_team

# Prediction Mode
if mode == "Prediction Mode":
    st.subheader("Enter Ticket Details")

    ticket_summary = st.text_input("Ticket Summary", "")
    ticket_description = st.text_area("Ticket Description", "")

    if st.button("Predict Team"):
        if not ticket_summary.strip() or not ticket_description.strip():
            st.warning("Please provide both summary and description.")
        else:
            predicted_team = predict_team(ticket_summary, ticket_description)
            st.success(f"✅ Predicted Team: `{predicted_team}`")

# Testing Mode

elif mode == "Testing Mode":
    st.subheader("🧪 Testing Mode: Evaluate on Sample Data")

    test_data = load_sample_data()

    if "Summary" not in test_data.columns or "Description" not in test_data.columns or "Fixed By" not in test_data.columns:
        st.error("CSV must contain 'Summary', 'Description', and 'Fixed By' columns.")
    else:
        num_samples = st.slider("Number of samples", min_value=1, max_value=10, value=5)

        if "resample_clicked" not in st.session_state:
            st.session_state["resample_clicked"] = True

        if st.button("🔄 Resample"):
            st.session_state["resample_clicked"] = not st.session_state["resample_clicked"]

        samples = get_random_samples(test_data, n=num_samples)

        for idx, row in samples.iterrows():
            result = evaluate_prediction(row, predict_team)

            st.markdown(f"### Sample {idx + 1}")
            st.markdown(f"**Summary:** {result['summary']}")
            st.markdown(f"**Description:** {result['description']}")
            st.markdown(f"**Predicted Team:** `{result['predicted']}`")
            st.markdown(f"**Actual Team:** `{result['actual']}`")

            if result["is_correct"]:
                st.success("✅ Correct Prediction")
            else:
                st.error("❌ Incorrect Prediction")

            st.markdown("---")


