"""Shared by train.py and infer.py: the 13 Choice columns, the text the encoder reads, and the model.

The encoder reads the same fields Jev does (title, venue, abstract[:6000]) joined by newlines, truncated to 512
tokens. The model is multilingual-e5-small, mean-pooled, with two linear heads: 13 logits (softmax = Jev's Choice
probabilities) and 2 logits (sigmoid = the is_rct and human_subjects scores).
"""
import os

os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

# Jev's 13 Choice options, in the fixed order of the student's softmax columns
CHOICES = ["rct", "nonrandomized_trial", "secondary_analysis", "observational", "case_report", "systematic_review",
           "meta_analysis", "narrative_review", "editorial_letter", "protocol", "guideline", "other_primary_research", "unknown"]
NOULS = ["is_rct", "human_subjects"]
ABSTRACT_CHARS = 6000


def text_of(w):
    """Same fields Jev sees (title, venue, abstract[:6000]); one string for the encoder."""
    parts = [w.get("title") or ""]
    if w.get("venue"):
        parts.append(w["venue"])
    if w.get("abstract"):
        parts.append(w["abstract"][:ABSTRACT_CHARS])
    return "\n".join(parts)


def answers_from(probs, is_rct, human):
    """Student outputs -> Jev-shaped answers, so tagger.study_design.derive() runs unchanged."""
    if not isinstance(probs, dict):
        probs = {c: float(p) for c, p in zip(CHOICES, probs)}
    return {"design": {"probabilities": probs}, "is_rct": {"noul": float(is_rct)}, "human_subjects": {"noul": float(human)}}


def build_model(base, dropout=0.1):
    import torch
    import torch.nn as nn
    from transformers import AutoModel

    class Student(nn.Module):
        def __init__(self, base, dropout=0.1):
            super().__init__()
            self.enc = AutoModel.from_pretrained(base, torch_dtype=torch.float32)
            d = self.enc.config.hidden_size
            self.drop = nn.Dropout(dropout)
            self.choice = nn.Linear(d, len(CHOICES))
            self.noul = nn.Linear(d, len(NOULS))

        def forward(self, ids, mask):
            h = self.enc(input_ids=ids, attention_mask=mask).last_hidden_state
            m = mask.unsqueeze(-1).to(h.dtype)
            pooled = self.drop((h * m).sum(1) / m.sum(1).clamp_min(1.0))
            return self.choice(pooled), self.noul(pooled)

    return Student(base, dropout)
