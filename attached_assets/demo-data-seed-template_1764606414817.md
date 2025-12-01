# Demo Data Seed Template

Use this template to create comprehensive test data for any project.

---

## Seed Script Template (TypeScript/Node.js)

```typescript
// seed.ts - Comprehensive Demo Data Seed Script

import { db } from './db';
import { users, projects, /* add your entity tables */ } from './schema';

// ============================================
// CONFIGURATION
// ============================================

const CONFIG = {
  testUser: {
    email: 'test@example.com',
    password: 'password123',  // Hash this in production!
    role: 'admin'
  },
  recordCounts: {
    users: 20,
    projects: 15,
    // Add counts for each entity
  }
};

// ============================================
// HELPER FUNCTIONS
// ============================================

// Random selection from array
const randomFrom = <T>(arr: T[]): T => arr[Math.floor(Math.random() * arr.length)];

// Random number in range
const randomBetween = (min: number, max: number): number => 
  Math.floor(Math.random() * (max - min + 1)) + min;

// Random date within range
const randomDate = (start: Date, end: Date): Date => 
  new Date(start.getTime() + Math.random() * (end.getTime() - start.getTime()));

// Random boolean
const randomBool = (): boolean => Math.random() > 0.5;

// Generate unique ID
let idCounter = 1000;
const nextId = (): number => idCounter++;

// ============================================
// SAMPLE DATA POOLS
// ============================================

const FIRST_NAMES = [
  'James', 'Mary', 'John', 'Patricia', 'Robert', 'Jennifer', 'Michael', 'Linda',
  'William', 'Elizabeth', 'David', 'Barbara', 'Richard', 'Susan', 'Joseph', 'Jessica',
  'Thomas', 'Sarah', 'Charles', 'Karen', 'Christopher', 'Nancy', 'Daniel', 'Lisa',
  'María', 'José', 'Wei', 'Fatima', 'Mohammed', 'Yuki', 'Priya', 'Raj'
];

const LAST_NAMES = [
  'Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia', 'Miller', 'Davis',
  'Rodriguez', 'Martinez', 'Hernandez', 'Lopez', 'Gonzalez', 'Wilson', 'Anderson',
  'Thomas', 'Taylor', 'Moore', 'Jackson', 'Martin', 'Lee', 'Thompson', 'White',
  'Chen', 'Patel', 'Kim', 'Nakamura', 'Singh', 'Okonkwo', 'Müller'
];

const EMAIL_DOMAINS = ['gmail.com', 'yahoo.com', 'outlook.com', 'company.com', 'example.com'];

const STATUSES = ['active', 'inactive', 'pending', 'suspended', 'archived'];

const PRIORITIES = ['low', 'medium', 'high', 'critical'];

const LOREM_WORDS = [
  'lorem', 'ipsum', 'dolor', 'sit', 'amet', 'consectetur', 'adipiscing', 'elit',
  'sed', 'do', 'eiusmod', 'tempor', 'incididunt', 'ut', 'labore', 'et', 'dolore',
  'magna', 'aliqua', 'enim', 'ad', 'minim', 'veniam', 'quis', 'nostrud'
];

// ============================================
// GENERATOR FUNCTIONS
// ============================================

function generateEmail(firstName: string, lastName: string): string {
  const formats = [
    `${firstName.toLowerCase()}.${lastName.toLowerCase()}`,
    `${firstName.toLowerCase()}${lastName.toLowerCase()}`,
    `${firstName.toLowerCase()}_${lastName.toLowerCase()}`,
    `${firstName[0].toLowerCase()}${lastName.toLowerCase()}`,
  ];
  return `${randomFrom(formats)}@${randomFrom(EMAIL_DOMAINS)}`;
}

function generatePhone(): string {
  return `(${randomBetween(200, 999)}) ${randomBetween(200, 999)}-${randomBetween(1000, 9999)}`;
}

function generateSentence(wordCount: number = 10): string {
  const words = Array.from({ length: wordCount }, () => randomFrom(LOREM_WORDS));
  words[0] = words[0].charAt(0).toUpperCase() + words[0].slice(1);
  return words.join(' ') + '.';
}

function generateParagraph(sentenceCount: number = 4): string {
  return Array.from({ length: sentenceCount }, () => 
    generateSentence(randomBetween(8, 15))
  ).join(' ');
}

// ============================================
// ENTITY GENERATORS
// ============================================

interface GeneratedUser {
  id: number;
  email: string;
  password: string;
  firstName: string;
  lastName: string;
  phone: string;
  role: string;
  status: string;
  createdAt: Date;
  lastLoginAt: Date | null;
}

function generateUser(overrides: Partial<GeneratedUser> = {}): GeneratedUser {
  const firstName = randomFrom(FIRST_NAMES);
  const lastName = randomFrom(LAST_NAMES);
  const createdAt = randomDate(new Date('2023-01-01'), new Date());
  
  return {
    id: nextId(),
    email: generateEmail(firstName, lastName),
    password: 'hashed_password_here',  // Use proper hashing
    firstName,
    lastName,
    phone: generatePhone(),
    role: randomFrom(['admin', 'manager', 'user', 'viewer']),
    status: randomFrom(STATUSES),
    createdAt,
    lastLoginAt: randomBool() ? randomDate(createdAt, new Date()) : null,
    ...overrides
  };
}

// Add more entity generators following the same pattern:

// function generateProject(overrides = {}): Project { ... }
// function generateHospital(overrides = {}): Hospital { ... }
// function generateConsultant(overrides = {}): Consultant { ... }
// etc.

// ============================================
// SEED FUNCTIONS
// ============================================

async function seedUsers() {
  console.log('Seeding users...');
  
  // 1. Create test user (always first)
  const testUser = generateUser({
    email: CONFIG.testUser.email,
    password: CONFIG.testUser.password,
    role: 'admin',
    status: 'active',
    firstName: 'Test',
    lastName: 'User'
  });
  
  // 2. Create admin users
  const admins = Array.from({ length: 2 }, () => 
    generateUser({ role: 'admin', status: 'active' })
  );
  
  // 3. Create managers
  const managers = Array.from({ length: 3 }, () => 
    generateUser({ role: 'manager', status: 'active' })
  );
  
  // 4. Create regular users (various statuses)
  const regularUsers = Array.from({ length: 10 }, () => 
    generateUser({ role: 'user' })
  );
  
  // 5. Create edge case users
  const edgeCaseUsers = [
    // Very long name
    generateUser({ 
      firstName: 'Alexander-Christopher',
      lastName: 'Van-der-Westhuizen-Johannesburg',
      role: 'user',
      status: 'active'
    }),
    // Unicode characters
    generateUser({
      firstName: 'José',
      lastName: 'García-Müller',
      role: 'user',
      status: 'active'
    }),
    // Inactive user
    generateUser({
      status: 'inactive',
      lastLoginAt: new Date('2022-01-01')
    }),
    // Pending user (never logged in)
    generateUser({
      status: 'pending',
      lastLoginAt: null
    }),
    // Suspended user
    generateUser({
      status: 'suspended'
    })
  ];
  
  const allUsers = [testUser, ...admins, ...managers, ...regularUsers, ...edgeCaseUsers];
  
  // Insert into database
  await db.insert(users).values(allUsers);
  
  console.log(`✅ Created ${allUsers.length} users`);
  return allUsers;
}

// Add more seed functions for each entity:

// async function seedProjects(users: User[]) { ... }
// async function seedHospitals() { ... }
// async function seedConsultants() { ... }
// etc.

// ============================================
// MAIN SEED FUNCTION
// ============================================

async function seed() {
  console.log('🌱 Starting database seed...\n');
  
  try {
    // Clear existing data (optional - use with caution!)
    // await db.delete(users);
    // await db.delete(projects);
    
    // Seed in dependency order
    const createdUsers = await seedUsers();
    // const createdProjects = await seedProjects(createdUsers);
    // const createdHospitals = await seedHospitals();
    // etc.
    
    console.log('\n✅ Database seeding complete!');
    console.log('━'.repeat(40));
    console.log('Test User Credentials:');
    console.log(`  Email: ${CONFIG.testUser.email}`);
    console.log(`  Password: ${CONFIG.testUser.password}`);
    console.log('━'.repeat(40));
    
  } catch (error) {
    console.error('❌ Seeding failed:', error);
    throw error;
  }
}

// Run if called directly
seed().catch(console.error);
```

