-- 021 — the situation summary, with its lifecycle in the schema (CHG-040).
--
-- Exactly three states, and the walls between them are constraints rather than service code
-- (ADR-002): a summary cannot be Approved without an approver and a time, cannot carry
-- approved text while still a Draft, and cannot exist without the figures it was drafted
-- from and the verification that judged it.
--
-- `label` is the honesty marker CHG-040 specifies: `Drafted from platform data` when the
-- model's draft survived verification, `Assembled from platform data` when a second failure
-- fell back to templated text. A reader can always tell which they are holding.

create table summaries (
    id             text primary key,
    scenario_id    text not null references scenarios (id) on delete cascade,
    state          text not null default 'Draft'
                   check (state in ('Draft', 'Approved', 'Sent')),
                                              -- the frozen vocabulary, in the store: never
                                              --   'pending', never 'published'
    draft_text     text not null,
    approved_text  text,
    label          text not null
                   check (label in ('Drafted from platform data',
                                    'Assembled from platform data')),
    source_figures text not null,             -- json: the fixed set the model was allowed to
                                              --   see, stored so the verification table can
                                              --   be re-rendered forever (§6: reads from
                                              --   stored rows)
    verification   text not null,             -- json: every extracted figure and noun, with
                                              --   its platform value and verdict
    drafted_at     text not null,
    drafted_by     text not null references users (id),
    approved_by    text references users (id),
    approved_at    text,
    seq            integer not null,

    check ((state = 'Draft') = (approved_by is null)
           and (state = 'Draft') = (approved_at is null)
           and (state = 'Draft') = (approved_text is null)),
                                              -- approval is never anonymous, never undated,
                                              --   and never textless; a Draft is all three
    unique (scenario_id, seq)
);

create index summaries_latest on summaries (scenario_id, seq desc);

-- BR-004, re-asserted. Present after this migration or the guarantee is gone (ADR-004).
create trigger if not exists decision_records_no_update
before update on decision_records
begin
    select raise(abort, 'decision_records is append-only (BR-004, ADR-004)');
end;

create trigger if not exists decision_records_no_delete
before delete on decision_records
begin
    select raise(abort, 'decision_records is append-only (BR-004, ADR-004)');
end;
