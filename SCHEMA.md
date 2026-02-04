# Neo4j Database Schema

## Node Types

### 1. Agent
ICE agents involved in violations.
- uid=1000(claude) gid=1000(claude) groups=1000(claude),4(adm),24(cdrom),27(sudo),30(dip),46(plugdev),101(lxd) (String, UNIQUE)
-  (String, UNIQUE) - Agent name
-  (String) - Badge/employee ID
-  (Float) - Compensation or estimate
-  (String) - Known address
-  (String) - Confirmed, Suspected, Out of Frame
- ,  (DateTime)
-  (String)

### 2. Violation
Documents violations (execution, murder, abuse, etc.)
- uid=1000(claude) gid=1000(claude) groups=1000(claude),4(adm),24(cdrom),27(sudo),30(dip),46(plugdev),101(lxd) (String, UNIQUE)
-  (String) - execution, murder, abuse, assault, etc.
-  (String)
- Wed Feb  4 03:12:50 AM UTC 2026 (Date)
-  (String)
-  (Integer)
-  (String) - critical, severe, moderate, mild
- ,  (DateTime)

### 3. Incident
Specific incidents linking violations to agents.
- uid=1000(claude) gid=1000(claude) groups=1000(claude),4(adm),24(cdrom),27(sudo),30(dip),46(plugdev),101(lxd) (String, UNIQUE)
-  (String)
- Wed Feb  4 03:12:50 AM UTC 2026 (Date)
-  (String)
-  (String) - Confirmed, Suspected, Out of Frame
-  (List<String>) - FOIA, news, etc.
- ,  (DateTime)

### 4. Employee (ICE Registry)
All ICE employees since Trump administration.
- uid=1000(claude) gid=1000(claude) groups=1000(claude),4(adm),24(cdrom),27(sudo),30(dip),46(plugdev),101(lxd) (String, UNIQUE)
-  (String) - Full name
-  (String)
-  (String)
-  (String) - Job title
-  (Date)
-  (String)
-  (String) - Active, Inactive, Terminated

### 5. Source
Evidence and documentation sources.
- uid=1000(claude) gid=1000(claude) groups=1000(claude),4(adm),24(cdrom),27(sudo),30(dip),46(plugdev),101(lxd) (String, UNIQUE)
-  (String) - FOIA, news, report, testimony, etc.
-  (String)
-  (String)
-  (String)
-  (Date)
-  (Float) - 0-1

## Relationships

- **COMMITTED**: Agent → Violation (with confirmation_status, role)
- **INVOLVED_IN**: Agent/Employee → Incident
- **DOCUMENTED_BY**: Incident → Source
- **RELATED_TO**: Violation → Violation (pattern tracking)
- **EMPLOYED_AS**: Employee → Position

## Key Queries

See DEPLOYMENT.md for detailed examples.

