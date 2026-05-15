### 기존 프롬포트 
```
PROMPT_TEMPLATE = 'You are a web security expert. Classify each HTTP request as "Normal" or "Anomalous" and provide a brief reason.\n\nExamples:\nRequest: GET /index.jsp HTTP/1.1\nOutput: {{"label": "Normal", "reason": "Standard page request, no suspicious pattern"}}\n\nRequest: GET /search?q=\' OR \'1\'=\'1 HTTP/1.1\nOutput: {{"label": "Anomalous", "reason": "Classic SQL Injection pattern with OR 1=1"}}\n\nNow classify:\nRequest: {http_text}\nOutput:'
```

```
시간
  10/100건 완료 (8.3초, 건당 0.83초)
  20/100건 완료 (14.3초, 건당 0.72초)
  30/100건 완료 (21.6초, 건당 0.72초)
  40/100건 완료 (29.4초, 건당 0.74초)
  50/100건 완료 (37.3초, 건당 0.75초)
  60/100건 완료 (45.8초, 건당 0.76초)
  70/100건 완료 (52.3초, 건당 0.75초)
  80/100건 완료 (60.5초, 건당 0.76초)
  90/100건 완료 (67.6초, 건당 0.75초)
  100/100건 완료 (74.3초, 건당 0.74초)

총 소요: 74.3초
1만 건 환산: 약 124분

정확도

LLM 정확도: 0.8300
LLM F1:    0.8211
분류 실패(Unknown): 1건

              precision    recall  f1-score   support

      Normal       0.90      0.79      0.84        56
   Anomalous       0.76      0.89      0.82        44

    accuracy                           0.83       100
   macro avg       0.83      0.84      0.83       100
weighted avg       0.84      0.83      0.83       100
```

### 오탐 방지 Few-shot 프롬프트 (정확도 80%)
```
PROMPT_TEMPLATE = '''You are a web security expert. Classify each HTTP request as "Normal" or "Anomalous" and provide a brief reason.

Examples:
Request: GET /index.jsp HTTP/1.1
Output: {{"label": "Normal", "reason": "Standard page request, no suspicious pattern"}}

Request: GET /search?q=' OR '1'='1 HTTP/1.1
Output: {{"label": "Anomalous", "reason": "Classic SQL Injection pattern with OR 1=1"}}

Request: POST /tienda1/publico/entrar.jsp HTTP/1.1\nBody: errorMsg=Credenciales+incorrectas
Output: {{"label": "Normal", "reason": "Standard login error message, not an attack"}}

Request: GET /tienda1/publico/anadir.jsp?id=1&B1=Añadir+al+carrito HTTP/1.1
Output: {{"label": "Normal", "reason": "Normal e-commerce add-to-cart behavior"}}

Now classify:
Request: {http_text}
Output:'''
```
```
시간
  10/100건 완료 (5.9초, 건당 0.59초)
  20/100건 완료 (11.4초, 건당 0.57초)
  30/100건 완료 (17.8초, 건당 0.59초)
  40/100건 완료 (25.0초, 건당 0.62초)
  50/100건 완료 (31.9초, 건당 0.64초)
  60/100건 완료 (38.5초, 건당 0.64초)
  70/100건 완료 (44.6초, 건당 0.64초)
  80/100건 완료 (50.4초, 건당 0.63초)
  90/100건 완료 (56.9초, 건당 0.63초)
  100/100건 완료 (62.4초, 건당 0.62초)

총 소요: 62.4초
1만 건 환산: 약 104분

정확도
LLM 정확도: 0.8000
LLM F1:    0.7561
분류 실패(Unknown): 1건

              precision    recall  f1-score   support

      Normal       0.79      0.88      0.83        56
   Anomalous       0.82      0.70      0.76        44

    accuracy                           0.80       100
   macro avg       0.80      0.79      0.79       100
weighted avg       0.80      0.80      0.80       100
```

### 생각의 사슬 (Chain-of-Thought) 유도 프롬프트
```
PROMPT_TEMPLATE = '''Analyze the HTTP request strictly for security threats. Classify as "Normal" or "Anomalous".
Do not flag normal e-commerce traffic or application errors as anomalous. 
Only flag true threats like SQLi, XSS, and unauthorized access.

Examples:
Request: GET /index.jsp HTTP/1.1
Output: {{"label": "Normal", "reason": "The request only asks for the root index page without any parameters. Safe."}}

Request: GET /item?id=1; DROP TABLE users HTTP/1.1
Output: {{"label": "Anomalous", "reason": "The id parameter contains a semicolon followed by a SQL DROP statement. Severe SQLi."}}

Now classify:
Request: {http_text}
Output:'''
```
```
시간
  10/100건 완료 (8.5초, 건당 0.85초)
  20/100건 완료 (14.8초, 건당 0.74초)
  30/100건 완료 (21.9초, 건당 0.73초)
  40/100건 완료 (30.1초, 건당 0.75초)
  50/100건 완료 (38.2초, 건당 0.76초)
  60/100건 완료 (46.3초, 건당 0.77초)
  70/100건 완료 (53.4초, 건당 0.76초)
  80/100건 완료 (60.6초, 건당 0.76초)
  90/100건 완료 (68.0초, 건당 0.76초)
  100/100건 완료 (74.9초, 건당 0.75초)

총 소요: 74.9초
1만 건 환산: 약 125분
정확도
LLM 정확도: 0.7800
LLM F1:    0.7500
분류 실패(Unknown): 1건

              precision    recall  f1-score   support

      Normal       0.80      0.80      0.80        56
   Anomalous       0.75      0.75      0.75        44

    accuracy                           0.78       100
   macro avg       0.78      0.78      0.78       100
weighted avg       0.78      0.78      0.78       100

```