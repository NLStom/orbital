# Test Datasets for Graphiton

Three themed datasets designed to showcase Graphiton's capabilities: pattern discovery, data cleaning, and visualization.

---

## Dataset 1: FreshMart (Grocery E-commerce)

**Domain**: Retail / Supply Chain
**Tables**: 5
**Total Rows**: ~100

### Tables

| Table | Rows | Description |
|-------|------|-------------|
| customers.csv | 18 | Customer master data |
| products.csv | 18 | Product catalog with supplier FK |
| suppliers.csv | 7 | Supplier info with reliability scores |
| orders.csv | 38 | Order transactions |
| inventory_shipments.csv | 22 | Supplier deliveries to warehouse |

### Story to Discover

> **"FreshMart loses money on perishables because shipments arrive on Mondays but demand peaks on weekends."**

The agent should find:
- Orders spike on Saturday/Sunday (day_of_week column)
- All shipments arrive on Monday (arrival_date)
- Spoiled orders cluster on Monday (status = 'spoiled')
- South region supplier (S003) has lowest reliability and quality grades

### Data Quality Issues

| Issue | Location | Example |
|-------|----------|---------|
| Missing customer_id | orders.csv | O006, O011, O018, O024, O033 have blank customer_id |
| Inconsistent date formats | customers.csv, orders.csv | "2023-03-15" vs "Jan 5, 2023" vs "03/20/2023" |
| Duplicate customers | customers.csv | C001/C011/C015 are all "Alice Chen" variants |
| Missing price | products.csv | P015 (Olive Oil) has no unit_price |
| Negative quantity | orders.csv | O029 has quantity = -1 |
| Missing email | customers.csv | C016 has blank email |

---

## Dataset 2: TechCorp (HR Analytics)

**Domain**: Human Resources
**Tables**: 5
**Total Rows**: ~80

### Tables

| Table | Rows | Description |
|-------|------|-------------|
| departments.csv | 6 | Department lookup with budgets |
| employees.csv | 25 | Employee records with hierarchy |
| performance_reviews.csv | 25 | Quarterly performance ratings |
| training_courses.csv | 10 | Available training programs |
| training_enrollment.csv | 15 | Course enrollment records |

### Story to Discover

> **"Remote workers outperform office workers by 15% but earn 12% less."**

The agent should find:
- Remote employees: E003, E006, E009, E014, E016, E017, E019, E021, E023, E024, E025
- Remote avg performance: ~4.4 (high performers)
- Remote avg salary: lower than office counterparts in same roles
- Engineering has lowest training participation despite highest budget
- Some salaries are clearly monthly (E006: $6,500, E014: $8,500) vs annual

### Data Quality Issues

| Issue | Location | Example |
|-------|----------|---------|
| Orphan manager_id | employees.csv | E013 reports to E099 (doesn't exist) |
| Salary unit mismatch | employees.csv | E006=$6,500 and E014=$8,500 (monthly vs annual) |
| Missing hire_date | employees.csv | E016 has blank hire_date |
| Inconsistent dept names | employees.csv | "Engineering" vs "Eng" vs "Mktg" vs "marketing" |
| Future hire_date | employees.csv | E024 hired "2026-03-15" |

---

## Dataset 3: GlobalAir (Travel Network)

**Domain**: Aviation / Travel
**Tables**: 4
**Total Rows**: ~85

### Tables

| Table | Rows | Description |
|-------|------|-------------|
| airports.csv | 10 | Airport master data |
| routes.csv | 24 | Flight routes between cities |
| weather.csv | 35 | Daily weather by city |
| delays.csv | 28 | Flight delay records |

### Story to Discover

> **"40% of London delays correlate with weather - adding weather-based rebooking could save millions."**

The agent should find:
- London (LHR) routes have the most delays
- Storm days (Jan 7-8, Jan 20-21) = massive delays (150-270 min)
- Clear/Cloudy days = minimal delays (0-30 min)
- Cascade delays: DXB delays (DL021, DL024) happen after LHR storms
- Tokyo routes are consistently on-time (good weather)

### Data Quality Issues

| Issue | Location | Example |
|-------|----------|---------|
| Mixed airport codes/city names | routes.csv | R012 uses "London" instead of "LHR", R015 uses "London" |
| Missing airline | routes.csv | R012 has blank airline |
| Delay unit mismatch | delays.csv | DL006 = 2.5 (hours) vs others in minutes |
| Negative delay | delays.csv | DL008 = -15 (early arrival recorded wrong) |
| Weather data gaps | weather.csv | Singapore missing most days |

---

## Relationships (ERD)

### FreshMart
```
customers ──1:N── orders ──N:1── products ──N:1── suppliers
                                    │
suppliers ──1:N── inventory_shipments
```

### TechCorp
```
departments ──1:N── employees ──1:N── performance_reviews
                       │
                       └──1:N── training_enrollment ──N:1── training_courses
                       │
                       └── manager_id (self-reference)
```

### GlobalAir
```
airports ──1:N── routes (origin) ──1:N── delays
    │               │
    └──1:N── routes (destination)
    │
    └──1:N── weather
```

---

## Usage

Upload any dataset folder as a multi-file upload to create a linked dataset:

```
1. Create new session in Graphiton
2. Click + button in chat
3. Select all CSVs from one folder (e.g., all freshmart/*.csv)
4. Ask questions like:
   - "Why are orders being spoiled?"
   - "Show me the relationship between weather and delays"
   - "Which employees are underpaid relative to their performance?"
```

---

## Testing Checklist

- [ ] Agent can JOIN tables correctly via foreign keys
- [ ] Agent discovers the embedded story/pattern
- [ ] Agent identifies data quality issues when asked
- [ ] Charts render correctly from query results
- [ ] Graph visualization works for network data (routes)

---

*Generated: 2025-02-03*
