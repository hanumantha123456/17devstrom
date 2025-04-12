import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline
import joblib

# Load dataset
data = pd.read_csv("training_data.csv")

# Model pipeline: TF-IDF + Naive Bayes
model = Pipeline([
    ("tfidf", TfidfVectorizer()),
    ("clf", MultinomialNB())
])

# Train the model
model.fit(data["message"], data["category"])

# Save the model
joblib.dump(model, "classifier_model.pkl")