---

## Fixture Data Template (JSON)

Create these files in `cypress/fixtures/`:

### users.json
```json
{
  "testUser": {
    "email": "test@example.com",
    "password": "password123"
  },
  "adminUser": {
    "email": "admin@example.com",
    "password": "admin123"
  },
  "regularUser": {
    "email": "user@example.com",
    "password": "user123"
  },
  "invalidUser": {
    "email": "invalid@example.com",
    "password": "wrongpassword"
  },
  "newUser": {
    "firstName": "New",
    "lastName": "User",
    "email": "newuser@example.com",
    "password": "NewUser123!",
    "role": "user"
  },
  "edgeCases": {
    "longName": {
      "firstName": "Alexandros-Konstantinos-Theodoros",
      "lastName": "Papadopoulos-Karamanlis-Venizelos",
      "email": "longname@example.com"
    },
    "specialChars": {
      "firstName": "José",
      "lastName": "O'Brien-García",
      "email": "special@example.com"
    },
    "unicodeName": {
      "firstName": "田中",
      "lastName": "太郎",
      "email": "unicode@example.com"
    }
  }
}
```

### generic-records.json
```json
{
  "validRecord": {
    "name": "Test Record",
    "description": "This is a test record for E2E testing.",
    "status": "active",
    "priority": "medium"
  },
  "minimalRecord": {
    "name": "Minimal"
  },
  "maximalRecord": {
    "name": "Maximal Record With All Fields",
    "description": "This record has every optional field filled in for comprehensive testing purposes.",
    "status": "active",
    "priority": "high",
    "category": "category-a",
    "tags": ["tag1", "tag2", "tag3"],
    "metadata": {
      "source": "e2e-test",
      "version": "1.0"
    }
  },
  "edgeCases": {
    "longName": {
      "name": "This is an extremely long name that tests the maximum character limit for the name field in the database and UI"
    },
    "specialChars": {
      "name": "Test <script>alert('xss')</script> & \"quotes\" 'apostrophe'",
      "description": "Contains <b>HTML</b> and \"special\" characters & symbols © ® ™"
    },
    "unicode": {
      "name": "日本語テスト 한국어 العربية",
      "description": "Emoji test: 🎉 ✅ ❌ 🚀 💡 🔥"
    },
    "whitespace": {
      "name": "  Leading and trailing spaces  ",
      "description": "\n\nNewlines\n\nand\ttabs\t\there"
    },
    "empty": {
      "name": "",
      "description": ""
    }
  }
}
```

