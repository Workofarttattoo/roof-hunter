def log_outcome(prediction, actual, revenue=0):
    return {
        "predicted": prediction,
        "actual": actual,
        "revenue": revenue,
        "error": abs(prediction - actual)
    }
