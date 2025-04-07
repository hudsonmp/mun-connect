import torch
from transformers import AutoTokenizer, AutoModelForTokenClassification, TrainingArguments, Trainer
from datasets import Dataset
import numpy as np
import json
import os
from typing import List, Dict, Optional

# Define our custom entity labels
ENTITY_LABELS = [
    "O",  # Outside of any entity
    "B-COMMITTEE", "I-COMMITTEE",
    "B-CHARACTER", "I-CHARACTER",
    "B-COUNTRY", "I-COUNTRY",
    "B-TOPIC", "I-TOPIC",
    "B-SUBTOPIC", "I-SUBTOPIC",
    "B-COMMITTEETYPE", "I-COMMITTEETYPE",
    "B-TIMEFRAME", "I-TIMEFRAME",
    "B-SOURCE", "I-SOURCE"
]

# Create label mappings
label2id = {label: i for i, label in enumerate(ENTITY_LABELS)}
id2label = {i: label for i, label in enumerate(ENTITY_LABELS)}

def load_training_data(json_file: str) -> List[Dict]:
    """
    Load and convert the labeled JSON data into training examples.
    """
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    training_examples = []
    
    for doc_name, doc_data in data.items():
        text = doc_data["text"]
        entities = doc_data["entities"]
        
        # Create character-level labels
        labels = ["O"] * len(text)
        
        # Fill in entity labels
        for entity_type, entity_spans in entities.items():
            if entity_type != "sources":  # Sources are handled differently
                for start_idx, end_idx, entity_text in entity_spans:
                    # Add B- prefix for the first token
                    labels[start_idx] = f"B-{entity_type.upper()}"
                    # Add I- prefix for the rest of the tokens
                    for i in range(start_idx + 1, end_idx):
                        labels[i] = f"I-{entity_type.upper()}"
        
        training_examples.append({
            "text": text,
            "labels": labels
        })
    
    return training_examples

def tokenize_and_align_labels(examples: List[Dict], tokenizer) -> Dataset:
    """
    Tokenize texts and align labels with tokens.
    """
    tokenized_inputs = []
    labels = []
    
    for example in examples:
        text = example["text"]
        char_labels = example["labels"]
        
        # Tokenize text
        tokenized = tokenizer(
            text,
            padding="max_length",
            truncation=True,
            max_length=512,
            return_offsets_mapping=True
        )
        
        # Align labels with tokens
        label_ids = []
        offset_mapping = tokenized.pop("offset_mapping")
        
        for offset in offset_mapping:
            if offset[0] == 0 and offset[1] == 0:  # Special tokens
                label_ids.append(-100)
            else:
                label = char_labels[offset[0]]
                label_ids.append(label2id.get(label, 0))  # Use 0 (O) as default
        
        tokenized["labels"] = label_ids
        tokenized_inputs.append(tokenized)
        labels.append(label_ids)
    
    # Convert to Dataset
    dataset_dict = {
        "input_ids": [x["input_ids"] for x in tokenized_inputs],
        "attention_mask": [x["attention_mask"] for x in tokenized_inputs],
        "labels": labels
    }
    
    return Dataset.from_dict(dataset_dict)

def compute_metrics(eval_preds):
    """
    Compute metrics for evaluation.
    """
    predictions, labels = eval_preds
    predictions = np.argmax(predictions, axis=2)
    
    # Remove ignored index (special tokens)
    true_predictions = [
        [id2label[p] for (p, l) in zip(prediction, label) if l != -100]
        for prediction, label in zip(predictions, labels)
    ]
    true_labels = [
        [id2label[l] for (p, l) in zip(prediction, label) if l != -100]
        for prediction, label in zip(predictions, labels)
    ]
    
    # Compute metrics
    total_correct = 0
    total_tokens = 0
    
    for pred_seq, label_seq in zip(true_predictions, true_labels):
        for pred, label in zip(pred_seq, label_seq):
            if pred == label:
                total_correct += 1
            total_tokens += 1
    
    accuracy = total_correct / total_tokens if total_tokens > 0 else 0
    
    return {
        "accuracy": accuracy
    }

def fine_tune_model(
    training_file: str,
    output_dir: str = "fine_tuned_model",
    num_train_epochs: int = 3,
    batch_size: int = 8,
    learning_rate: float = 2e-5
) -> None:
    """
    Fine-tune the NER model on our custom dataset.
    """
    # Initialize tokenizer and model
    print("Loading tokenizer and model...")
    tokenizer = AutoTokenizer.from_pretrained("dslim/bert-base-NER")
    model = AutoModelForTokenClassification.from_pretrained(
        "dslim/bert-base-NER",
        num_labels=len(ENTITY_LABELS),
        id2label=id2label,
        label2id=label2id
    )
    
    # Load and prepare dataset
    print("Loading training data...")
    examples = load_training_data(training_file)
    dataset = tokenize_and_align_labels(examples, tokenizer)
    
    # Split dataset
    print("Splitting dataset into train and validation...")
    dataset = dataset.train_test_split(test_size=0.2)
    
    # Define training arguments
    training_args = TrainingArguments(
        output_dir=output_dir,
        num_train_epochs=num_train_epochs,
        per_device_train_batch_size=batch_size,
        per_device_eval_batch_size=batch_size,
        learning_rate=learning_rate,
        evaluation_strategy="epoch",
        save_strategy="epoch",
        logging_dir=f"{output_dir}/logs",
        load_best_model_at_end=True,
        metric_for_best_model="accuracy",
        save_total_limit=2,  # Keep only the 2 best checkpoints
    )
    
    # Initialize trainer
    print("Initializing trainer...")
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=dataset["train"],
        eval_dataset=dataset["test"],
        compute_metrics=compute_metrics,
        tokenizer=tokenizer
    )
    
    # Train model
    print("\nStarting training...")
    trainer.train()
    
    # Save the fine-tuned model
    print("\nSaving model...")
    trainer.save_model(output_dir)
    tokenizer.save_pretrained(output_dir)
    
    print(f"\nModel saved to {output_dir}")

if __name__ == "__main__":
    training_file = "../training_data.json"
    
    if not os.path.exists(training_file):
        print(f"Error: Training data file not found at {training_file}")
        print("Please run create_training_data.py first and label the data.")
    else:
        fine_tune_model(training_file) 