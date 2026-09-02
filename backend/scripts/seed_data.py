"""Static seed content: categories, the South Lebanon location tree, businesses.

Kept as data rather than inline code so an administrator can later extend the
same structures, and so the seed script itself stays readable.
"""

from __future__ import annotations

from typing import TypedDict


class CategorySeed(TypedDict):
    name_ar: str
    slug: str
    icon: str
    sort_order: int


class LocationSeed(TypedDict, total=False):
    name_ar: str
    slug: str
    children: list[LocationSeed]


class ItemSeed(TypedDict, total=False):
    title: str
    description: str
    price: str
    is_available: bool


class BusinessSeed(TypedDict, total=False):
    name: str
    owner_phone: str
    category: str
    location: str
    status: str
    short_description: str
    description: str
    phone: str
    whatsapp: str
    address_text: str
    rejection_reason: str
    slug: str
    socials: dict[str, str]
    items: list[ItemSeed]


CATEGORIES: list[CategorySeed] = [
    {"name_ar": "مطاعم ومأكولات", "slug": "restaurants", "icon": "utensils", "sort_order": 1},
    {"name_ar": "حلويات", "slug": "sweets", "icon": "cake", "sort_order": 2},
    {"name_ar": "مواد غذائية", "slug": "groceries", "icon": "shopping-basket", "sort_order": 3},
    {"name_ar": "ألبسة", "slug": "clothing", "icon": "shirt", "sort_order": 4},
    {"name_ar": "صحة وجمال", "slug": "beauty", "icon": "sparkles", "sort_order": 5},
    {"name_ar": "خدمات منزلية", "slug": "home-services", "icon": "home", "sort_order": 6},
    {"name_ar": "صيانة", "slug": "maintenance", "icon": "wrench", "sort_order": 7},
    {"name_ar": "سيارات", "slug": "automotive", "icon": "car", "sort_order": 8},
    {"name_ar": "تعليم", "slug": "education", "icon": "graduation-cap", "sort_order": 9},
    {"name_ar": "زراعة", "slug": "agriculture", "icon": "sprout", "sort_order": 10},
    {"name_ar": "حرف وصناعات", "slug": "crafts", "icon": "hammer", "sort_order": 11},
    {"name_ar": "تقنية", "slug": "technology", "icon": "laptop", "sort_order": 12},
    {"name_ar": "تصوير وإعلام", "slug": "media", "icon": "camera", "sort_order": 13},
    {"name_ar": "منتجات منزلية", "slug": "homemade", "icon": "gift", "sort_order": 14},
    {"name_ar": "أخرى", "slug": "other", "icon": "grid", "sort_order": 99},
]

# governorate -> districts -> towns
LOCATIONS: list[LocationSeed] = [
    {
        "name_ar": "الجنوب",
        "slug": "south-governorate",
        "children": [
            {
                "name_ar": "صور",
                "slug": "tyre",
                "children": [
                    {"name_ar": "الصرفند", "slug": "sarafand"},
                    {"name_ar": "قانا", "slug": "qana"},
                    {"name_ar": "معركة", "slug": "maaroub"},
                ],
            },
            {
                "name_ar": "صيدا",
                "slug": "saida",
                "children": [
                    {"name_ar": "الغازية", "slug": "ghazieh"},
                    {"name_ar": "حارة صيدا", "slug": "haret-saida"},
                ],
            },
            {
                "name_ar": "جزين",
                "slug": "jezzine",
                "children": [{"name_ar": "كفرحونة", "slug": "kfarhouna"}],
            },
            {
                "name_ar": "بنت جبيل",
                "slug": "bint-jbeil",
                "children": [
                    {"name_ar": "عيترون", "slug": "aitaroun"},
                    {"name_ar": "تبنين", "slug": "tebnine"},
                ],
            },
        ],
    },
    {
        "name_ar": "النبطية",
        "slug": "nabatieh-governorate",
        "children": [
            {
                "name_ar": "النبطية",
                "slug": "nabatieh",
                "children": [
                    {"name_ar": "كفررمان", "slug": "kfarremen"},
                    {"name_ar": "زبدين", "slug": "zebdine"},
                ],
            },
            {
                "name_ar": "مرجعيون",
                "slug": "marjeyoun",
                "children": [{"name_ar": "القليعة", "slug": "qlayaa"}],
            },
            {
                "name_ar": "حاصبيا",
                "slug": "hasbaya",
                "children": [{"name_ar": "شبعا", "slug": "shebaa"}],
            },
        ],
    },
]

