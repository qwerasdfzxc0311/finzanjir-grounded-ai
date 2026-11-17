# FINZANJIR: bepul va chidamli xotira infratuzilmasi

**Holat:** taklif / ko‘rib chiqish uchun. Hech qanday Cloudflare resursi yaratilmagan va production trafik ko‘chirilmagan.
**Tekshiruv sanasi:** 2026-11-17.

## 1. Maqsad
FINZANJIR shaxsiy ma’lumotlari, hujjatlari, rasmlari, audiosi, videolari, tadqiqot natijalari va avtonom ish holatini imkon qadar bepul, xavfsiz va uzoq muddat saqlash. Egasi uzoq vaqt tizimga kirmasa ham, mavjud vazifalar yo‘qolmasligi va ruxsatlar o‘z-o‘zidan kengaymasligi kerak.

## 2. Asosiy xulosa
Bepul xizmatlar bilan boshlang‘ich darajada doimiy saqlash va qisqa, bo‘laklarga bo‘lingan fon vazifalarini qurish mumkin. Biroq hech bir bepul provayder 10 yil davomida o‘zgarmas bepul tarif, uzluksiz compute yoki mutlaq ma’lumot saqlanish kafolatini bermaydi. Shu sababli FINZANJIR bitta provayderga yoki bitta nusxaga tayanmasligi kerak.

## 3. Ko‘rib chiqilgan variantlar

### A. Cloudflare D1 + R2 + Workers (asosiy nomzod)
- D1 Free: bitta baza 500 MB; akkaunt bo‘yicha jami 5 GB; kuniga 5 mln row read va 100 ming row write; Free Time Travel 7 kun.
- R2 Standard Free: oy davomida o‘rtacha 10 GB saqlash, oyiga 1 mln Class A va 10 mln Class B operatsiya; egress bepul.
- Workers Free: kuniga 100 ming so‘rov; HTTP/Cron chaqiruviga 10 ms CPU; Cron chaqiruvi maksimal wall time 15 daqiqa; akkauntda 5 ta Cron Trigger.
- D1 metadata, vazifa holati, indekslar va manifestlar uchun; R2 shifrlangan fayl obyektlari uchun; Worker kichik vazifa bo‘laklari, jadval va nazorat uchun.
- D1 Time Travel faqat 7 kunlik tiklash oynasi. Bu uzoq muddatli yoki provayderdan mustaqil zaxira nusxasi o‘rnini bosmaydi.
- R2 va D1 bitta provayder ichida. Cloudflare akkaunti yo‘qolsa yoki bloklansa, ikkalasi birgalikda xavf ostida; shu sababli ikkinchi provayderga mustaqil shifrlangan nusxa zarur.

### B. Supabase Free (ikkinchi darajali variant)
- 500 MB Postgres; 1 GB file storage; avtomatik backup yo‘q; 7 kun faollik past bo‘lsa loyiha pauzaga tushishi mumkin.
- Uzoq muddatli yagona asosiy ombor sifatida tavsiya etilmaydi.

### C. Render Free
- Web service fayl tizimi ephemeral; Free Postgres 30 kundan keyin tugaydi; Free Background Worker yo‘q.
- FINZANJIRning yagona doimiy xotirasi yoki avtonom worker hosti bo‘la olmaydi.

### D. Google Drive akkauntlari — mustaqil zaxira va manba
- Oddiy shaxsiy Google akkauntida 15 GB umumiy joy Drive, Gmail va Photos o‘rtasida bo‘linadi.
- 100 akkaunt nazariy jihatdan ko‘p alohida manba beradi, lekin bu bitta umumiy 1.5 TB bepul quota yoki kafolatlangan saqlash hajmi degani emas. Har bir akkauntning bo‘sh joyi, API ruxsati, quota, tiklash emaili va egasi alohida nazorat qilinadi.
- Google shaxsiy akkauntlari 2 yil ishlatilmasa o‘chirilishi mumkin. Google Photos mahsulotida ham 2 yil faoliyatsizlik bo‘yicha alohida o‘chirish siyosati bor. Shuning uchun uzoq muddatli arxivni faqat Google akkauntlariga tashlab qo‘yish mumkin emas.
- Drive nusxalari FINZANJIR tomonidan oldindan shifrlanadi; Google faqat shifrlangan backup fayllarini ko‘radi. Har bir hisob faqat egasi alohida ulagan va ruxsat bergan doirada ishlatiladi.

