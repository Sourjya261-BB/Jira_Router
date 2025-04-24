import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from preprocessors.preprocessor_MBERT_base import format_query_string
import torch.nn.functional as F
import os
from dotenv import load_dotenv
load_dotenv()

HF_TOKEN = os.getenv("HF_TOKEN")
HF_PROFILE = os.getenv("HF_PROFILE")

MODEL_ID = f"{HF_PROFILE}/modernbert-finetuned-lomada"
LOCAL_MODEL_DIR = "src/models/MBERT_base/modernbert-finetuned-lomada"

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

def load_model_and_tokenizer():
    try:
        # Try to load from Hugging Face Hub
        tokenizer = AutoTokenizer.from_pretrained(MODEL_ID,use_auth_token=HF_TOKEN)
        model = AutoModelForSequenceClassification.from_pretrained(MODEL_ID,use_auth_token=HF_TOKEN)
        print("✅ Loaded model from Hugging Face Hub.")
    except Exception as e:
        print(f"⚠️ Could not load from Hub. Falling back to local model. Reason: {e}")
        tokenizer = AutoTokenizer.from_pretrained(LOCAL_MODEL_DIR)
        model = AutoModelForSequenceClassification.from_pretrained(
            LOCAL_MODEL_DIR,
            local_files_only=True
        )
    
    return tokenizer, model.to(device)

tokenizer, model = load_model_and_tokenizer()


label_map = model.config.id2label

# def predict_team(summary: str, description: str) -> str:
#     """
#     Returns the predicted team name for a ticket.
#     """
#     query_string = format_query_string(summary, description)
#     inputs = tokenizer(
#         query_string,
#         truncation=True,
#         padding="longest",
#         return_tensors="pt"
#     )
#     inputs = {k: v.to(model.device) for k, v in inputs.items()}

#     model.eval()
#     with torch.no_grad():
#         outputs = model(**inputs)
#         logits = outputs.logits 
    

#     # pred_index = torch.argmax(logits, dim=-1).item()
#     pred_index = int(torch.argmax(logits, dim=-1))
    
#     return label_map.get(pred_index, "Unknown")



def predict_team(summary: str, description: str) -> str:
    inputs = tokenizer(
        format_query_string(summary, description),
        truncation=True,
        padding=True,                # simple future‑proof padding
        return_tensors="pt"
    )
    inputs = {k: v.to(model.device) for k, v in inputs.items()}

    model.eval()
    with torch.no_grad():
        logits = model(**inputs).logits
        probs = F.softmax(logits, dim=-1)

    predicted_class_idx = torch.argmax(probs, dim=1).item()

    pred_idx = int(torch.argmax(logits, dim=-1))
    return label_map.get(pred_idx, f"LABEL_{pred_idx}")

