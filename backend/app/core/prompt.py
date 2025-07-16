import json

def get_prompt(keyword: str):
    return f"""
    You are an e-commerce search quality evaluator. Please analyze this Musinsa (Korean fashion e-commerce) search results screenshot and calculate search quality metrics.

    Search keyword: "{keyword if keyword else 'Unknown'}"

    Please evaluate based on these criteria:
    1. NDCG@10 (Normalized Discounted Cumulative Gain at 10): Measures the ranking quality of the top 10 search results, considering both relevance and position. Higher-ranked relevant items contribute more to the score. Range: 0.0-1.0, where 1.0 means perfect ranking of highly relevant items.
    
    2. Precision: The fraction of retrieved results that are relevant to the search query. Calculated as (Number of relevant results) / (Total number of results shown). Range: 0.0-1.0, where 1.0 means all shown results are relevant.
    
    3. Recall: The fraction of relevant items that were successfully retrieved by the search. Calculated as (Number of relevant results retrieved) / (Total number of relevant items that should exist). Range: 0.0-1.0, where 1.0 means all relevant items were found.

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
      "recall_reason": "Most relevant products for '{keyword if keyword else 'Unknown'}' were retrieved, but some popular brands or specific styles are missing.",
      "precision_issues": [
        {{
          "goods_no": "N/A",
          "goods_name": "Example Irrelevant Product",
          "reason": "This product is not related to '{keyword if keyword else 'Unknown'}' search term because..."
        }}
      ]
    }}

    This is for academic research purposes to improve e-commerce search quality. Please provide the evaluation in the exact JSON format above.

    IMPORTANT: Do not include ```json code blocks or any markdown formatting. Return only the raw JSON object.
    """

def get_prompt_with_api_data(keyword: str, api_data: list):
    """API 데이터를 포함한 상세한 평가 프롬프트"""
    # 상품 정보를 추출할 최대 개수 설정
    MAX_PRODUCTS = 60
    # API 데이터에서 상품 정보 추출 (처음 MAX_PRODUCTS개만)
    products_info = []
    for i, product in enumerate(api_data[:MAX_PRODUCTS]):
        products_info.append({
            "rank": i + 1,
            "goods_no": product.get("goodsNo", "N/A"),
            "goods_name": product.get("goodsName", "N/A"),
            "brand_name": product.get("brandName", "N/A"),
            "price": product.get("price", 0),
            "sale_rate": product.get("saleRate", 0),
            "review_count": product.get("reviewCount", 0),
            "review_score": product.get("reviewScore", 0)
        })
    
    products_json = json.dumps(products_info, ensure_ascii=False, indent=2)
    
    return f"""
    You are an e-commerce search quality evaluator. Please analyze this Musinsa (Korean fashion e-commerce) search results screenshot along with the provided API data to calculate detailed search quality metrics.

    Search keyword: "{keyword if keyword else 'Unknown'}"

    API Data (Top {MAX_PRODUCTS} products):
    {products_json}

    Please evaluate based on these criteria:
    1. NDCG@10 (Normalized Discounted Cumulative Gain at 10): Measures the ranking quality of the top 10 search results, considering both relevance and position. Higher-ranked relevant items contribute more to the score. Range: 0.0-1.0, where 1.0 means perfect ranking of highly relevant items.
    
    2. Precision: The fraction of retrieved results that are relevant to the search query. Calculated as (Number of relevant results) / (Total number of results shown). Range: 0.0-1.0, where 1.0 means all shown results are relevant. Use API data to identify irrelevant products.
    
    3. Recall: The fraction of relevant items that were successfully retrieved by the search. Calculated as (Number of relevant results retrieved) / (Total number of relevant items that should exist). Range: 0.0-1.0, where 1.0 means all relevant items were found.

    Evaluation criteria:
    - Relevance between search keyword "{keyword if keyword else 'Unknown'}" and displayed products
    - Product image quality and appropriateness for the search term
    - Price information appropriateness
    - Brand information accuracy
    - How well the search results match what users would expect when searching for "{keyword if keyword else 'Unknown'}"

    IMPORTANT: For Precision analysis, identify specific products that are NOT relevant to the search keyword. For each irrelevant product, provide:
    - goods_no: Product number from API data
    - goods_name: Product name
    - reason: Why this product is not relevant to the search keyword

    Please respond ONLY in the following JSON format:
    {{
      "ndcg@10": 0.75,
      "precision": 0.82,
      "recall": 0.68,
      "ndcg_reason": "8 out of top 10 results show high relevance to search keyword '{keyword if keyword else 'Unknown'}' and are appropriately ranked.",
      "precision_reason": "8 out of 10 total results are relevant to the search keyword '{keyword if keyword else 'Unknown'}', showing high precision.",
      "recall_reason": "Most relevant products for '{keyword if keyword else 'Unknown'}' were retrieved, but some popular brands or specific styles are missing.",
      "precision_issues": [
        {{
          "goods_no": 1234567,
          "goods_name": "Example Irrelevant Product",
          "reason": "This product is not related to '{keyword if keyword else 'Unknown'}' search term because..."
        }}
      ]
    }}

    This is for academic research purposes to improve e-commerce search quality. Please provide the evaluation in the exact JSON format above.

    IMPORTANT: 
    - Do not include ```json code blocks or any markdown formatting. Return only the raw JSON object.
    - Analyze the screenshot visually AND cross-reference with the API data
    - Be specific about which products are irrelevant and why
    - If all products seem relevant, return an empty precision_issues array
    """
