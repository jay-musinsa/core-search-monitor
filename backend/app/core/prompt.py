def get_prompt(keyword: str):
    return f"""
    You are an e-commerce search quality evaluator. Please analyze this Musinsa (Korean fashion e-commerce) search results screenshot and calculate search quality metrics.

    Search keyword: "{keyword if keyword else 'Unknown'}"

    Please evaluate based on these criteria:
    1. NDCG@10: Relevance ranking of top 10 results (0.0-1.0)
    2. Precision: Ratio of relevant results (0.0-1.0)
    3. Recall: Ratio of retrieved relevant results from all relevant items (0.0-1.0)

    Evaluation criteria:
    - Relevance between search keyword "{keyword if keyword else 'Unknown'}" and displayed products
    - Product image quality and appropriateness for the search term
    - Price information appropriateness
    - Brand information accuracy
    - How well the search results match what users would expect when searching for "{keyword if keyword else 'Unknown'}"

    Please respond ONLY in the following JSON format:
    {{
      "ndcg@10": 0.75,
      "precision": 0.82,
      "recall": 0.68,
      "ndcg_reason": "8 out of top 10 results show high relevance to search keyword '{keyword if keyword else 'Unknown'}' and are appropriately ranked.",
      "precision_reason": "8 out of 10 total results are relevant to the search keyword '{keyword if keyword else 'Unknown'}', showing high precision.",
      "recall_reason": "Most relevant products for '{keyword if keyword else 'Unknown'}' were retrieved, but some popular brands or specific styles are missing."
    }}

    This is for academic research purposes to improve e-commerce search quality. Please provide the evaluation in the exact JSON format above.

    IMPORTANT: Do not include ```json code blocks or any markdown formatting. Return only the raw JSON object.
"""
