def score_property(home, hail_prob, dist_km):
    return (
        0.5 * hail_prob +
        0.3 * home.get("vulnerability", 0.5) +
        0.2 * max(0, (1 - dist_km / 20))
    )


def generate_targets(properties, storm_lat, storm_lon, hail_prob):
    results = []

    for home in properties:
        dist = ((home["lat"] - storm_lat)**2 + (home["lon"] - storm_lon)**2)**0.5 * 111

        score = score_property(home, hail_prob, dist)

        if score > 0.6:
            results.append({
                "home": home,
                "score": score,
                "distance_km": dist
            })

    return sorted(results, key=lambda x: x["score"], reverse=True)[:100]

def classify_target(prob):
    if prob >= 0.80:
        return "DEPLOY"
    elif prob >= 0.60:
        return "CALL"
    elif prob >= 0.40:
        return "WATCH"
    return "IGNORE"
