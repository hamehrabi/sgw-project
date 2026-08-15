"""Durable state, and the constraints that make the business rules true.

Every constraint the store can express lives in the schema rather than in application
code (ADR-002): a rule that lives only in code is removed by the first refactor with
every test still green.
"""
