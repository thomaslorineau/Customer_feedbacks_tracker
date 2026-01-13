from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

analyzer = SentimentIntensityAnalyzer()


def analyze(text: str):
    if not text:
        return {'score': 0.0, 'label': 'neutral'}
    scores = analyzer.polarity_scores(text)
    compound = scores.get('compound', 0.0)
    if compound >= 0.05:
        label = 'positive'
    elif compound <= -0.05:
        label = 'negative'
    else:
        label = 'neutral'
    return {'score': compound, 'label': label}
