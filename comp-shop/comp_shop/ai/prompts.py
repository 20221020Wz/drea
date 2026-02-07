"""AI Prompt模板 - 用于Claude API结构化输出"""

# ──────────────────── 关键词扩展 ────────────────────

KEYWORD_EXPANSION_PROMPT = """\
You are a product search expert for US hardware retail stores (Home Depot, Walmart, Lowe's, Harbor Freight).

Given a product category keyword, generate a comprehensive list of search keywords that would \
help find ALL products in this category across these retailers.

Category keyword: {keyword}

Requirements:
1. Include singular and plural forms
2. Include common synonyms and alternative names
3. Include subcategory-specific terms
4. Include brand-specific product line names if applicable
5. Keep keywords relevant - don't include unrelated tools

Return a JSON object:
{{
    "primary_keyword": "the main search term",
    "expanded_keywords": ["keyword1", "keyword2", "keyword3", ...],
    "subcategories": ["subcategory1", "subcategory2", ...],
    "notes": "any important notes about search strategy"
}}
"""

# ──────────────────── 规格提取 ────────────────────

SPEC_EXTRACTION_PROMPT = """\
You are a product specification extraction expert. Extract structured specifications \
from the following product information.

Product Name: {name}
Brand: {brand}
Description:
{description}

Raw Specifications:
{raw_specs}

Extract the following fields as a JSON object. If a field cannot be determined, use null.

{{
    "size": "Primary size measurement (e.g., '6 in.', '8 in.', '10 in.'). \
Standardize to inches.",
    "type": "Product type/subtype (e.g., 'Needle Nose Pliers', 'Locking Pliers', \
'Tongue and Groove Pliers', 'Diagonal Cutting Pliers')",
    "material": "Primary material (e.g., 'Chrome Vanadium Steel', 'Carbon Steel')",
    "features": ["key feature 1", "key feature 2"],
    "handle_type": "Handle material/type (e.g., 'Comfort Grip', 'Dipped', 'Bi-Material')",
    "jaw_type": "Jaw type if applicable (e.g., 'Straight', 'Curved', 'Serrated')",
    "cutting_capability": "Cutting capability if applicable",
    "adjustable": true/false,
    "set_size": "Number of pieces if it's a set (e.g., '3-Piece', '5-Piece'), null if single",
    "weight": "Weight with unit",
    "warranty": "Warranty information",
    "country_of_origin": "Manufacturing country"
}}

Important:
- Sizes should be standardized to inches (convert mm or cm if needed)
- For sets, identify the individual sizes included
- Features should be concise key selling points only
- Be precise with product type classification
"""

# ──────────────────── 维度推荐 ────────────────────

DIMENSION_RECOMMENDATION_PROMPT = """\
You are a market analysis expert for the US hardware/tools retail market.

Based on the following product data summary, recommend the best dimensions (axes) \
for creating a competitive comparison matrix.

Category: {category}
Total Products: {product_count}
Retailers: {retailers}

Available extracted fields and their value distributions:
{field_distributions}

Sample product names:
{sample_names}

Recommend 2-3 dimensions that would be most useful for:
1. Identifying market gaps (products competitors have but target retailer doesn't)
2. Making purchasing/assortment decisions
3. Comparing product coverage across retailers

Return a JSON object:
{{
    "primary_dimension": {{
        "field": "the field name to use as primary axis",
        "display_name": "Human-readable name for this dimension",
        "reason": "Why this dimension is most important"
    }},
    "secondary_dimension": {{
        "field": "the field name to use as secondary axis",
        "display_name": "Human-readable name",
        "reason": "Why this is a good secondary dimension"
    }},
    "optional_dimension": {{
        "field": "optional third dimension",
        "display_name": "Human-readable name",
        "reason": "Why this could add value"
    }},
    "matrix_layout": "Description of how the comparison matrix should be organized",
    "analysis_tips": ["tip1 for interpreting the matrix", "tip2", ...]
}}
"""

# ──────────────────── Gap分析 ────────────────────

GAP_ANALYSIS_PROMPT = """\
You are a market gap analysis expert for US hardware retail. Analyze the following \
competitive product data and identify market opportunities.

Target Retailer: {target_retailer}
Category: {category}

Product Coverage by Retailer:
{coverage_data}

Gap Summary (products competitors have but {target_retailer} doesn't):
{gap_data}

Price Range Analysis:
{price_analysis}

For each identified gap, provide:
1. Gap type (complete_gap, brand_gap, price_band_gap, feature_gap)
2. Specific description of the missing product/segment
3. Business priority (1-10 scale) with justification
4. Recommended action (product to develop, brand to acquire, etc.)
5. Expected market potential (based on competitor performance)

Return a JSON object:
{{
    "summary": "Executive summary of key findings (2-3 sentences)",
    "total_gaps_found": number,
    "opportunities": [
        {{
            "gap_type": "complete_gap|brand_gap|price_band_gap|feature_gap",
            "description": "Detailed description of the gap",
            "dimension": "Which dimension this gap is on",
            "dimension_value": "Specific value (e.g., '10 in.' or '$20-30')",
            "priority": 8,
            "priority_reason": "Why this priority score",
            "competitor_data": {{
                "retailers_with_product": ["retailer1", "retailer2"],
                "example_products": ["Product Name 1 ($XX)", "Product Name 2 ($XX)"],
                "avg_rating": 4.2,
                "avg_price": 25.99
            }},
            "recommendation": "Specific recommendation for filling this gap"
        }}
    ],
    "market_insights": ["insight1", "insight2", ...]
}}
"""

# ──────────────────── 数据清洗和标准化 ────────────────────

DATA_CLEANING_PROMPT = """\
You are a data quality expert. Review the following product data and identify any issues \
that need correction.

Products to review:
{products_json}

For each product, check:
1. Is the brand correctly identified? (Check against product name)
2. Is the price reasonable for this category?
3. Are there any obvious data extraction errors?
4. Is the product actually in the correct category?

Return a JSON object:
{{
    "corrections": [
        {{
            "sku": "product SKU",
            "field": "field to correct",
            "original_value": "current value",
            "corrected_value": "suggested correction",
            "reason": "why this correction is needed"
        }}
    ],
    "flagged_products": [
        {{
            "sku": "product SKU",
            "issue": "description of the issue",
            "severity": "high|medium|low"
        }}
    ],
    "data_quality_score": 0.95
}}
"""
