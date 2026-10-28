# Specifications

The chronometer is developed spec-first for changes to its file formats, its exchange with the
cycling site and what the judge sees, with [Spec Kit](https://github.com/github/spec-kit), whose
skills both coding agents here (Claude Code and Codex) carry.

```
specs/
  app/                        the program as it works today
    chronometer.md            slots, files, backups, site exchange
  <NNN>-<short-name>/         one feature
    spec.md                   what and why, for the judge and the readers of the files
    plan.md, tasks.md         how it will be built, once the spec is reviewed
```

The principles every plan is checked against are in
[`.specify/memory/constitution.md`](../.specify/memory/constitution.md).

**Keep `app/` true.** A change that alters described behaviour updates it in the same pull request.
