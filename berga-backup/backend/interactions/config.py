# Constantes de configuração para o sistema de recomendações e interações

LEARNING_RATE = 0.15          # λ para EWMA (quanto maior, mais rápido se adapta)

ACTION_WEIGHTS = {
    "like": 1.0,
    "saved": 0.5,
    "read": 0.3,
    "dislike": 1.0,           # peso para o vetor negativo
}

PUBLISHER_BOOST_FACTOR = 0.2  # β para afinidade com publisher (usado nas recomendações)
NEGATIVE_PENALTY_FACTOR = 0.3 # α para penalidade do vetor negativo