## 4. Tavsiya etilgan arxitektura
1. **Render API/frontend:** mavjud foydalanuvchi interfeysi va API qoladi. Render ephemeral filesystem xotira sifatida ishlatilmaydi.
2. **Cloudflare D1:** account registry, source metadata, job queue, checkpoints, content hashes, audit events, backup manifests va search metadata.
3. **Cloudflare R2:** fayllarning shifrlangan blob nusxalari (DOCX/PDF/rasm/audio/video), original fayl nomi va metadata esa D1 da alohida.
4. **Cloudflare Worker Cron:** har 5 daqiqada navbatni tekshiradigan kichik coordinator. U og‘ir OCR, video/audio transkripsiya yoki model inference bajarmaydi; faqat bounded step va tashqi API chaqiruvlarini boshqaradi.
5. **Mustaqil backup:** har kuni D1 export + R2 object manifest shifrlanib, egasi tanlagan Google Drive akkaunt(lar)i va egasining offline qurilmasiga nusxalanadi.
6. **Offline recovery:** shifrlash kalitining recovery nusxasi Cloudflare va Google Drive’dan tashqarida saqlanadi. Kalit yo‘qolsa, shifrlangan backupni tiklab bo‘lmaydi.

## 5. 60 daqiqa ish / 10 daqiqa dam olish qoidasi
Bepul Worker 60 daqiqa uzluksiz ishlay olmaydi: Cron chaqiruvining maksimal davomiyligi 15 daqiqa va CPU limiti 10 ms. Shu sababli bu qoida uzluksiz bitta process sifatida emas, balki D1 da saqlanadigan state machine sifatida bajariladi:
- work_window_started_at, work_deadline, rest_until, last_checkpoint, lease_owner, lease_expires_at saqlanadi.
- Har chaqiruv bitta kichik vazifa bajaradi, checkpoint yozadi va chiqadi.
- 60 daqiqalik faol ish oynasi tugagach, rest_until = now + 10 minutes; shu vaqtgacha yangi tadqiqot qadami olinmaydi.
- Har bir vazifa idempotent bo‘ladi; lease muddati tugasa boshqa chaqiruv checkpointdan davom ettiradi.
- Xatolar retry budget, exponential backoff va quarantine bilan boshqariladi.
- Worker faqat boshqaruv va yengil I/O; katta fayl parsing, OCR, multimodal inference va model training alohida compute talab qiladi. Bepul Cloudflare Worker bular uchun yetarli deb ko‘rsatilmaydi.

Bu mexanizm vaqt oralig‘ini boshqaradi, ammo provayder Cron ishga tushishini kafolatlamaydi. Uzoq muddatli unattended compute uchun bepul tarif kafolati yo‘q.

## 6. Ma’lumot yo‘qolishiga qarshi himoya
- 3-2-1 tamoyili: kamida 3 nusxa, kamida 2 mustaqil saqlash muhiti/provayder, kamida 1 offline nusxa.
- Fayl R2 ga yozilishidan oldin AES-256-GCM bilan shifrlanadi; nonce har obyekt uchun noyob; integrity hash va format versiyasi manifestga yoziladi.
- Backup obyektlari timestamp va content hash bilan immutable nomlanadi; mavjud backup ustiga yozilmaydi.
- D1 Time Travel (7 kun) tezkor tiklash uchun; kunlik export esa Cloudflare’dan tashqaridagi mustaqil Drive va offline nusxaga.
- Har kuni backup natijasi tekshiriladi; har oy tasodifiy backupdan alohida test muhitiga tiklash sinovi o‘tkaziladi.
- Backup muvaffaqiyatsiz bo‘lsa, yangi import/knowledge promotion vaqtincha to‘xtaydi va diagnostikada ogohlantirish ko‘rsatiladi.
- Kalitlar, OAuth tokenlar va maxfiy ma’lumotlar loglarga yozilmaydi; kalit backup obyektlari bilan bir joyda saqlanmaydi.