### dates.json
```json
{
  "today": "2024-12-01",
  "yesterday": "2024-11-30",
  "lastWeek": "2024-11-24",
  "lastMonth": "2024-11-01",
  "lastYear": "2023-12-01",
  "future": "2025-06-15",
  "farFuture": "2030-01-01",
  "pastYear": "2020-01-01",
  "dateRanges": {
    "thisWeek": {
      "start": "2024-11-25",
      "end": "2024-12-01"
    },
    "thisMonth": {
      "start": "2024-11-01",
      "end": "2024-11-30"
    },
    "thisQuarter": {
      "start": "2024-10-01",
      "end": "2024-12-31"
    },
    "thisYear": {
      "start": "2024-01-01",
      "end": "2024-12-31"
    }
  },
  "invalidDates": {
    "impossibleDate": "2024-02-30",
    "wrongFormat": "01-12-2024",
    "textDate": "December First",
    "partialDate": "2024-12"
  }
}
```

---

## Data Requirements Checklist

For comprehensive testing, ensure you have:

### ☐ User Data
- [ ] At least 1 admin user
- [ ] At least 1 manager user
- [ ] Multiple regular users (10+)
- [ ] Inactive user(s)
- [ ] Pending user(s)
- [ ] Suspended user(s)
- [ ] User with long name
- [ ] User with special characters
- [ ] User with Unicode name

### ☐ Entity Data (for each entity type)
- [ ] 15-20 records (for pagination)
- [ ] Records in each status
- [ ] Records with various dates (past, present, future)
- [ ] Records with different priorities/categories
- [ ] Records with edge case data
- [ ] Related records (parent-child relationships)

### ☐ Edge Case Data
- [ ] Empty/null fields
- [ ] Maximum length strings
- [ ] Special characters
- [ ] Unicode/international characters
- [ ] HTML/script tags (for XSS testing)
- [ ] Whitespace variations
- [ ] Boundary numbers (0, -1, MAX_INT)
- [ ] Boundary dates

### ☐ Relationship Data
- [ ] One-to-one relationships
- [ ] One-to-many relationships
- [ ] Many-to-many relationships
- [ ] Orphaned records (for cascade testing)
- [ ] Circular references (if applicable)

---

## Quick Seed Commands

Add these to your `package.json`:

```json
{
  "scripts": {
    "seed": "npx tsx seed.ts",
    "seed:test": "NODE_ENV=test npx tsx seed.ts",
    "seed:reset": "npm run db:reset && npm run seed",
    "seed:minimal": "npx tsx seed.ts --minimal",
    "seed:full": "npx tsx seed.ts --full"
  }
}
```

Then run:
```bash
npm run seed        # Seed with default data
npm run seed:reset  # Clear and re-seed
npm run seed:full   # Seed with maximum data
```
