# Configuration constants for the recommendations and interactions system

LEARNING_RATE = 0.15          # λ for EWMA (higher = adapts faster)

ACTION_WEIGHTS = {
    "like": 1.0,
    "saved": 0.5,
    "read": 0.33,
    "dislike": 1.0,
}