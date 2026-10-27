# UzTerm AI — web interfeys

React + TypeScript + Vite. Backend (FastAPI) bilan `/api` orqali ishlaydi.

## Ishga tushirish

Avval backendni ishga tushiring (repo ildizida, README'ga qarang). Keyin:

```bash
cd frontend
npm install
npm run dev
```

Brauzerda: http://localhost:5173. Vite `/api` so'rovlarini
`http://127.0.0.1:8000` ga yuboradi. Backend boshqa portda bo'lsa:

```bash
UZTERM_API_URL=http://127.0.0.1:8765 npm run dev
```

## Buyruqlar

| Buyruq | Vazifasi |
|---|---|
| `npm run dev` | dev-server |
| `npm test` | `vitest` testlari (`src/*.test.ts`) |
| `npm run typecheck` | TypeScript tekshiruvi |
| `npm run build` | production build (`dist/`) |

## Tuzilma

| Fayl | Vazifasi |
|---|---|
| `src/App.tsx` | sahifa: matn kiritish, holatlar (yuklanish, xato, bo'sh natija, eski natija), eksport |
| `src/components/HighlightedText.tsx` | matnda terminlarni ajratib ko'rsatish |
| `src/components/ResultsTable.tsx` | natijalar jadvali |
| `src/components/TermDetails.tsx` | tanlangan termin tafsilotlari (taʼrif, manba, meʼyoriy shakl) |
| `src/segments.ts` | backend pozitsiyalarini matn bo'laklariga aylantirish |
| `src/exporters.ts` | JSON va CSV eksport |
| `src/api.ts` | API so'rovlari va xato xabarlari |

**Pozitsiyalar.** Backend `start`/`end` ni Unicode belgilari bo'yicha
qaytaradi, JavaScript satrlari esa UTF-16 bo'yicha indekslanadi. Shuning uchun
`segments.ts` matnni `Array.from` bilan belgilarga ajratadi. Aks holda emoji
kabi belgilardan keyin belgilash siljib ketadi; bu holat testda tekshiriladi.
