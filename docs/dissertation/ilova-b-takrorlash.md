# B ilova. Natijalarni takrorlash

Muhit: Python 3.11+ (3.13 da tekshirilgan), `pip install -r requirements.txt`.
Barcha buyruqlar repozitoriy ildizidan, `PYTHONPATH=backend` bilan ishga tushiriladi.

```bash
# 1. Maʼlumot (kumush annotatsiya, BIO, to'plamlar)
python -m app.annotation.silver                       # data/silver/ -> data/annotations/claude/
python -m app.annotation.sequential claude2           # test, uchrash-ma-uchrash -> data/annotations/claude2/
python -m app.dataset.split data/annotations/claude/*.jsonl --include-drafts --output-dir data/processed/silver
python -m app.dataset.bio sample                      # 100 gap + data/bio/review.txt -> data/bio/sentences-100.jsonl
python -m app.dataset.bio validate data/bio/sentences-100.jsonl
python -m app.dataset.bio export data/processed/silver/train.jsonl -o data/processed/bio/train.jsonl

# 2. Lug'at (faqat train)
python -m app.annotation.dictionary

# 3. Modellar va aniqlash tajribalari (≈ 2.5 daqiqa, 4 yadro)
python -m app.models.experiment                                   # 2.2-jadval, models/*.crfsuite
python -m app.models.experiment --test-files data/annotations/claude2/*.jsonl \
       --output reports/experiment-silver-test2.json              # 2.3-jadval

# Alohida o'qitish / qayta yuklab baholash / matnni tahlil qilish
python -m app.models.crf train data/processed/silver/train.jsonl --model models/crf-gazetteer.crfsuite --gazetteer data/terms.json
python -m app.models.crf evaluate data/processed/silver/test.jsonl --model models/crf-gazetteer.crfsuite
python -m app.models.crf predict "Morfonologiya tilshunoslik boʻlimi." --model models/crf.crfsuite

# 4. Meʼyorlashtirish (3.1-jadval)
python -m app.evaluation.normalization data/processed/silver/test.jsonl --output reports/normalization-test.json

# 4a. Variantdorlik: guruhlash, sinonim/dublet, omonimiya (3.2–3.4-jadvallar)
python -m app.variation.experiment                    # -> reports/variation.json, reports/variation-groups.json

# 4b. Meʼyor tekshiruvi (3.6-jadval)
python -m app.norms.experiment                        # -> reports/term-check-synthetic.json
python -m app.norms.checker --output reports/term-check.json --review-sample data/judgments/term-check-review.csv
python -m app.norms.checker "Fonemalar" "o'zak" "фонема"   # alohida terminlar

# 4c. Tezaurus (2.5-jadval)
python -m app.ontology.thesaurus                      # -> reports/thesaurus.json, reports/thesaurus.ttl

# 5. Statistik nomzodlar (2.1-jadval)
python -m app.nlp.candidates --method tfidf --pos-filter --top 0 --output reports/candidates-tfidf-pos.csv
python -m app.evaluation.judgments score --rankings reports/candidates-tfidf.csv reports/candidates-tfidf-pos.csv \
       --judgments data/judgments/candidates-claude.csv
python -m app.nlp.candidates --method ncvalue --top 0 --output reports/candidates-ncvalue.csv
python -m app.nlp.candidates --method cvalue --pattern-filter --top 0 --output reports/candidates-cvalue-pattern.csv
python -m app.nlp.candidates --method weirdness --pattern-filter --contrast data/contrast/raw/*.txt \
       --top 0 --output reports/candidates-weirdness-pattern.csv
python -m app.evaluation.judgments score --rankings reports/candidates-*.csv \
       --judgments data/judgments/candidates-adjudicated.csv

# 5a. Lingvistik / statistik / gibrid modellar, span darajasida (2.1a-jadval)
python -m app.models.pattern_experiment               # -> reports/experiment-patterns.json

# 5b. Transformer (GPU, Google Colab: notebooks/xlmr_colab.ipynb)
pip install torch transformers sentencepiece
python -m app.models.transformer --model xlm-roberta-base         # 2.2.7-bo'lim, models/transformer/
python -m app.models.transformer --load --test-files data/annotations/claude2/*.jsonl \
       --output reports/experiment-transformer-test2.json

# 6. Taqqoslash jadvali
python -m app.evaluation.report                       # -> docs/experiments-table.md

# 7. Testlar va interfeyslar
python -m pytest
streamlit run streamlit_app.py                        # http://localhost:8501
uvicorn app.main:app --port 8000 && (cd frontend && npm run dev)   # React: tahlil, annotatsiya, baholash
```

**Determinizm.** Quyidagilar har safar bir xil natija beradi:

- to'plamlarga ajratish va 100 gapni tanlash — tasodifiylik yo'q;
- CRF — L-BFGS, tasodifiy boshlang'ich qiymat yo'q;
- bootstrap — qat'iy `seed = 13`.

| Komponent | Versiya |
|---|---|
| python-crfsuite | 0.9.12 (CRFsuite 0.12) |
| FastAPI | 0.162.0 |
| Streamlit | 1.50.0 |
| React | 19 |
| Vite | 7 |
