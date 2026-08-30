# Module Handoff Document Template

Use this template when completing a milestone or passing interface outputs to another developer.

---

## 1. Module Name & Owner
- **Module:** `src/<module_name>/`
- **Owner:** <Developer Name>
- **Date:** YYYY-MM-DD
- **Target Consumer Module:** `src/<downstream_module>/` (<Downstream Developer>)

---

## 2. Changes Delivered
- Brief summary of functions/classes delivered.
- Verified input shapes and output shapes.

---

## 3. Contract Compliance
- Which contract from `CONTRACTS.md` does this adhere to?
- Confirm coordinate convention (X = forward, Y = left, Z = up, units = meters).

---

## 4. How to Test
```bash
pytest tests/<module_name>/ -v
```

---

## 5. Known Limitations & Next Steps
- Edge cases not yet handled.
- Dependencies or environment considerations.
