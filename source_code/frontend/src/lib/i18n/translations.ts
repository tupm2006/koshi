/**
 * Translation dictionary.
 *
 * `en` is the source of truth: `Translations` is derived from it, so adding a
 * key without a Vietnamese counterpart is a compile error rather than a string
 * that silently falls back at runtime.
 */

export const LOCALES = ['en', 'vi'] as const;
export type Locale = (typeof LOCALES)[number];

export const LOCALE_LABELS: Record<Locale, string> = {
  en: 'English',
  vi: 'Tiếng Việt',
};

const en = {
  // --- shared / nav ---
  'nav.features': 'Features',
  'nav.how': 'How it works',
  'nav.pricing': 'Pricing',
  'nav.faq': 'FAQ',
  'nav.signIn': 'Sign in',
  'nav.getStarted': 'Get started',
  'nav.language': 'Language',

  // --- hero ---
  'hero.eyebrow': 'Project management engine',
  'hero.title': 'Track work at the speed you think.',
  'hero.subtitle':
    'A local-first, keyboard-driven tracker for small software teams. Four states, real dependency maths, and AI that returns structured data instead of paragraphs.',
  'hero.ctaPrimary': 'Start free',
  'hero.ctaSecondary': 'See how it works',
  'hero.note': 'No credit card required.',

  // --- product preview ---
  'preview.caption': 'The board, in the two views you actually use.',
  'preview.todo': 'To Do',
  'preview.inProgress': 'In Progress',
  'preview.blocked': 'Blocked',
  'preview.done': 'Done',
  'preview.task1': 'Design the schema',
  'preview.task2': 'Build the sync layer',
  'preview.task3': 'Waiting on API keys',
  'preview.task4': 'Ship the dashboard',

  // --- features ---
  'features.eyebrow': 'Why Koshi',
  'features.title': 'Built for people who ship.',
  'features.subtitle': 'Everything here exists because a slow tracker was getting in the way.',
  'features.keyboard.title': 'Keyboard-first',
  'features.keyboard.body':
    'Navigate, create and re-prioritise without touching the mouse. Vim-style movement in both table and board views.',
  'features.graph.title': 'Dependency-aware',
  'features.graph.body':
    'Topological ordering and a weighted critical path, recomputed live. See what is actually blocking the release.',
  'features.ai.title': 'Structured AI',
  'features.ai.body':
    'Weekly summaries, meeting minutes and assignment suggestions returned as validated data, never as a wall of chat text.',
  'features.offline.title': 'Local-first',
  'features.offline.body':
    'Every change lands in your browser first, so the network never blocks a keystroke. Personal projects keep working offline.',
  'features.roles.title': 'Per-project roles',
  'features.roles.body':
    'Be a manager on one project and a contributor on another. No global permissions to untangle.',
  'features.speed.title': 'No spinners',
  'features.speed.body':
    'Zero animation budget and no optimistic-update flicker. State changes are committed before the next frame.',

  // --- how it works ---
  'how.eyebrow': 'How it works',
  'how.title': 'Three steps to a working board.',
  'how.step1.title': 'Create a project',
  'how.step1.body': 'Sign up and create a project. You become its Project Manager automatically.',
  'how.step2.title': 'Invite your team',
  'how.step2.body': 'Add teammates by email and set each person a role in that project.',
  'how.step3.title': 'Work at speed',
  'how.step3.body': 'Press n to create, Space to advance a status, v to inspect the dependency graph.',
  'how.videoTitle': 'Product tour',
  'how.videoBody': 'A two-minute walkthrough of the board, the graph view and the AI workflows.',
  'how.videoMissing': 'Demo video not configured yet.',

  // --- use cases ---
  'cases.eyebrow': 'Who it is for',
  'cases.title': 'Small teams with real dependencies.',
  'cases.a.title': 'Product teams',
  'cases.a.body': 'Plan a sprint, see the critical path, and know which task actually unblocks the rest.',
  'cases.b.title': 'Agencies',
  'cases.b.body': 'Separate projects, separate rosters, separate roles — with one login.',
  'cases.c.title': 'Solo builders',
  'cases.c.body': 'A personal project keeps working offline, on a plane or a bad connection.',

  // --- pricing ---
  'pricing.eyebrow': 'Pricing',
  'pricing.title': 'Simple plans.',
  'pricing.subtitle': 'Start free. Upgrade when your team grows.',
  'pricing.perMonth': '/month',
  'pricing.free.name': 'Free',
  'pricing.free.price': '$0',
  'pricing.free.body': 'For one person and one project.',
  'pricing.free.f1': '1 project',
  'pricing.free.f2': 'Full keyboard and graph engine',
  'pricing.free.f3': 'Offline editing',
  'pricing.team.name': 'Team',
  'pricing.team.price': '$8',
  'pricing.team.body': 'For a team that ships together.',
  'pricing.team.f1': 'Unlimited projects',
  'pricing.team.f2': 'Per-project roles',
  'pricing.team.f3': 'AI summaries and minutes',
  'pricing.business.name': 'Business',
  'pricing.business.price': '$16',
  'pricing.business.body': 'For several teams at once.',
  'pricing.business.f1': 'Everything in Team',
  'pricing.business.f2': 'Priority support',
  'pricing.business.f3': 'Self-hosting guide',
  'pricing.popular': 'Most popular',
  'pricing.cta': 'Get started',

  // --- faq ---
  'faq.title': 'Questions',
  'faq.q1': 'Does it work offline?',
  'faq.a1':
    'Yes, for personal projects. Changes are saved in your browser first and synced when you reconnect. Projects with more than one member become read-only while offline, so two people cannot silently overwrite each other.',
  'faq.q2': 'How do permissions work?',
  'faq.a2':
    'Roles are set per project, not per account. You can manage one project and contribute to another with the same login.',
  'faq.q3': 'What does the AI actually do?',
  'faq.a3':
    'It produces weekly progress summaries, turns raw meeting notes into action items, and suggests who should take a task based on skills and current workload. Output is schema-validated, so it never returns free-form text where structured data is expected.',
  'faq.q4': 'Can I export my data?',
  'faq.a4': 'Yes. The whole board exports to JSON and imports back, with no proprietary format in between.',

  // --- final CTA + footer ---
  'cta.title': 'Ready to try it?',
  'cta.body': 'Create an account and have a board running in under a minute.',
  'cta.button': 'Create your account',
  'footer.tagline': 'A high-velocity project management engine.',
  'footer.product': 'Product',
  'footer.company': 'Company',
  'footer.rights': 'MIT licensed.',

  // --- auth panel ---
  'auth.signInTitle': 'Sign in',
  'auth.signUpTitle': 'Create your account',
  'auth.signInSub': 'Welcome back.',
  'auth.signUpSub': 'Free, and takes a minute.',
  'auth.fullName': 'Full name',
  'auth.skills': 'Skills',
  'auth.optional': '(optional)',
  'auth.email': 'Email address',
  'auth.password': 'Password',
  'auth.submitSignIn': 'Sign in',
  'auth.submitSignUp': 'Create account',
  'auth.working': 'Working…',
  'auth.toSignUp': "Don't have an account? Create one",
  'auth.toSignIn': 'Already have an account? Sign in',
  'auth.noRoleNote':
    'No role to pick. Create a project and you are its Project Manager; roles are set per project.',
  'auth.demo': 'Demo',
  'auth.close': 'Close',
  'auth.failed': 'Authentication failed',

  // --- board / offline ---
  'board.offlineShared': 'Offline — read-only',
  'board.offlineSharedHint':
    'This project has other members, so editing is paused until you reconnect. That prevents two people overwriting each other.',
  'board.offlinePersonal': 'Offline — editing locally',
  'board.noProject': 'No project selected',
} as const;

