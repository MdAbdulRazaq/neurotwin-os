import torch
import torch.nn as nn
from transformers import DistilBertModel, DistilBertTokenizer
from typing import List, Tuple
import numpy as np


class DistilBERTCNN(nn.Module):
    """DistilBERT + CNN fusion model for emotion detection."""

    def __init__(
        self,
        num_emotions: int = 6,
        dropout: float = 0.3,
        cnn_kernel_sizes: List[int] = None,
        cnn_num_filters: int = 128,
    ):
        super().__init__()
        self.num_emotions = num_emotions
        if cnn_kernel_sizes is None:
            cnn_kernel_sizes = [3, 4, 5]

        # DistilBERT as feature extractor (frozen by default)
        self.distilbert = DistilBertModel.from_pretrained("distilbert-base-uncased")
        self.hidden_size = self.distilbert.config.hidden_size  # 768

        # Freeze DistilBERT parameters
        for param in self.distilbert.parameters():
            param.requires_grad = False

        # CNN layers for local pattern extraction
        self.convs = nn.ModuleList([
            nn.Conv1d(
                in_channels=self.hidden_size,
                out_channels=cnn_num_filters,
                kernel_size=k,
                padding=k // 2
            )
            for k in cnn_kernel_sizes
        ])

        self.dropout = nn.Dropout(dropout)
        self.classifier = nn.Linear(cnn_num_filters * len(cnn_kernel_sizes), num_emotions)

        # Tokenizer
        self.tokenizer = DistilBertTokenizer.from_pretrained("distilbert-base-uncased")
        self.max_length = 128

    def forward(self, input_ids, attention_mask):
        # Get DistilBERT embeddings
        bert_output = self.distilbert(
            input_ids=input_ids,
            attention_mask=attention_mask
        )
        # Shape: [batch, seq_len, hidden_size]
        embeddings = bert_output.last_hidden_state

        # Transpose for CNN: [batch, hidden_size, seq_len]
        embeddings = embeddings.transpose(1, 2)

        # Apply CNN with different kernel sizes
        conv_outputs = []
        for conv in self.convs:
            conv_out = torch.relu(conv(embeddings))
            # Global max pooling over time dimension
            pooled = torch.max_pool1d(conv_out, kernel_size=conv_out.shape[2]).squeeze(2)
            conv_outputs.append(pooled)

        # Concatenate all CNN outputs
        fused = torch.cat(conv_outputs, dim=1)
        fused = self.dropout(fused)

        # Classify
        logits = self.classifier(fused)
        return logits

    def predict(self, text: str) -> Tuple[str, np.ndarray]:
        """Predict emotion for a single text input."""
        self.eval()

        # Tokenize
        inputs = self.tokenizer(
            text,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=self.max_length
        )

        with torch.no_grad():
            logits = self.forward(
                input_ids=inputs["input_ids"],
                attention_mask=inputs["attention_mask"]
            )
            probs = torch.softmax(logits, dim=1).squeeze().numpy()

        # Emotion labels (standard 6 emotions)
        emotions = ["angry", "disgust", "fear", "happy", "sad", "surprise"]
        predicted_idx = np.argmax(probs)
        return emotions[predicted_idx], probs


# Convenience function for loading the model
def load_emotion_model(model_path: str = None):
    """Load the emotion detection model."""
    model = DistilBERTCNN()
    if model_path:
        model.load_state_dict(torch.load(model_path, map_location="cpu"))
    model.eval()
    return model
