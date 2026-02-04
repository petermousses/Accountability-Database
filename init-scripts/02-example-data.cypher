// Example Agent
CREATE (a:Agent {
  id: "agent-example-001",
  name: "Example Agent",
  badge_number: "EX001",
  amount_paid: 0,
  status: "Suspected",
  created_at: datetime()
});

// Example Violation
CREATE (v:Violation {
  id: "violation-example-001",
  type: "abuse",
  description: "Example violation",
  severity: "moderate",
  created_at: datetime()
});