## 7. Xavfsizlik va shaxsiylik
- Har bir Google akkaunt owner ID bilan bog‘lanadi; akkauntlar o‘rtasida ma’lumotlar aralashmaydi.
- OAuth tokenlar server-side shifrlanadi; scope alohida va eng kam imtiyozli; Drive backup uchun faqat app tomonidan yaratilgan/tanlangan fayllar ruxsati.
- Google Photos Picker faqat foydalanuvchi tanlagan media bilan ishlaydi; Google Photos to‘liq kutubxonasini cheksiz ko‘rish deb va’da qilinmaydi.
- Import qilingan hujjat va media avval quarantine; manba, akkaunt, file ID, hash, sana va ruxsatlar bilan saqlanadi.
- Hech qanday backup avtomatik ravishda authoritative FINZANJIR bilim bazasi yoki trening datasetiga qo‘shilmaydi.
- Tizim o‘z ruxsatini kengaytira olmaydi, Google parolini ko‘rmaydi, fayllarni o‘chirmaydi yoki foydalanuvchi roziligisiz tashqi joyga ulashmaydi.

## 8. Ishga tushirish darvozalari
Quyidagilar bajarilmaguncha haqiqiy shaxsiy ma’lumot importi yoqilmaydi:
1. Owner-only Cloudflare account va kerakli API token scopes tasdiqlanishi.
2. D1/R2 test resurslari yaratilishi va minimal ruxsat bilan bog‘lanishi.
3. AES-GCM encrypt/decrypt, nonce, hash va key recovery testlari o‘tishi.
4. D1 export, R2 backup, Drive mirror va restore drill muvaffaqiyatli bo‘lishi.
5. Worker cron, lease, checkpoint, 60/10 state machine, retry va duplicate delivery testlari o‘tishi.
6. Per-account isolation, OAuth revocation, access audit va data deletion testlari o‘tishi.
7. Usage budget guard: bepul limitga yaqinlashganda yangi ishlarni xavfsiz pauza qilish; pulli resurslar avtomatik yoqilmasligi.
8. Faqat shundan keyin egasi alohida ruxsat bergan Google akkauntlari bilan kichik sinov.

## 9. Qabul mezonlari
- Render restart/redeploy D1/R2 ma’lumotlariga ta’sir qilmaydi.
- Bir xil backup qayta yuborilsa duplicate obyekt yoki buzilgan indeks paydo bo‘lmaydi.
- Har bir obyekt hash bilan tekshiriladi.
- Backup nusxasidan mustaqil tiklash ko‘rsatiladi.
- Worker to‘xtab qolsa, lease tugagach oxirgi checkpointdan davom etadi.
- 60/10 rejimi server restarts va duplicate Cron chaqiruvlarida buzilmaydi.
- Limit tugasa, ma’lumot o‘chirilmaydi va kutilmagan pulli xarajat yuzaga kelmaydi.
- Bir Google akkauntdagi ma’lumot boshqa akkauntga yoki boshqa FINZANJIR foydalanuvchisiga chiqmaydi.

## 10. Rasmiy manbalar
- Cloudflare D1 limits: https://developers.cloudflare.com/d1/platform/limits/
- D1 Time Travel: https://developers.cloudflare.com/d1/reference/time-travel/
- Cloudflare R2 pricing: https://developers.cloudflare.com/r2/pricing/
- Workers limits: https://developers.cloudflare.com/workers/platform/limits/
- Cron Triggers: https://developers.cloudflare.com/workers/configuration/cron-triggers/
- Supabase Free pausing: https://supabase.com/docs/guides/platform/free-project-pausing
- Render Free limitations: https://render.com/docs/free
- Google storage quotas: https://support.google.com/accounts/answer/9312312
- Google inactive account policy: https://support.google.com/accounts/answer/12418290
