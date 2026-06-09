"""
============================================================
🎓 ACADEMIC TRACK B: Donut Model Fine-Tuning for Document AI
============================================================

📌 Purpose: 4th Year Major Project — Document Understanding
📌 Model: naver-clova-ix/donut-base
📌 Dataset: CORD (Consolidated Receipt Dataset)
📌 Platform: Google Colab with FREE GPU (T4)
📌 Estimated Training Time: ~30-45 minutes on T4

Run this script in Google Colab:
1. Go to https://colab.research.google.com
2. Create new notebook
3. Set Runtime → Change runtime type → GPU (T4)
4. Copy-paste sections below into cells

Ye script dikhata hai ki hum kaise ek pre-trained Document AI
model ko receipt/invoice understanding ke liye fine-tune karte hain.
Production mein PaddleOCR use ho raha hai (Track A), lekin ye script
thesis/documentation ke liye hai — ki humne model training bhi kiya.
============================================================
"""

# ══════════════════════════════════════════════════════════════════
# CELL 1: Install Dependencies
# Colab mein ye packages pehle se nahi hote, install karna padega
# ══════════════════════════════════════════════════════════════════

# !pip install -q transformers datasets sentencepiece torch torchvision
# !pip install -q pytorch-lightning wandb  # Optional: logging ke liye
# !pip install -q Pillow

import os
import sys
print("✅ Dependencies ready!")
print(f"Python version: {sys.version}")

# GPU check karo — T4 ya better hona chahiye
import torch
if torch.cuda.is_available():
    gpu_name = torch.cuda.get_device_name(0)
    gpu_memory = torch.cuda.get_device_properties(0).total_mem / 1e9
    print(f"🎮 GPU: {gpu_name} ({gpu_memory:.1f} GB)")
else:
    print("⚠️ No GPU found! Training will be very slow. Enable GPU in Runtime settings.")


# ══════════════════════════════════════════════════════════════════
# CELL 2: Load CORD Dataset from HuggingFace
# CORD = Consolidated Receipt Dataset — 1000 receipt images
# Har image ke saath structured JSON annotation hai
# ══════════════════════════════════════════════════════════════════

from datasets import load_dataset

# CORD dataset download karo — ye ~100MB hai
print("📥 Downloading CORD dataset...")
dataset = load_dataset("naver-clova-ix/cord-v2")

print(f"✅ Dataset loaded!")
print(f"   Train: {len(dataset['train'])} samples")
print(f"   Validation: {len(dataset['validation'])} samples")
print(f"   Test: {len(dataset['test'])} samples")

# Ek sample dekho — kya kya fields hain
sample = dataset['train'][0]
print(f"\n📋 Sample keys: {list(sample.keys())}")
print(f"   Image size: {sample['image'].size}")
print(f"   Ground truth (first 200 chars): {str(sample['ground_truth'])[:200]}...")


# ══════════════════════════════════════════════════════════════════
# CELL 3: Initialize Donut Processor & Model
# Donut = Document Understanding Transformer
# Vision Encoder (Swin Transformer) + Text Decoder (BART)
# ══════════════════════════════════════════════════════════════════

from transformers import DonutProcessor, VisionEncoderDecoderModel, VisionEncoderDecoderConfig

# Pre-trained Donut model load karo
MODEL_NAME = "naver-clova-ix/donut-base"

print(f"📥 Loading {MODEL_NAME}...")
processor = DonutProcessor.from_pretrained(MODEL_NAME)
model = VisionEncoderDecoderModel.from_pretrained(MODEL_NAME)

# Model ko GPU pe bhejo
device = "cuda" if torch.cuda.is_available() else "cpu"
model = model.to(device)

print(f"✅ Model loaded on {device}")
print(f"   Parameters: {sum(p.numel() for p in model.parameters()) / 1e6:.1f}M")
print(f"   Trainable: {sum(p.numel() for p in model.parameters() if p.requires_grad) / 1e6:.1f}M")


# ══════════════════════════════════════════════════════════════════
# CELL 4: Preprocess Data — Donut ke Special Token Format
# Donut structured output generate karta hai special tokens ke saath
# <s_menu><s_name>Coffee</s_name><s_price>150</s_price></s_menu>
# ══════════════════════════════════════════════════════════════════

import json
from PIL import Image

# CORD ke ground truth ko Donut token format mein convert karo
def preprocess_ground_truth(gt_string):
    """
    CORD ground truth JSON ko Donut ke special token sequence mein convert karta hai.
    Example output: <s_cord-v2><s_menu><s_nm>Coffee</s_nm><s_price>150</s_price></s_menu></s_cord-v2>
    """
    gt = json.loads(gt_string)
    # Recursively convert to token format
    return json2token(gt, sort_json_key=False)


