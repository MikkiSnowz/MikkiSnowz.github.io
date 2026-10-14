// All site content lives here, so updating the portfolio means editing this file only.

export const profile = {
  name: 'Sahatpat Anankatham',
  nickname: 'Mikki',
  location: 'Melbourne, VIC',
  email: 'mickynextgen@gmail.com',
  github: 'https://github.com/MikkiSnowz',
  githubHandle: 'MikkiSnowz',
  roles: [
    'Software Engineering Student',
    'Backend Developer',
    'Data Explorer',
    'Game Builder',
  ],
  tagline:
    'Second-year Computing and Software Systems student at the University of Melbourne, looking for a software engineering internship.',
  summary: [
    "I'm a second-year Computing and Software Systems student at the University of Melbourne (WAM 78+). I work mainly in Python, Java, C and SQL, and I've built features that are live on a student club website.",
    'I enjoy building things that people actually use, from a point-of-sale app that keeps every cent exact, to a check-in system running on Cloudflare for a university club.',
  ],
};

export const stats = [
  { value: 94.3, decimals: 2, suffix: '', label: 'ATAR' },
  { value: 78, decimals: 0, suffix: '+', label: 'University WAM' },
  { value: 40, decimals: 0, suffix: '+', label: 'Software Dev study score' },
  { value: 3, decimals: 0, suffix: '', label: 'Spoken languages' },
];

export type Project = {
  title: string;
  tech: string[];
  link?: string;
  icon: string;
  points: string[];
};

export const projects: Project[] = [
  {
    title: 'Order Management System',
    tech: ['Python', 'Tkinter', 'SQLite', 'pytest'],
    link: 'https://github.com/MikkiSnowz/Thai_restaurant_ordering_system',
    icon: '🧾',
    points: [
      'Desktop point-of-sale app for dine-in and takeaway orders, with running totals and a flow for sending an order to the kitchen, completing it or voiding it.',
      'Orders save to SQLite as they’re entered, and money is stored as integer cents so totals stay exact and nothing is lost if the app closes.',
      'Daily report showing revenue and completed and voided orders, plus customer search and sortable columns to see which items sell best.',
      'Staff logins use hashed passwords and lock out after repeated failed attempts. Modular code covered by a pytest suite.',
    ],
  },
  {
    title: 'Shadow Aliens: 2D Arcade Game',
    tech: ['Java', 'Bagel', 'Maven', 'Git'],
    icon: '👾',
    points: [
      '2D arcade game with player and enemy movement, collision detection, waves of enemies and four power-ups (shield, life, engine, cooldown).',
      'Reworked around an abstract GameObject class so Player, Enemy, Projectile and PowerUp share behaviour through inheritance, cutting duplicated code.',
      'Game loop built around explicit states (start, pause, HUD, end screens) with variable game speed using frame-time accumulation.',
    ],
  },
  {
    title: 'Travel Behaviour Clustering Analysis',
    tech: ['Python', 'pandas', 'scikit-learn'],
    icon: '📊',
    points: [
      'Cleaned transport datasets by filling in missing values and turning income groups into numeric features.',
      'Built features from raw journey data to describe how each person travels.',
      'Ran K-Means and hierarchical clustering to find distinct groups of travellers.',
    ],
  },
];

export const leadership = [
  {
    role: 'IT Officer',
    org: 'Melbourne Information Security Club (UMISC)',
    tech: ['Astro', 'Cloudflare Pages', 'Drizzle ORM', 'Cloudflare D1', 'Turnstile'],
    points: [
      'Built the public event check-in system for the club website with a small student developer team, agreeing requirements with committee members along the way.',
      'Wrote the database schema and backend using Drizzle ORM and Cloudflare D1. Added Cloudflare Turnstile for bot protection, duplicate-entry checks, and scheduled cron jobs that clear out old data automatically.',
    ],
  },
  {
    role: 'Sponsorship Director',
    org: 'Thai Student Association, University of Melbourne',
    tech: ['Partnerships', 'Negotiation', 'Event branding'],
    points: [
      'Found and signed corporate sponsors to help fund club events.',
      'Looked after sponsors from first outreach through negotiation, and coordinated branding and event visibility so the partnerships continued.',
    ],
  },
];

export const education = [
  {
    school: 'University of Melbourne',
    degree: 'Bachelor of Science (Computing and Software Systems)',
    period: '2025 – Present',
    points: ['WAM 78+'],
    subjects: [
      'Foundations of Computing (Python)',
      'Foundations of Algorithms (C)',
      'Algorithms and Data Structures (C)',
      'Object Oriented Software Development (Java, Git, Maven)',
      'Database Systems (SQL, MySQL, SQLite)',
      'Elements of Data Processing (pandas, scikit-learn)',
    ],
  },
  {
    school: 'Camberwell High School',
    degree: 'Victorian Certificate of Education',
    period: '2019 – 2024',
    points: [
      'ATAR 94.30',
      'Dux of Applied Computing: Software Development (study score 40+)',
      'VCE Academic Excellence Award',
    ],
    subjects: [],
  },
];

export const skills = [
  {
    group: 'Languages',
    items: ['Python', 'Java', 'C', 'TypeScript', 'JavaScript', 'SQL', 'HTML/CSS', 'Swift'],
  },
  {
    group: 'Libraries & Frameworks',
    items: ['pandas', 'NumPy', 'scikit-learn', 'Matplotlib', 'Tkinter', 'Astro', 'Node.js', 'Drizzle ORM'],
  },
  {
    group: 'Tools & Platforms',
    items: ['Git', 'Maven', 'Docker', 'pytest', 'SQLite', 'MySQL', 'Cloudflare Pages', 'Cloudflare D1'],
  },
  {
    group: 'Spoken Languages',
    items: ['Thai', 'English', 'Japanese'],
  },
];
