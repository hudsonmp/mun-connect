#!/usr/bin/env python
"""
Basic debug script for PyTorch model testing
"""
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader

# Simple dataset
class SimpleDataset(Dataset):
    def __init__(self, size=10):
        self.data = torch.randn(size, 10)
        self.labels = torch.randint(0, 3, (size,))
        
    def __len__(self):
        return len(self.data)
        
    def __getitem__(self, idx):
        return {
            "text": self.data[idx],
            "label": self.labels[idx]
        }

# Simple model
class SimpleModel(nn.Module):
    def __init__(self, input_dim=10, hidden_dim=5, num_classes=3):
        super(SimpleModel, self).__init__()
        self.fc1 = nn.Linear(input_dim, hidden_dim)
        self.fc2 = nn.Linear(hidden_dim, num_classes)
        self.relu = nn.ReLU()
        
    def forward(self, x):
        x = self.relu(self.fc1(x))
        x = self.fc2(x)
        return x

# Train function
def train_simple_model(train_dataset, val_dataset, epochs=1):
    print("Starting training")
    device = torch.device("cpu")
    
    # Create data loaders
    train_loader = DataLoader(train_dataset, batch_size=2, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=2)
    
    # Initialize model
    model = SimpleModel()
    model.to(device)
    print("Model initialized")
    
    # Loss function and optimizer
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=0.001)
    
    # Training loop
    for epoch in range(epochs):
        print(f"Epoch {epoch+1}/{epochs}")
        
        # Training
        model.train()
        total_loss = 0
        
        for i, batch in enumerate(train_loader):
            print(f"  Batch {i+1}/{len(train_loader)}")
            
            inputs = batch["text"].to(device)
            labels = batch["label"].to(device)
            
            # Forward pass
            outputs = model(inputs)
            loss = criterion(outputs, labels)
            
            # Backward pass
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            
            total_loss += loss.item()
        
        # Validation
        print("Running validation")
        model.eval()
        correct = 0
        total = 0
        
        with torch.no_grad():
            for batch in val_loader:
                inputs = batch["text"].to(device)
                labels = batch["label"].to(device)
                
                outputs = model(inputs)
                _, predicted = torch.max(outputs, 1)
                
                total += labels.size(0)
                correct += (predicted == labels).sum().item()
        
        accuracy = correct / total
        print(f"Epoch {epoch+1}, Loss: {total_loss/len(train_loader):.4f}, Accuracy: {accuracy:.4f}")
    
    print("Training completed")
    return model

# Test function
def test_simple_model(test_dataset, model):
    print("Testing model")
    device = torch.device("cpu")
    test_loader = DataLoader(test_dataset, batch_size=2)
    
    model.eval()
    correct = 0
    total = 0
    
    with torch.no_grad():
        for batch in test_loader:
            inputs = batch["text"].to(device)
            labels = batch["label"].to(device)
            
            outputs = model(inputs)
            _, predicted = torch.max(outputs, 1)
            
            total += labels.size(0)
            correct += (predicted == labels).sum().item()
    
    accuracy = correct / total
    print(f"Test Accuracy: {accuracy:.4f}")
    return accuracy

# Main function
def main():
    print("Creating datasets")
    train_dataset = SimpleDataset(20)
    val_dataset = SimpleDataset(10)
    test_dataset = SimpleDataset(10)
    
    print("Training model")
    model = train_simple_model(train_dataset, val_dataset, epochs=2)
    
    print("Testing model")
    test_simple_model(test_dataset, model)
    
    print("Debug complete")

if __name__ == "__main__":
    main() 