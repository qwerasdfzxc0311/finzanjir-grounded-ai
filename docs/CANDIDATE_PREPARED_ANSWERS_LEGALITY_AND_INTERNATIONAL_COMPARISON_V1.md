# Candidate prepared answers: legality and international comparison

**Status:** candidate wording only — not a legal opinion, not an approved canonical runtime answer, and not evidence that FINZANJIR is authorized or operational.

**Purpose:** prepare careful answers for expert questions while preserving the distinction between the author's intent, documented design principles, legal verification, prototype status, and actual deployment.

## Muallifning mutaxassislar bilan ishlashga tayyorligi — ikkala javob uchun umumiy pozitsiya

Ikkala savolga javob berishda muallifning pozitsiyasi «FINZANJIR tayyor, hamma masala hal qilingan» yoki «men hamma narsani bilaman» degan da'vo bo'lmasligi kerak. To'g'ri mazmun quyidagicha:

«Men FINZANJIR ustida izlandim, imkonim va mavjud sharoitim doirasida konsepsiya, tahlil, dastlabki texnik ishlar va ayrim sinovlarni amalga oshirdim. Shu jarayonda ko'plab masalalarni o'rgandim, lekin barcha yo'nalishlarni oxirigacha yetkazish imkonim bo'lmadi. Buning huquqiy, texnik, moliyaviy va tashkiliy sabablari ham bo'ldi. Men loyihamni xatosiz deb hisoblamayman: unda kamchiliklar, tekshirilishi kerak bo'lgan taxminlar va hali yechilmagan savollar borligini tan olaman. Aynan shuning uchun tajribali mutaxassislar bilan ochiq muhokama, mustaqil audit va tanqidiy baholashni istayman. Maqsadim tayyor deb e'lon qilish emas, balki to'g'ri yo'nalishni aniqlab, kamchiliklarni tuzatish, xavfsiz va qonuniy chegaralarni mustahkamlash hamda imkoniyat bo'lsa, ishni bosqichma-bosqich davom ettirishdir.»

Bu fikr muallifning kamchiliklarni tan olishga tayyorligini ko'rsatadi, ammo hujjat bilan tasdiqlanmagan ishlarni bajarilgan deb ko'rsatmaydi. «Dastlabki ishlar» deyilganda faqat real mavjud konsepsiya, tahlil, prototip yoki sinovlar nazarda tutiladi; har birining holati alohida ko'rsatiladi.

## 1. “FINZANJIR qonuniymi? Qonuniy ishlay oladimi?”

### Candidate Uzbek answer

FINZANJIR muallifining maqsadi hech qachon qonunni chetlab o'tadigan yoki fuqarolarning huquqlarini buzadigan tizim yaratish bo'lmagan. Aksincha, loyiha ustida izlanish olib borilgan davrda uning ishlashi qonun va vakolat doirasiga mos bo'lishi, fuqarolarning qonuniy operatsiyalariga asossiz zarar yetkazmasligi hamda axborot xavfsizligi har tomonlama hisobga olinishi kerakligi asosiy tamoyil sifatida ko'zda tutilgan.

Shu sababli konsepsiyada ma'lumotlarni sababsiz, cheksiz hajmda yoki muddatsiz yig'ish emas, balki aniq maqsad uchun zarur bo'lgan eng kam ma'lumot bilan ishlash; ma'lumotni faqat tegishli qonuniy asos va vakolat mavjud bo'lganda olish yoki qayta ishlash; saqlash muddatini oldindan belgilash; muddat tugaganda qonuniy tartibda o'chirish yoki arxivlash; kirishni vakolatli shaxslar bilan cheklash; har bir murojaat va harakatni qayd etish kabi talablar ko'zlangan. Banklar o'rtasida esa xom mijoz ma'lumotlarini cheklanmagan tarzda tarqatish emas, balki faqat qonuniy ravishda almashishga ruxsat etilgan, aniq maqsadga zarur bo'lgan minimal signal yoki indikatorlardan foydalanish yo'li o'rganilgan. Biroq signalni qisqartirish, kodlash yoki shaxssizlantirishning o'zi ham uni avtomatik ravishda qonuniy qiladi, deb bo'lmaydi: qayta aniqlash imkoniyati, bank siri, shaxsga doir ma'lumotlar va almashishning aniq huquqiy asosi alohida tekshirilishi kerak.

