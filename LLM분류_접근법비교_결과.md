# PROMPT_TEMPLATE = 'You are a web security expert. Classify each HTTP request as "Normal" or "Anomalous" and provide a brief reason.\n\nExamples:\nRequest: GET /index.jsp HTTP/1.1\nOutput: {{"label": "Normal", "reason": "Standard page request, no suspicious pattern"}}\n\nRequest: GET /search?q=\' OR \'1\'=\'1 HTTP/1.1\nOutput: {{"label": "Anomalous", "reason": "Classic SQL Injection pattern with OR 1=1"}}\n\nNow classify:\nRequest: {http_text}\nOutput:'
시간<br>
10/100건 완료 (7.9초, 건당 0.79초)<br>
20/100건 완료 (14.0초, 건당 0.70초)<br>
30/100건 완료 (20.5초, 건당 0.68초)<br>
40/100건 완료 (28.2초, 건당 0.71초)<br>
50/100건 완료 (36.0초, 건당 0.72초)<br>
60/100건 완료 (44.1초, 건당 0.74초)<br>
70/100건 완료 (50.2초, 건당 0.72초)<br>
80/100건 완료 (58.2초, 건당 0.73초)<br>
90/100건 완료 (65.4초, 건당 0.73초)<br>
100/100건 완료 (72.0초, 건당 0.72초)<br>
정확도<br>
```text
LLM 정확도: 0.8300
LLM F1:    0.8211
분류 실패(Unknown): 1건

              precision    recall  f1-score   support

      Normal       0.90      0.79      0.84        56
   Anomalous       0.76      0.89      0.82        44

    accuracy                           0.83       100
   macro avg       0.83      0.84      0.83       100
weighted avg       0.84      0.83      0.83       100