export type TranslationKey = keyof typeof en;
export type Translations = Record<TranslationKey, string>;

const vi: Translations = {
  'nav.features': 'Tính năng',
  'nav.how': 'Cách hoạt động',
  'nav.pricing': 'Bảng giá',
  'nav.faq': 'Hỏi đáp',
  'nav.signIn': 'Đăng nhập',
  'nav.getStarted': 'Bắt đầu',
  'nav.language': 'Ngôn ngữ',

  'hero.eyebrow': 'Nền tảng quản lý dự án',
  'hero.title': 'Quản lý công việc nhanh như bạn nghĩ.',
  'hero.subtitle':
    'Công cụ theo dõi công việc ưu tiên bàn phím, chạy cục bộ, dành cho đội phát triển nhỏ. Bốn trạng thái, tính toán phụ thuộc thực sự, và AI trả về dữ liệu có cấu trúc thay vì đoạn văn dài.',
  'hero.ctaPrimary': 'Dùng thử miễn phí',
  'hero.ctaSecondary': 'Xem cách hoạt động',
  'hero.note': 'Không cần thẻ tín dụng.',

  'preview.caption': 'Bảng công việc, ở hai chế độ bạn thực sự dùng.',
  'preview.todo': 'Cần làm',
  'preview.inProgress': 'Đang làm',
  'preview.blocked': 'Bị chặn',
  'preview.done': 'Hoàn thành',
  'preview.task1': 'Thiết kế lược đồ dữ liệu',
  'preview.task2': 'Xây dựng lớp đồng bộ',
  'preview.task3': 'Đang chờ khoá API',
  'preview.task4': 'Hoàn thiện bảng điều khiển',

  'features.eyebrow': 'Vì sao chọn Koshi',
  'features.title': 'Dành cho người thực sự làm ra sản phẩm.',
  'features.subtitle': 'Mọi thứ ở đây ra đời vì một công cụ chậm chạp đã từng cản đường.',
  'features.keyboard.title': 'Ưu tiên bàn phím',
  'features.keyboard.body':
    'Di chuyển, tạo mới và đổi độ ưu tiên mà không cần chuột. Điều hướng kiểu Vim ở cả chế độ bảng và Kanban.',
  'features.graph.title': 'Hiểu quan hệ phụ thuộc',
  'features.graph.body':
    'Sắp xếp tô-pô và đường găng có trọng số, tính lại theo thời gian thực. Thấy ngay việc nào đang chặn cả bản phát hành.',
  'features.ai.title': 'AI có cấu trúc',
  'features.ai.body':
    'Báo cáo tuần, biên bản họp và gợi ý phân công được trả về dưới dạng dữ liệu đã kiểm tra, không phải một đoạn chat dài.',
  'features.offline.title': 'Chạy cục bộ trước',
  'features.offline.body':
    'Mọi thay đổi được lưu trong trình duyệt trước, nên mạng không bao giờ làm nghẽn thao tác. Dự án cá nhân vẫn dùng được khi mất mạng.',
  'features.roles.title': 'Vai trò theo từng dự án',
  'features.roles.body':
    'Làm quản lý ở dự án này và thành viên ở dự án khác. Không có phân quyền toàn cục rối rắm.',
  'features.speed.title': 'Không vòng xoay chờ',
  'features.speed.body':
    'Không hiệu ứng động, không nhấp nháy khi cập nhật. Trạng thái được ghi xong trước khung hình kế tiếp.',

  'how.eyebrow': 'Cách hoạt động',
  'how.title': 'Ba bước để có bảng công việc.',
  'how.step1.title': 'Tạo dự án',
  'how.step1.body': 'Đăng ký và tạo một dự án. Bạn tự động trở thành Quản lý dự án của nó.',
  'how.step2.title': 'Mời đồng đội',
  'how.step2.body': 'Thêm thành viên bằng email và đặt vai trò cho từng người trong dự án đó.',
  'how.step3.title': 'Làm việc thật nhanh',
  'how.step3.body': 'Nhấn n để tạo, Space để chuyển trạng thái, v để xem đồ thị phụ thuộc.',
  'how.videoTitle': 'Video giới thiệu',
  'how.videoBody': 'Hướng dẫn hai phút về bảng công việc, đồ thị phụ thuộc và các luồng AI.',
  'how.videoMissing': 'Chưa cấu hình video giới thiệu.',

  'cases.eyebrow': 'Dành cho ai',
  'cases.title': 'Đội nhỏ với những phụ thuộc có thật.',
  'cases.a.title': 'Đội sản phẩm',
  'cases.a.body': 'Lập kế hoạch sprint, xem đường găng, biết việc nào thực sự mở khoá cho phần còn lại.',
  'cases.b.title': 'Công ty dịch vụ',
  'cases.b.body': 'Nhiều dự án, nhiều đội, nhiều vai trò khác nhau — chỉ với một tài khoản.',
  'cases.c.title': 'Người làm một mình',
  'cases.c.body': 'Dự án cá nhân vẫn chạy khi mất mạng, trên máy bay hay lúc kết nối chập chờn.',

  'pricing.eyebrow': 'Bảng giá',
  'pricing.title': 'Gói cước đơn giản.',
  'pricing.subtitle': 'Bắt đầu miễn phí. Nâng cấp khi đội bạn lớn hơn.',
  'pricing.perMonth': '/tháng',
  'pricing.free.name': 'Miễn phí',
  'pricing.free.price': '0đ',
  'pricing.free.body': 'Cho một người và một dự án.',
  'pricing.free.f1': '1 dự án',
  'pricing.free.f2': 'Đầy đủ bàn phím và đồ thị phụ thuộc',
  'pricing.free.f3': 'Chỉnh sửa khi ngoại tuyến',
  'pricing.team.name': 'Nhóm',
  'pricing.team.price': '190.000đ',
  'pricing.team.body': 'Cho đội cùng nhau ra sản phẩm.',
  'pricing.team.f1': 'Không giới hạn dự án',
  'pricing.team.f2': 'Vai trò theo từng dự án',
  'pricing.team.f3': 'Báo cáo và biên bản bằng AI',
  'pricing.business.name': 'Doanh nghiệp',
  'pricing.business.price': '390.000đ',
  'pricing.business.body': 'Cho nhiều đội cùng lúc.',
  'pricing.business.f1': 'Toàn bộ gói Nhóm',
  'pricing.business.f2': 'Hỗ trợ ưu tiên',
  'pricing.business.f3': 'Hướng dẫn tự triển khai',
  'pricing.popular': 'Phổ biến nhất',
  'pricing.cta': 'Bắt đầu',

  'faq.title': 'Câu hỏi thường gặp',
  'faq.q1': 'Có dùng được khi mất mạng không?',
  'faq.a1':
    'Có, với dự án cá nhân. Thay đổi được lưu trong trình duyệt trước rồi đồng bộ khi có mạng lại. Dự án có nhiều hơn một thành viên sẽ chuyển sang chỉ đọc khi ngoại tuyến, để hai người không âm thầm ghi đè lên nhau.',
  'faq.q2': 'Phân quyền hoạt động thế nào?',
  'faq.a2':
    'Vai trò được đặt theo từng dự án, không theo tài khoản. Bạn có thể quản lý dự án này và tham gia dự án khác với cùng một tài khoản.',
  'faq.q3': 'AI thực sự làm được gì?',
  'faq.a3':
    'Nó tạo báo cáo tiến độ tuần, chuyển ghi chép cuộc họp thô thành danh sách việc cần làm, và gợi ý người phù hợp nhận việc dựa trên kỹ năng và khối lượng hiện tại. Kết quả luôn được kiểm tra theo lược đồ, nên không bao giờ trả về văn bản tự do ở chỗ cần dữ liệu có cấu trúc.',
  'faq.q4': 'Tôi có xuất được dữ liệu không?',
  'faq.a4': 'Có. Toàn bộ bảng công việc xuất ra JSON và nhập lại được, không có định dạng độc quyền nào ở giữa.',

  'cta.title': 'Sẵn sàng dùng thử?',
  'cta.body': 'Tạo tài khoản và có ngay bảng công việc trong chưa đầy một phút.',
  'cta.button': 'Tạo tài khoản',
  'footer.tagline': 'Nền tảng quản lý dự án tốc độ cao.',
  'footer.product': 'Sản phẩm',
  'footer.company': 'Công ty',
  'footer.rights': 'Giấy phép MIT.',

  'auth.signInTitle': 'Đăng nhập',
  'auth.signUpTitle': 'Tạo tài khoản',
  'auth.signInSub': 'Chào mừng trở lại.',
  'auth.signUpSub': 'Miễn phí, chỉ mất một phút.',
  'auth.fullName': 'Họ và tên',
  'auth.skills': 'Kỹ năng',
  'auth.optional': '(không bắt buộc)',
  'auth.email': 'Địa chỉ email',
  'auth.password': 'Mật khẩu',
  'auth.submitSignIn': 'Đăng nhập',
  'auth.submitSignUp': 'Tạo tài khoản',
  'auth.working': 'Đang xử lý…',
  'auth.toSignUp': 'Chưa có tài khoản? Tạo ngay',
  'auth.toSignIn': 'Đã có tài khoản? Đăng nhập',
  'auth.noRoleNote':
    'Không cần chọn vai trò. Tạo một dự án và bạn là Quản lý dự án của nó; vai trò được đặt theo từng dự án.',
  'auth.demo': 'Dùng thử',
  'auth.close': 'Đóng',
  'auth.failed': 'Xác thực thất bại',

  'board.offlineShared': 'Ngoại tuyến — chỉ đọc',
  'board.offlineSharedHint':
    'Dự án này có thành viên khác, nên việc chỉnh sửa tạm dừng cho tới khi có mạng lại. Điều đó tránh việc hai người ghi đè lên nhau.',
  'board.offlinePersonal': 'Ngoại tuyến — đang lưu cục bộ',
  'board.noProject': 'Chưa chọn dự án',
};

export const MESSAGES: Record<Locale, Translations> = { en, vi };