Bu tamoyillar muallifning yo'nalishi va loyiha uchun qo'yilgan talablarni ifodalaydi. Ular barcha huquqiy masalalar hal qilinganini, barcha zarur ruxsatlar olinganini yoki FINZANJIR hozir banklararo real ma'lumot almashib ishlayotganini anglatmaydi. Izlanish davomida huquqiy, texnik, moliyaviy va tashkiliy qiyinchiliklar sabab ishni to'liq yakunlash imkoni bo'lmagan. Shuning uchun hozirgi to'g'ri javob: FINZANJIR qonuniy ishlashga moslashtirilishi ko'zlangan, lekin uning to'liq qonuniy ishga tushishi hali mutaxassislar bilan tekshirilishi va tegishli vakolatli tashkilotlar hamda banklarning huquqiy, komplayens, axborot xavfsizligi va texnik bahosidan o'tishi kerak.

Keyingi bosqichda har bir ma'lumot turi bo'yicha alohida jadval tuzilishi lozim: nima olinadi, nima uchun kerak, kim oladi, qaysi huquqiy asosga tayanadi, kim bilan va qaysi shartlarda almashiladi, qayerda saqlanadi, qancha muddat saqlanadi, kim kira oladi va muddat tugaganda nima qilinadi. Shundan keyingina ruxsat etilgan ma'lumot oqimi va pilot doirasi aniqlanishi mumkin. FINZANJIRning pozitsiyasi — qonunni buzib keyin moslashtirish emas, balki qonun va vakolat chegaralarini oldindan aniqlab, arxitekturani shu chegaralarga mos qurishdir. Muallif bu talablarning barchasi amalda to'liq bajarilgan deb da'vo qilmaydi; aksincha, mavjud yechimlarni mutaxassislar bilan audit qilish, xatolar va yetishmayotgan jihatlarni aniqlash, so'ngra ularni qonuniy asosda tuzatish uchun ochiq.

### Mandatory answer boundaries

- Never answer simply “yes, FINZANJIR is legal” or “no, it is illegal” without a dated legal assessment of the actual activity, actors, data, purpose, and permissions.
- Never present the author's good-faith intention as a legal authorization, regulator approval, or completed compliance audit.
- Treat “signal”, hashed/pseudonymized identifier, or reduced dataset as potentially protected information until legal re-identification and secrecy analysis is completed.
- Do not imply that a central exchange, cross-bank sharing, or any particular data field is permitted merely because it is technically possible.
- State clearly that concept/prototype, controlled pilot, and live interbank operation have different legal and operational requirements.
- Keep current Uzbek law, Central Bank requirements, bank secrecy, personal-data rules, cybersecurity, localization/cross-border transfer, retention/deletion, and bank contracts in a dated source map reviewed by qualified local counsel and relevant institutions.

## 2. “Boshqa davlatlarda FINZANJIRga o'xshash tizimlar bormi? FINZANJIR ulardan nusxa olinganmi?”

### Candidate Uzbek answer

Ha, FINZANJIR ko'zlagan ayrim vazifalarga o'xshash yondashuvlar boshqa davlatlarda ham mavjud. Shuning uchun “bunday tizimlar dunyoda umuman yo'q” deyish to'g'ri bo'lmaydi. Masalan, FATFning 2026-yilgi xalqaro sharhida kamida 84 ta davlat-xususiy sektor hamkorligi qayd etilgan; 52 ta yurisdiksiya kamida bitta shunday hamkorlikka ega ekanini bildirgan. Bu tashabbuslarning tuzilishi, vakolati, ma'lumot almashish doirasi va ishlash usuli bir xil emas.

Ayrim misollar: Fransiyada Banque de France boshqaruvidagi FNC-RF 2026-yil 7-maydan ishlay boshlagan bo'lib, firibgarlik xavfi bilan bog'liq deb belgilangan IBANlar haqidagi cheklangan ma'lumotlarni to'lov xizmatlari provayderlari o'rtasida almashishga xizmat qiladi. Unda hisob egasining shaxsi umumiy yozuvda berilmaydi; hisob yurituvchi bank o'z tekshiruvini o'tkazib, natijani qaytaradi. Janubiy Koreyada ASAP platformasi 2025-yil oktabrda ishga tushirilgan; 2026-yil 4-avgustdan kuchga kirgan yangilangan qoidalar moliya kompaniyalari, telekommunikatsiya provayderlari va tergov organlari o'rtasida vishing bilan bog'liq ma'lumot almashish imkoniyatini kengaytirgan. Buyuk Britaniyada JMLIT+ davlat organlari va moliya sektori o'rtasidagi moliyaviy jinoyatlarga qarshi hamkorlik modelidir. Singapur boshchiligidagi Project FRONTIER+ esa bir nechta yurisdiksiyani qamrab olgan transmilliy firibgarlikka qarshi hamkorlik misolidir. Bular FINZANJIRning to'liq nusxasi yoki aynan bir xil tizimlar degani emas; ular faqat ayrim vazifalar, hamkorlik mexanizmlari yoki ma'lumot almashish yondashuvlari bo'yicha qiyosiy misollardir.

