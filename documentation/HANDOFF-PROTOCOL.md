# 🔄 Handoff Protocol for PTV Transit

This document describes the shift handoff system for seamless collaboration between developers working in 12-hour rotating shifts across timezones.

## Team Configuration

| Developer | Subscription | Timezone | Role |
|-----------|--------------|----------|------|
| **Gaurav** | Claude Pro Max | Melbourne (AEST/AEDT) | Development Manager |
| **Imad** | Claude Pro | [TBD] | Peer Programmer |

---

## 📁 File Structure

```
ptv_transit/
└── .claude/
    ├── CLAUDE.md                    # Project context (auto-loaded by Claude Code)
    ├── commands/
    │   ├── handoff.md               # /handoff - Generate end-of-shift handoff
    │   ├── catchup.md               # /catchup - Load start-of-shift context
    │   ├── status.md                # /status  - Quick status check
    │   └── sync.md                  # /sync    - Git synchronization helper
    └── handoffs/
        ├── CURRENT-HANDOFF.md       # Active handoff document
        └── archive/                  # Historical handoffs (optional)
            └── 2026-01-14-gaurav.md
```

---

## 🚀 Quick Reference

### Starting Your Shift

```bash
# 1. Pull latest code (includes handoff)
cd ptv_transit
git pull origin main

# 2. Activate environment
source venv/bin/activate

# 3. Start Claude Code
claude

# 4. Load context from previous shift
/catchup

# 5. (Optional) Quick status check
/status

# 6. Start working!
```

### Ending Your Shift

```bash
# 1. In your Claude Code session, generate handoff
/handoff

# 2. Review the generated handoff document
# (Claude will create .claude/handoffs/CURRENT-HANDOFF.md)

# 3. Commit all changes including handoff
git add .
git commit -m "Handoff: 2026-01-14 Gaurav -> Imad"

# 4. Push to GitHub
git push origin main

# 5. Done! Your partner can now continue seamlessly.
```

---

## 📋 Custom Slash Commands

| Command | When to Use | What It Does |
|---------|-------------|--------------|
| `/catchup` | **Start** of shift | Reads handoff, summarizes priorities, offers next steps |
| `/handoff` | **End** of shift | Analyzes session, creates handoff document |
| `/status` | Anytime | Quick project status (git, tests, handoff info) |
| `/sync` | Before/after work | Helps with git pull/push operations |

---

## 📝 Handoff Document Structure

Each handoff includes:

1. **✅ Completed This Session** - What was accomplished
2. **🔄 Work In Progress** - Partial work with exact state
3. **⚠️ Blockers & Issues** - Problems to be aware of
4. **📝 Decisions Made** - Technical decisions and rationale
5. **🎯 Priorities for Next Session** - Ordered task list
6. **📁 Files Changed** - What was modified
7. **🧪 Test Status** - Passing/failing tests
8. **💬 Notes** - Personal tips for the next developer

---

## 🔧 How It Works

### The Problem
Claude Code sessions don't persist between sessions. When you start a new session, Claude has no memory of previous work. This is especially problematic for:
- Multi-day projects
- Team collaboration across timezones
- Complex, multi-phase implementations

### The Solution
File-based handoff system that:
1. **Captures context** at end of each session
2. **Stores in Git** for version control and sharing
3. **Auto-loads via CLAUDE.md** for project context
4. **Restores via /catchup** for session-specific context

### Why Files Instead of Session Persistence?
- ✅ Works with both Pro and Pro Max subscriptions
- ✅ Version controlled (can see history of handoffs)
- ✅ Human-readable (can review without Claude)
- ✅ No dependency on cloud storage
- ✅ Works offline

---

## ⚠️ Important Rules

### DO ✅
- Run `/catchup` at the START of every session
- Run `/handoff` at the END of every session
- Commit and push handoff before logging off
- Pull latest before starting work
- Keep handoffs specific and actionable

### DON'T ❌
- Don't skip the handoff (your partner loses context)
- Don't work without pulling first (causes merge conflicts)
- Don't leave uncommitted changes
- Don't write vague handoffs ("worked on stuff")
- Don't forget to mention blockers

---

## 🔄 Workflow Diagram

```
┌─────────────────┐
│  Developer A    │
│  Starts Shift   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  git pull       │
│  /catchup       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Development    │
│  Work           │
│  (several hrs)  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  /handoff       │
│  git add .      │
│  git commit     │
│  git push       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Developer A    │
│  Ends Shift     │
└────────┬────────┘
         │
    ═════╪═════════════════════════════
         │        (12 hours pass)
         │
         ▼
┌─────────────────┐
│  Developer B    │
│  Starts Shift   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  git pull       │  ← Gets A's handoff
│  /catchup       │  ← Loads context
└────────┬────────┘
         │
         ▼
    (cycle continues)
```

---

## 🛠️ Troubleshooting

### "No handoff file found"
```bash
# Check if file exists
ls -la .claude/handoffs/

# Check archive
ls -la .claude/handoffs/archive/

# Fallback to legacy context
cat CONTEXT.md
```

### "Merge conflicts after pull"
```bash
# See conflicting files
git status

# Open and resolve conflicts manually
# Then:
git add .
git commit -m "Resolve merge conflicts"
```

### "Tests failing after pulling"
```bash
# Run tests to see failures
pytest -v

# Check if dependencies changed
pip install -r requirements.txt

# If still failing, check handoff for known issues
```

### "Claude doesn't see the CLAUDE.md"
- Ensure you're in the correct directory: `cd ptv_transit`
- Check file exists: `ls .claude/CLAUDE.md`
- Claude Code auto-loads `.claude/CLAUDE.md` at session start

---

## 📊 Best Practices

### For Effective Handoffs

1. **Be Specific**: "Implemented X in file Y" not "worked on stuff"
2. **Include Context**: Why decisions were made, not just what
3. **List Files**: Changed files help the next dev get oriented
4. **Prioritize**: Order next tasks by importance
5. **Test Status**: Always mention if tests pass/fail

### For Smooth Transitions

1. **Commit Often**: Small commits are easier to understand
2. **Push Promptly**: Don't leave code only on your machine
3. **Document Blockers**: Even if you can't solve them
4. **Leave Clean State**: No half-working code if possible
5. **Update Docs**: Keep DEVELOPMENT_STATUS.md current

---

## 📚 References

- [Claude Code Memory Documentation](https://code.claude.com/docs/en/memory)
- [Claude Code Slash Commands](https://code.claude.com/docs/en/slash-commands)
- [GTFS Specification](https://gtfs.org/)
- [Project Repository](https://github.com/caprihan/PTV_Assistant)

---

*Protocol Version: 1.0*
*Last Updated: 2026-01-14*
