// Create constraints for data integrity
CREATE CONSTRAINT agent_name_unique IF NOT EXISTS FOR (a:Agent) REQUIRE a.name IS UNIQUE;
CREATE CONSTRAINT violation_id_unique IF NOT EXISTS FOR (v:Violation) REQUIRE v.id IS UNIQUE;
CREATE CONSTRAINT incident_id_unique IF NOT EXISTS FOR (i:Incident) REQUIRE i.id IS UNIQUE;
CREATE CONSTRAINT employee_id_unique IF NOT EXISTS FOR (e:Employee) REQUIRE e.id IS UNIQUE;

// Create indexes for performance
CREATE INDEX agent_name_idx IF NOT EXISTS FOR (a:Agent) ON (a.name);
CREATE INDEX agent_status_idx IF NOT EXISTS FOR (a:Agent) ON (a.status);
CREATE INDEX violation_type_idx IF NOT EXISTS FOR (v:Violation) ON (v.type);
CREATE INDEX incident_date_idx IF NOT EXISTS FOR (i:Incident) ON (i.date);
CREATE INDEX employee_name_idx IF NOT EXISTS FOR (e:Employee) ON (e.name);

// Create node property constraints
CREATE CONSTRAINT agent_id_exists IF NOT EXISTS FOR (a:Agent) REQUIRE a.id IS NOT NULL;
CREATE CONSTRAINT violation_id_exists IF NOT EXISTS FOR (v:Violation) REQUIRE v.id IS NOT NULL;