FINZANJIRni “dunyoda yagona” yoki “boshqa tizimlarning to'liq nusxasi” deb ta'riflash ham to'g'ri emas. Loyiha tashqi tajribani o'rganish, turli mamlakatlarda nimalar ishlagani va qaysi joylarda huquqiy, texnik, tashkiliy yoki moliyaviy to'siqlar yuzaga kelganini tahlil qilish asosida O'zbekiston sharoitiga mos yechim ishlab chiqishga qaratilgan. Buni isbotlash uchun har bir o'xshash tashabbusning vazifasi, huquqiy asosi, boshqaruv modeli, ishtirokchilari, ma'lumot almashish chegarasi, natijalari, xarajatlari va davomiyligi bo'yicha alohida taqqoslash kerak. Hozircha aniq manba bilan tasdiqlanmagan “falon tizim mablag' yetishmagani uchun yopilgan” kabi xulosalarni fakt sifatida aytmaslik kerak. Bunday holatlar uchrasa, ularning yopilish sababi rasmiy hisobot yoki ishonchli tahlil bilan tekshiriladi.

FINZANJIRning asosiy qarashi — moliyaviy firibgarlikni bitta belgi yoki bitta vosita bilan to'liq yo'q qilib bo'lmaydi. Buni uy atrofiga ekin ekilgan maydon misolida tushuntirish mumkin: sim to'r yirik hayvonlarni to'xtatishi mumkin, ammo tovuq yoki boshqa mayda jonivorlar kirishi ehtimoli qoladi; devor bu xavfni kamaytiradi, lekin zararli hasharotlar yoki ekinga ta'sir qiladigan boshqa omillarni bartaraf etmaydi. Demak, to'r, devor va zararkunandalarga qarshi choralar birgalikda yaxshiroq himoya beradi. Moliyaviy xavfsizlikda ham bank nazorati, firibgarlik indikatorlari, qonuniy ma'lumot almashish, inson ko'rigi, fuqarolar murojaatlari va boshqa himoya qatlamlari bir-birini to'ldirishi mumkin. Har bir qatlamning o'z chegarasi bor; hech biri mutlaq kafolat bermaydi.

Shu ma'noda FINZANJIR turli muammolarni bitta “sehrli” vosita bilan hal qilishni emas, balki ular o'rtasidagi bog'liqliklarni yagona zanjir sifatida ko'rib, mavjud qonuniy va institutsional mexanizmlarni bir-birini to'ldiradigan tarzda bog'lash imkoniyatini o'rganadi. Bu yondashuvning O'zbekistonda qanday shaklda ishlashi esa hali mutaxassislar bilan tekshirilishi, huquqiy va texnik chegaralari aniqlanishi, moliyaviy barqarorligi baholanishi va bosqichma-bosqich sinovdan o'tkazilishi kerak. Keyingi vazifa — mavjud tajribalarni ko'r-ko'rona ko'chirish emas, balki ularning muvaffaqiyatlari va xatolaridan saboq olib, O'zbekiston sharoitiga mos, xavfsiz va barqaror modelni mutaxassislar bilan yakunlash. Muallif bu yakuniy modelni allaqachon topdim demaydi; aksincha, o'z tahlilini tajribali mutaxassislar tanqidiga ochib, noto'g'ri taxminlarni tuzatish va yangi bilimlar asosida rivojlantirishga tayyor.

### Mandatory answer boundaries

- Say “similar initiatives and components exist”, not “an identical FINZANJIR exists”, unless a rigorous comparison establishes identity.
- Never claim uniqueness, superiority, complete originality, or direct copying without a documented comparison.
- Label each example by what it actually does; do not conflate fraud-account registries, public-private partnerships, anti-scam operations, AML intelligence sharing, and a proposed end-to-end fraud-chain platform.
- Do not say an initiative failed or closed because of funding without a reliable source documenting that reason.
- Explain that international examples demonstrate possible models, not automatic legal permission for Uzbekistan.
- The wall/fence/pests analogy is an explanatory metaphor, not a technical proof or guarantee.

## Source leads for expert comparison (not a complete legal review)

1. FATF, *Information Sharing to Combat Illicit Finance: Global Overview of Public and Private Sector Partnerships and Data Protection Arrangements* (8 July 2026): https://www.fatf-gafi.org/en/publications/Methodsandtrends/information-sharing-ppp-data-protection-arrangements.html
   - Reports at least 84 public-private partnerships globally and discusses legal basis, governance, safeguards, data protection, and examples including Singapore's Project FRONTIER+.
