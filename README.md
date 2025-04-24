```markdown
# 🔮 Jira Ticket Assignment Predictor
![image](https://github.com/user-attachments/assets/0a7fb497-0c30-4e05-a3d3-7a89b7a9b806)


This project provides a model to predict the **assignment team** for a Jira ticket based on its **summary** and **description**. It supports both interactive predictions and batch evaluations via a test mode.

## 🚀 Features

- Predicts team assignment using ticket summary and description
- Deployable with a simple Streamlit interface
- **Test mode**: randomly selects tickets in batches and evaluates performance
- Uses a fine-tuned transformer model for classification

---
## 🛠️ Setup & Installation

1. **Clone the repository**

2. **Create and activate a virtual environment**

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install required dependencies**

```bash
pip install -r requirements.txt
```

4. **Run the Streamlit app**

```bash
streamlit run src/app.py
```

---

## 🧪 Test Mode

The app includes a **test mode** that lets you evaluate the model's performance over a random batch of tickets.

- Test logic is implemented under `src/test/`
- You can toggle **Test Mode** in the **Streamlit sidebar**
- On selection, the app will run random batch predictions and show results

---

## 📁 Project Structure

```
.
├── src/
│   ├── app.py                         # Streamlit app entry point
│   ├── test/
│   ├── predictors/ 
│   ├── preprocessors/ 
│   ├── utils/                       
│   ├── models/
│   │   └── MBERT_base/
│   │       └── modernbert-finetuned-lomada/   # Fine-tuned model
│   └── preprocessors/
│       └── preprocessor_MBERT_base.py         # Query formatting
├── requirements.txt
└── README.md
```

---

## 🔐 Notes

- The models are **private** on Hugging Face, authenticate using:
  - `huggingface-cli login` via terminal, or
  - `use_auth_token=True` in `from_pretrained` calls

---
👥 Authors
- Sourjya Mukherjee
- Prasanth Lomada Reddy
- Purandhar Chilukuru

## 📬 Contact

Open an issue or reach out for questions, feedback, or contributions.
email: `sourjya.mukherjee@bigbasket.com`

```
