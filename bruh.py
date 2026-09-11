from rapidfuzz import process, fuzz

test_inputs = ["The Hangover", "War and Peace", "asdkfjasdf", "Batman"]
for title in test_inputs:
    result = process.extractOne(title, movies_df["title"].tolist(), scorer=fuzz.WRatio)
    print(title, "->", result)