2. FATF, *Combating End-to-End Illicit Financial Flows Linked to Scam Compounds* (2026): https://www.fatf-gafi.org/content/dam/fatf-gafi/reports/combating-illicit-financial-flows-linked-to-scam-compounds-fatf-2026.pdf
   - Provides comparative material on anti-scam coordination and cross-border mechanisms. Do not use it as the sole source for the current legal scope of FNC-RF or ASAP.
3. UK National Crime Agency, *National Economic Crime Centre / JMLIT+*: https://www.nationalcrimeagency.gov.uk/what-we-do/national-economic-crime-centre
   - Describes JMLIT+ as a public-private partnership with 200+ members and reports outcomes as of 31 December 2024. It also explains the Data Fusion capability and its targeted data-sharing model.
4. UK Government, *Guidance on the information sharing measures in the Economic Crime and Corporate Transparency Act 2023*, updated 3 October 2025: https://www.gov.uk/government/publications/information-sharing-measures-in-the-economic-crime-and-corporate-transparency-act/guidance-on-the-information-sharing-measures-in-the-economic-crime-and-corporate-transparency-act-2023
   - Describes voluntary direct or intermediary information sharing by eligible AML-regulated firms, with conditions and UK GDPR/complaints considerations.
5. FATF, *Private Sector Information Sharing* guidance: https://www.fatf-gafi.org/en/publications/fatfgeneral/documents/guidance-information-sharing.html
   - Explains that information sharing can help, but legal and operational constraints remain and safeguards are required.
6. Central Bank of Uzbekistan, AML/CFT/CPF supervision overview: https://cbu.uz/en/combating-money-laundering/aml-cft/about/
   - Confirms the Central Bank's supervisory role in AML/CFT/CPF for relevant licensed entities. This is not, by itself, a legal basis for FINZANJIR to access or exchange bank/customer data.
7. Central Bank of Uzbekistan FAQ on bank secrecy: https://cbu.uz/en/press_center/question_answer/3808/
   - Explains that client transaction, account, and deposit information is protected as bank secrecy and disclosure follows the law's specified procedures.

## Author's open-audit and continuous-improvement position

- The author explicitly invites expert criticism and independent review; the project must not be presented as complete or error-free.
- Separate completed work, partially completed work, planned work, and unverified assumptions with evidence.
- Record gaps, risks, disagreements, and corrections transparently; do not conceal shortcomings to make the project appear mature.
- Treat expert review as a next development stage, not as a ceremonial approval of a predetermined design.
- Revise or abandon design choices when evidence, law, security, or expert review shows they are unsuitable.

## Approval requirements before runtime activation

- Map every legal assertion to the current official Uzbek legal text and exact article/paragraph, with effective date and reviewer.
- Obtain qualified Uzbek legal/compliance review; separately document Central Bank and participating-bank requirements and approvals.
- Build a data-flow inventory covering data fields, purpose, source, controller/processor roles, legal basis, recipients, access, location, retention, deletion, audit, incident response, and cross-border transfer.
- Compare international examples using primary sources and distinguish legal frameworks from technical capabilities.
- Record which features are documented concepts, prototypes, planned work, or actually deployed.
- Obtain user approval and complete multilingual native-speaker review before marking either answer canonical.


## Source verification notes added 15 November 2026

- France FNC-RF: Banque de France / ACPR materials and the 7 May 2026 launch notice should be treated as the primary operational references. The current ACPR FAQ (version 7 October 2026) is particularly important for the exact data fields, investigation workflow, and the fact that an initial report is not itself a final fraud qualification. The French official order of 24 April 2026 defines technical operating modalities under the amended Monetary and Financial Code. These sources must be checked in full before converting this comparison into a public claim.
- South Korea ASAP: Financial Services Commission releases dated 29 October 2025, 15 January 2026, and 4 August 2026 establish the launch, legislative basis, and later expansion of the sharing scope. The August 2026 release is the current reference for participation by financial companies, telecom providers, and investigative authorities.
- Singapore FRONTIER+: use the FATF 2026 scam-compounds report for the cross-border platform and specific operation results. Distinguish FRONTIER+ from domestic anti-scam centres and from the broader FATF public-private partnership count.
- JMLIT+: use the UK National Crime Agency's current NECC/JMLIT+ page for membership, Data Fusion description, and outcomes as of 31 December 2024. Do not present those outcomes as independently causal impact without qualification.
- The FATF figure of at least 84 PPPs and 52 surveyed jurisdictions is confirmed by the 8 July 2026 FATF overview. Describe these as FATF-reported survey findings, not a census of every global information-sharing arrangement.
