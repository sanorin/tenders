def split_text(text, max_length=8000):
    chunks = []
    start = 0

    while start < len(text):
        chunks.append(text[start:start + max_length])
        start += max_length

    return chunks