# status is applied by the seed script; owners are generated from owner_phone.
BUSINESSES: list[BusinessSeed] = [
    {
        "name": "فرن أبو خليل",
        "owner_phone": "03111111",
        "category": "restaurants",
        "location": "tyre",
        "status": "APPROVED",
        "short_description": "مناقيش وفطائر على الصاج كل صباح، من قلب صور.",
        "description": (
            "فرن عائلي في صور نخبز فيه الخبز والمعجنات على الحطب منذ أكثر من عشرين سنة. "
            "نستخدم زعتراً بلدياً من مزارع الجنوب وجبنة طازجة يومياً، ونجهّز طلبات "
            "المناسبات والعزائم حسب الطلب."
        ),
        "phone": "07740111",
        "whatsapp": "03111111",
        "address_text": "شارع البلدية، مقابل الحديقة العامة، صور",
        "socials": {"INSTAGRAM": "https://instagram.com/manakish.aldayaa"},
        "items": [
            {"title": "منقوشة زعتر", "price": "1.50", "description": "زعتر بلدي مع زيت زيتون من الجنوب"},
            {"title": "منقوشة جبنة", "price": "3.00", "description": "جبنة عكاوي طازجة"},
            {"title": "لبنة وخضار", "price": "2.50", "description": "لبنة منزلية مع بندورة ونعناع وزيتون"},
            {"title": "صفيحة بلحم", "price": "2.00"},
        ],
    },
    {
        "name": "حلويات أبو علي",
        "owner_phone": "03222222",
        "category": "sweets",
        "location": "nabatieh",
        "status": "APPROVED",
        "short_description": "كنافة وبقلاوة ومعمول على أصولها في النبطية.",
        "description": "محل حلويات عائلي في النبطية، نحضّر الكنافة الطازجة يومياً ونستقبل طلبات الأعراس والمناسبات.",
        "phone": "07650222",
        "whatsapp": "03222222",
        "address_text": "شارع الشهداء، النبطية التحتا",
        "socials": {"FACEBOOK": "https://facebook.com/halawiyat.abuali", "INSTAGRAM": "https://instagram.com/abuali.sweets"},
        "items": [
            {"title": "كنافة بالجبنة", "price": "6.00", "description": "صحن وسط"},
            {"title": "بقلاوة مشكّلة", "price": "12.00", "description": "علبة كيلو"},
            {"title": "معمول بالتمر", "price": "8.00"},
        ],
    },
    {
        "name": "سوبرماركت الجنوب",
        "owner_phone": "03333333",
        "category": "groceries",
        "location": "saida",
        "status": "APPROVED",
        "short_description": "كل حاجيات البيت بأسعار مناسبة، مع توصيل داخل صيدا.",
        "phone": "07720333",
        "whatsapp": "03333333",
        "address_text": "شارع رياض الصلح، صيدا",
        "items": [
            {"title": "توصيل داخل صيدا", "price": "2.00", "description": "خلال ساعتين من الطلب"},
            {"title": "سلة المونة الشهرية", "price": "45.00"},
        ],
    },
    {
        "name": "صالون ليان",
        "owner_phone": "03444444",
        "category": "beauty",
        "location": "tyre",
        "status": "APPROVED",
        "short_description": "قصّ وتصفيف وعناية بالبشرة، بمواعيد مسبقة.",
        "whatsapp": "03444444",
        "address_text": "شارع عبد الحسين، صور",
        "socials": {"INSTAGRAM": "https://instagram.com/salon.layan"},
        "items": [
            {"title": "قص وتصفيف", "price": "15.00"},
            {"title": "صبغة كاملة", "price": "40.00"},
            {"title": "عناية بالبشرة", "price": "25.00", "is_available": False},
        ],
    },
    {
        "name": "نجارة الأرز",
        "owner_phone": "03555555",
        "category": "crafts",
        "location": "jezzine",
        "status": "APPROVED",
        "short_description": "أثاث خشبي مصنوع يدوياً وتفصيل حسب الطلب.",
        "phone": "07780555",
        "whatsapp": "03555555",
        "address_text": "الطريق العام، جزين",
        "items": [
            {"title": "طاولة طعام خشب سنديان", "price": "350.00"},
            {"title": "مكتبة حائط", "price": "180.00"},
            {"title": "تفصيل مطابخ", "description": "السعر حسب القياس والتصميم"},
        ],
    },
    {
        "name": "مؤسسة قانا للكهرباء",
        "owner_phone": "03666666",
        "category": "maintenance",
        "location": "qana",
        "status": "APPROVED",
        "short_description": "تمديدات كهربائية وصيانة طوارئ على مدار اليوم.",
        "phone": "07730666",
        "whatsapp": "03666666",
        "items": [
            {"title": "كشف وصيانة", "price": "20.00"},
            {"title": "تركيب نظام طاقة شمسية", "description": "زيارة معاينة مجانية"},
        ],
    },
    {
        "name": "مزرعة زيتون الجنوب",
        "owner_phone": "03777777",
        "category": "agriculture",
        "location": "bint-jbeil",
        "status": "APPROVED",
        "short_description": "زيت زيتون بلدي وزعتر ومونة من أرضنا في بنت جبيل.",
        "whatsapp": "03777777",
        "socials": {"WHATSAPP": "https://wa.me/9613777777"},
        "items": [
            {"title": "تنكة زيت زيتون ١٦ ليتر", "price": "160.00"},
            {"title": "زعتر بلدي كيلو", "price": "9.00"},
            {"title": "زيتون مكبوس", "price": "7.00"},
        ],
    },
    {
        "name": "مركز الجنوب للمعلوماتية",
        "owner_phone": "03888888",
        "category": "technology",
        "location": "nabatieh",
        "status": "APPROVED",
        "short_description": "صيانة حواسيب وتركيب شبكات وكاميرات مراقبة.",
        "phone": "07660888",
        "whatsapp": "03888888",
        "socials": {"WEBSITE": "https://south-it.example.com"},
        "items": [
            {"title": "صيانة كمبيوتر", "price": "25.00"},
            {"title": "تركيب كاميرات مراقبة", "price": "300.00"},
        ],
    },
    {
        "name": "ألبسة الأناقة",
        "owner_phone": "03999999",
        "category": "clothing",
        "location": "saida",
        "status": "APPROVED",
        "short_description": "ألبسة رجالية ونسائية بأسعار الجملة.",
        "whatsapp": "03999999",
        "items": [{"title": "قميص رجالي", "price": "18.00"}, {"title": "فستان سهرة", "price": "75.00"}],
    },
    {
        "name": "مطبخ أم حسن المنزلي",
        "owner_phone": "03101010",
        "category": "homemade",
        "location": "kfarremen",
        "status": "APPROVED",
        "short_description": "أطعمة منزلية ومونة بلدية بطلب مسبق.",
        "whatsapp": "03101010",
        "items": [
            {"title": "كبة نية", "price": "12.00"},
            {"title": "ورق عنب", "price": "15.00"},
            {"title": "مربى التين", "price": "6.00"},
        ],
    },
    {
        "name": "مدرسة الجنوب للدروس الخصوصية",
        "owner_phone": "03111212",
        "category": "education",
        "location": "tebnine",
        "status": "APPROVED",
        "short_description": "دروس تقوية بالرياضيات والفيزياء لطلاب الثانوي.",
        "phone": "07750121",
        "whatsapp": "03111212",
        "items": [
            {"title": "حصة فردية", "price": "10.00"},
            {"title": "اشتراك شهري - مجموعة", "price": "60.00"},
        ],
    },
    {
        "name": "كراج المرجعيوني",
        "owner_phone": "03121212",
        "category": "automotive",
        "location": "marjeyoun",
        "status": "PENDING_REVIEW",
        "short_description": "ميكانيك عام وتصليح محركات وكهرباء سيارات.",
        "phone": "07770121",
        "whatsapp": "03121212",
        "items": [{"title": "تغيير زيت", "price": "25.00"}, {"title": "فحص شامل", "price": "15.00"}],
    },
    {
        "name": "استوديو ضوء الجنوب",
        "owner_phone": "03131313",
        "category": "media",
        "location": "hasbaya",
        "status": "PENDING_REVIEW",
        "short_description": "تصوير أعراس ومناسبات ومنتجات.",
        "whatsapp": "03131313",
        "socials": {"INSTAGRAM": "https://instagram.com/south.light.studio"},
        "items": [{"title": "تصوير عرس", "price": "600.00"}, {"title": "جلسة تصوير منتجات", "price": "120.00"}],
    },
    {
        "name": "خدمات التنظيف السريعة",
        "owner_phone": "03141414",
        "category": "home-services",
        "location": "ghazieh",
        "status": "REJECTED",
        "rejection_reason": "الرجاء إضافة وصف أوضح للخدمات ورقم تواصل صحيح، وصورة شعار بجودة أفضل.",
        "short_description": "تنظيف منازل ومكاتب.",
        "whatsapp": "03141414",
        "items": [{"title": "تنظيف شقة", "price": "40.00"}],
    },
    {
        "name": "بقالة شبعا",
        "owner_phone": "03151515",
        "category": "groceries",
        "location": "shebaa",
        "status": "DRAFT",
        "short_description": "بقالة صغيرة تخدم أهالي شبعا.",
        "whatsapp": "03151515",
        "items": [],
    },
    {
        "name": "حداد الصرفند",
        "owner_phone": "03161616",
        "category": "crafts",
        "location": "sarafand",
        "status": "SUSPENDED",
        "short_description": "أعمال حدادة وأبواب ونوافذ حديد.",
        "phone": "07710161",
        "whatsapp": "03161616",
        "items": [{"title": "باب حديد", "price": "250.00"}],
    },
]