def json2token(obj, sort_json_key=True):
    """
    Recursively JSON object ko Donut token string mein convert karta hai.
    Nested objects ke liye opening/closing tags create karta hai.
    """
    if isinstance(obj, dict):
        if len(obj) == 1 and "text_sequence" in obj:
            return obj["text_sequence"]
        output = ""
        keys = sorted(obj.keys()) if sort_json_key else obj.keys()
        for k in keys:
            output += f"<s_{k}>" + json2token(obj[k], sort_json_key) + f"</s_{k}>"
        return output
    elif isinstance(obj, list):
        return "<sep/>".join([json2token(item, sort_json_key) for item in obj])
    else:
        # Remove special characters that confuse the tokenizer
        obj = str(obj)
        return obj


# Special tokens add karo processor mein
# Ye tokens model ko structured output generate karna seekhate hain
added_tokens = []
for sample in dataset['train']:
    gt = json.loads(sample['ground_truth'])
    gt_str = json2token(gt)
    # Extract all <s_xxx> and </s_xxx> tokens
    import re
    tokens = re.findall(r'</?s_\w+>', gt_str)
    added_tokens.extend(tokens)

# Unique tokens add karo
added_tokens = sorted(set(added_tokens))
print(f"📝 Adding {len(added_tokens)} special tokens to processor")
processor.tokenizer.add_tokens(added_tokens)
model.decoder.resize_token_embeddings(len(processor.tokenizer))

print(f"✅ Vocabulary size: {len(processor.tokenizer)}")


# ══════════════════════════════════════════════════════════════════
# CELL 5: Create PyTorch Dataset
# ══════════════════════════════════════════════════════════════════

from torch.utils.data import Dataset, DataLoader

class CORDDataset(Dataset):
    """
    CORD Dataset wrapper — Donut model ke liye ready karta hai.
    Har sample mein:
    - pixel_values: Preprocessed image tensor
    - labels: Tokenized ground truth sequence
    """

    def __init__(self, hf_dataset, processor, max_length=512):
        self.dataset = hf_dataset
        self.processor = processor
        self.max_length = max_length

    def __len__(self):
        return len(self.dataset)

    def __getitem__(self, idx):
        sample = self.dataset[idx]

        # Image preprocess karo
        image = sample['image'].convert("RGB")
        pixel_values = self.processor(image, return_tensors="pt").pixel_values.squeeze()

        # Ground truth tokenize karo
        gt = json.loads(sample['ground_truth'])
        target_text = "<s_cord-v2>" + json2token(gt) + "</s_cord-v2>"

        labels = self.processor.tokenizer(
            target_text,
            add_special_tokens=False,
            max_length=self.max_length,
            padding="max_length",
            truncation=True,
            return_tensors="pt",
        ).input_ids.squeeze()

        # Padding tokens ko -100 se replace karo (loss calculation mein ignore hoga)
        labels[labels == self.processor.tokenizer.pad_token_id] = -100

        return {
            "pixel_values": pixel_values,
            "labels": labels,
        }


# Datasets create karo
train_dataset = CORDDataset(dataset['train'], processor)
val_dataset = CORDDataset(dataset['validation'], processor)

print(f"✅ Train dataset: {len(train_dataset)} samples")
print(f"✅ Val dataset: {len(val_dataset)} samples")

# DataLoaders
train_loader = DataLoader(train_dataset, batch_size=2, shuffle=True, num_workers=2)
val_loader = DataLoader(val_dataset, batch_size=2, shuffle=False, num_workers=2)


# ══════════════════════════════════════════════════════════════════
# CELL 6: Training Loop
# HuggingFace Trainer use karenge — clean aur efficient
# ══════════════════════════════════════════════════════════════════

from transformers import Seq2SeqTrainer, Seq2SeqTrainingArguments

# Training hyperparameters — Colab free GPU ke liye optimized
training_args = Seq2SeqTrainingArguments(
    output_dir="./donut-cord-finetuned",
    num_train_epochs=3,                  # 3 epochs enough hai CORD ke liye
    per_device_train_batch_size=2,       # T4 pe 2 fit hota hai (16GB VRAM)
    per_device_eval_batch_size=2,
    learning_rate=2e-5,                  # Low LR for fine-tuning
    weight_decay=0.01,
    warmup_steps=100,
    logging_steps=50,
    eval_strategy="steps",
    eval_steps=200,
    save_strategy="steps",
    save_steps=500,
    save_total_limit=2,                  # Disk space bachao
    predict_with_generate=True,
    fp16=torch.cuda.is_available(),      # Mixed precision — faster training
    gradient_accumulation_steps=4,       # Effective batch size = 2 * 4 = 8
    dataloader_num_workers=2,
    remove_unused_columns=False,
    report_to="none",                    # Disable wandb logging (optional)
)

