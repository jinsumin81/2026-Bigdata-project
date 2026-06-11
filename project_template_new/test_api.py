import os
import requests
import xml.etree.ElementTree as ET
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
SERVICE_KEY = os.getenv("WORKNET_API_KEY", "")

BASE_URL = "https://www.work24.go.kr/cm/openApi/call/wk/callOpenApiSvcInfo212L01.do"

def search_jobs(keyword: str):
    params = {
        "authKey":    SERVICE_KEY,
        "returnType": "XML",
        "target":     "JOBCD",
        "srchType":   "K",
        "keyword":    keyword,
    }
    print(f"\n[검색어] {keyword}")
    res = requests.get(BASE_URL, params=params, timeout=10)
    print(f"[상태코드] {res.status_code}")
    print(f"[응답 원문 앞 800자]\n{res.text[:800]}\n")

    if res.status_code != 200:
        return []

    root = ET.fromstring(res.text)
    jobs = []
    for item in root.iter("jobList"):
        jobs.append({
            "직업코드":   item.findtext("jobCd") or "",
            "직업명":     item.findtext("jobNm") or "",
            "직업분류명": item.findtext("jobClcdNM") or "",
        })
    return jobs

if __name__ == "__main__":
    if not SERVICE_KEY:
        print("WORKNET_API_KEY가 .env에 없습니다.")
    else:
        results = search_jobs("IT")
        if results:
            print("=== 검색 결과 ===")
            for j in results:
                print(f"  [{j['직업코드']}] {j['직업명']} ({j['직업분류명']})")
        else:
            print("결과 없음")
