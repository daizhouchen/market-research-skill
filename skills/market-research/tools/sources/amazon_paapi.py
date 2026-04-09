"""
Amazon Product Advertising API 数据源 - 搜索Amazon商品信息

功能:
- 按关键词搜索Amazon商品
- 获取商品标题、价格、评分、评论数、特性和ASIN
- 简化实现(完整PA-API需要HMAC签名)

注意: 这是一个简化版实现。正式的Amazon PA-API v5需要:
- HMAC-SHA256 请求签名
- 正确的 AWS SigV4 认证头
实际生产环境建议使用 paapi5-python-sdk
"""

import hashlib
import hmac
import json as json_lib
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

try:
    import requests
except ImportError:
    requests = None
    print("[警告] 缺少 requests 依赖，请运行: pip install requests")

# PA-API v5 端点模板
PAAPI_ENDPOINTS = {
    "www.amazon.com": "webservices.amazon.com",
    "www.amazon.co.uk": "webservices.amazon.co.uk",
    "www.amazon.de": "webservices.amazon.de",
    "www.amazon.co.jp": "webservices.amazon.co.jp",
    "www.amazon.sg": "webservices.amazon.sg",
    "www.amazon.com.au": "webservices.amazon.com.au",
}

PAAPI_REGION_MAP = {
    "www.amazon.com": "us-east-1",
    "www.amazon.co.uk": "eu-west-1",
    "www.amazon.de": "eu-west-1",
    "www.amazon.co.jp": "us-west-2",
    "www.amazon.sg": "us-west-2",
    "www.amazon.com.au": "us-west-2",
}


