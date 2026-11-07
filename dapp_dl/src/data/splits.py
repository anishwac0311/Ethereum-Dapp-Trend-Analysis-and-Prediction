"""Repeated stratified train/val/test splits for the survival models (stratified on the event flag)."""
import numpy as np
from sklearn.model_selection import train_test_split


def stratified_event_split(event, seed, test_frac=0.25, val_frac=0.15):
    """Return (train_idx, val_idx, test_idx) as integer positions into `event`."""
    idx = np.arange(len(event))
    tr_val, te = train_test_split(idx, test_size=test_frac, stratify=event, random_state=seed)
    tr, va = train_test_split(tr_val, test_size=val_frac / (1 - test_frac), stratify=event[tr_val], random_state=seed)
    return tr, va, te