# Trainer initialize karo
trainer = Seq2SeqTrainer(
    model=model,
    args=training_args,
    train_dataset=train_dataset,
    eval_dataset=val_dataset,
)

# 🚀 Training start!
print("🚀 Starting training...")
print(f"   Epochs: {training_args.num_train_epochs}")
print(f"   Batch size: {training_args.per_device_train_batch_size}")
print(f"   FP16: {training_args.fp16}")
print(f"   Estimated time: ~30-45 mins on T4")
print("=" * 60)

# %%time
train_result = trainer.train()

# Training results
print("\n" + "=" * 60)
print("✅ Training Complete!")
print(f"   Training loss: {train_result.training_loss:.4f}")
print(f"   Training time: {train_result.metrics.get('train_runtime', 0):.0f}s")


# ══════════════════════════════════════════════════════════════════
# CELL 7: Evaluate on Test Set
# ══════════════════════════════════════════════════════════════════

print("📊 Evaluating on validation set...")
eval_results = trainer.evaluate()
print(f"   Eval loss: {eval_results.get('eval_loss', 'N/A')}")


# ══════════════════════════════════════════════════════════════════
# CELL 8: Demo Inference — Fine-tuned Model Test
# ══════════════════════════════════════════════════════════════════

def inference(image, model, processor):
    """
    Fine-tuned model se ek receipt image process karo.
    Returns: Structured output (JSON-like token sequence)
    """
    model.eval()

    pixel_values = processor(image, return_tensors="pt").pixel_values.to(device)

    # Task prompt — model ko batao ki CORD format mein output chahiye
    task_prompt = "<s_cord-v2>"
    decoder_input_ids = processor.tokenizer(
        task_prompt, add_special_tokens=False, return_tensors="pt"
    ).input_ids.to(device)

    # Generate output
    with torch.no_grad():
        outputs = model.generate(
            pixel_values,
            decoder_input_ids=decoder_input_ids,
            max_length=model.decoder.config.max_position_embeddings,
            pad_token_id=processor.tokenizer.pad_token_id,
            eos_token_id=processor.tokenizer.eos_token_id,
            use_cache=True,
            num_beams=1,           # Greedy decoding (fast)
            bad_words_ids=[[processor.tokenizer.unk_token_id]],
        )

    # Decode output tokens
    output_text = processor.batch_decode(outputs, skip_special_tokens=False)[0]

    # Clean up: special tokens remove karo
    output_text = output_text.replace(processor.tokenizer.eos_token, "")
    output_text = output_text.replace(processor.tokenizer.pad_token, "")

    return output_text


# Test on a sample receipt
print("🧪 Testing on sample receipt...")
test_sample = dataset['test'][0]
test_image = test_sample['image'].convert("RGB")

output = inference(test_image, model, processor)
print(f"\n📋 Model Output:\n{output[:500]}")

# Compare with ground truth
gt = json.loads(test_sample['ground_truth'])
gt_text = json2token(gt)
print(f"\n📋 Ground Truth:\n{gt_text[:500]}")


# ══════════════════════════════════════════════════════════════════
# CELL 9: Save Fine-tuned Model
# Google Drive pe save karo ya HuggingFace Hub pe upload karo
# ══════════════════════════════════════════════════════════════════

# Local save
SAVE_PATH = "./donut-cord-finetuned-final"
model.save_pretrained(SAVE_PATH)
processor.save_pretrained(SAVE_PATH)
print(f"✅ Model saved to {SAVE_PATH}")

# Google Drive pe save karo (Colab mein)
# from google.colab import drive
# drive.mount('/content/drive')
# import shutil
# shutil.copytree(SAVE_PATH, "/content/drive/MyDrive/donut-cord-finetuned")
# print("✅ Model saved to Google Drive!")

print("\n" + "=" * 60)
print("🎓 FINE-TUNING COMPLETE!")
print("=" * 60)
print("""
Summary:
- Model: naver-clova-ix/donut-base (fine-tuned on CORD)
- Task: Receipt/Invoice understanding
- Output: Structured extraction of menu items, prices, totals
- This demonstrates Track B (Academic) of our Dual-Track ML Pipeline

For production (Track A), we use PaddleOCR with Hindi support
which works out-of-the-box without any training.
""")