def search_amazon(
    keywords: str,
    marketplace: str = "www.amazon.sg",
    config: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """搜索Amazon商品。

    Args:
        keywords: 搜索关键词
        marketplace: Amazon市场域名(如 "www.amazon.sg")
        config: API配置 {"access_key", "secret_key", "partner_tag"}

    Returns:
        {products: [{title, price, rating, review_count, features, asin}, ...]}

    注意: 这是简化实现，完整版需要HMAC签名认证。
    """
    if requests is None:
        return {
            "error": "requests 未安装，请运行: pip install requests",
            "products": [],
        }

    if config is None:
        config = {}

    access_key = config.get("access_key", "")
    secret_key = config.get("secret_key", "")
    partner_tag = config.get("partner_tag", "")

    if not all([access_key, secret_key, partner_tag]):
        return {
            "error": "缺少 Amazon PA-API 凭证(access_key, secret_key, partner_tag)",
            "products": [],
        }

    host = PAAPI_ENDPOINTS.get(marketplace, "webservices.amazon.com")
    region = PAAPI_REGION_MAP.get(marketplace, "us-east-1")
    path = "/paapi5/searchitems"

    # 构建请求体
    payload = {
        "Keywords": keywords,
        "PartnerTag": partner_tag,
        "PartnerType": "Associates",
        "Marketplace": marketplace,
        "Resources": [
            "ItemInfo.Title",
            "ItemInfo.Features",
            "Offers.Listings.Price",
            "ItemInfo.ByLineInfo",
        ],
        "SearchIndex": "All",
        "ItemCount": 10,
    }

    try:
        # 简化请求 - 真实环境需要 AWS SigV4 签名
        # 这里构建签名头用于演示
        headers = _build_signed_headers(
            host=host,
            path=path,
            payload=json_lib.dumps(payload),
            access_key=access_key,
            secret_key=secret_key,
            region=region,
        )

        url = f"https://{host}{path}"
        response = requests.post(
            url,
            json=payload,
            headers=headers,
            timeout=30,
        )
        response.raise_for_status()

        data = response.json()
        return _parse_search_results(data)

    except requests.exceptions.HTTPError as e:
        status = e.response.status_code if e.response is not None else "unknown"
        body = e.response.text[:300] if e.response is not None else ""
        return {
            "error": f"Amazon PA-API HTTP错误 {status}: {body}",
            "products": [],
        }
    except requests.exceptions.RequestException as e:
        return {"error": f"请求失败: {str(e)}", "products": []}
    except Exception as e:
        return {"error": f"未知错误: {str(e)}", "products": []}


def _build_signed_headers(
    host: str,
    path: str,
    payload: str,
    access_key: str,
    secret_key: str,
    region: str,
) -> Dict[str, str]:
    """构建带有AWS SigV4签名的请求头(简化版)。

    Args:
        host: API主机名
        path: API路径
        payload: 请求体JSON字符串
        access_key: AWS访问密钥
        secret_key: AWS秘密密钥
        region: AWS区域

    Returns:
        签名后的请求头字典
    """
    service = "ProductAdvertisingAPI"
    now = datetime.now(timezone.utc)
    amz_date = now.strftime("%Y%m%dT%H%M%SZ")
    date_stamp = now.strftime("%Y%m%d")

    # 计算payload哈希
    payload_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()

    # 构建规范请求
    canonical_headers = f"content-type:application/json; charset=utf-8\nhost:{host}\nx-amz-date:{amz_date}\n"
    signed_headers = "content-type;host;x-amz-date"
    canonical_request = f"POST\n{path}\n\n{canonical_headers}\n{signed_headers}\n{payload_hash}"

    # 构建签名字符串
    algorithm = "AWS4-HMAC-SHA256"
    credential_scope = f"{date_stamp}/{region}/{service}/aws4_request"
    string_to_sign = (
        f"{algorithm}\n{amz_date}\n{credential_scope}\n"
        + hashlib.sha256(canonical_request.encode("utf-8")).hexdigest()
    )

    # 计算签名
    def _sign(key: bytes, msg: str) -> bytes:
        return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()

    k_date = _sign(f"AWS4{secret_key}".encode("utf-8"), date_stamp)
    k_region = _sign(k_date, region)
    k_service = _sign(k_region, service)
    k_signing = _sign(k_service, "aws4_request")

    signature = hmac.new(
        k_signing, string_to_sign.encode("utf-8"), hashlib.sha256
    ).hexdigest()

    authorization = (
        f"{algorithm} "
        f"Credential={access_key}/{credential_scope}, "
        f"SignedHeaders={signed_headers}, "
        f"Signature={signature}"
    )

    return {
        "Content-Type": "application/json; charset=utf-8",
        "Host": host,
        "X-Amz-Date": amz_date,
        "Authorization": authorization,
        "Content-Encoding": "amz-1.0",
        "X-Amz-Target": "com.amazon.paapi5.v1.ProductAdvertisingAPIv1.SearchItems",
    }


def _parse_search_results(data: Dict[str, Any]) -> Dict[str, Any]:
    """解析Amazon PA-API搜索结果。

    Args:
        data: API响应JSON

    Returns:
        {products: [{title, price, rating, review_count, features, asin}, ...]}
    """
    products: List[Dict[str, Any]] = []
    items = data.get("SearchResult", {}).get("Items", [])

    for item in items:
        item_info = item.get("ItemInfo", {})
        title_info = item_info.get("Title", {})
        features_info = item_info.get("Features", {})
        offers = item.get("Offers", {})
        listings = offers.get("Listings", [])

        price_str = ""
        if listings:
            price_info = listings[0].get("Price", {})
            price_str = price_info.get("DisplayAmount", "")

        products.append({
            "title": title_info.get("DisplayValue", ""),
            "price": price_str,
            "rating": None,  # PA-API v5 不直接返回评分
            "review_count": None,
            "features": features_info.get("DisplayValues", []),
            "asin": item.get("ASIN", ""),
        })

    return {"products": products}


if __name__ == "__main__":
    import json
    import sys

    keywords = sys.argv[1] if len(sys.argv) > 1 else "smart watch"
    marketplace = sys.argv[2] if len(sys.argv) > 2 else "www.amazon.sg"

    print(f"正在搜索 Amazon: keywords={keywords}, marketplace={marketplace}")
    print("[提示] 需要在 config 参数中提供 access_key, secret_key, partner_tag")

    data = search_amazon(keywords, marketplace=marketplace)
    print(json.dumps(data, ensure_ascii=False, indent=2))
