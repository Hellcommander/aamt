// Places the new skills of a skill-page mod on their parent tab's tree cells.
// Canonical copy: TreePlacement.py pastes this block into each skill-page mod's mod.js
// (D2RMM mods cannot share code), together with that mod's STOCK_CELLS table.
//
//   placeOnTree(skills, skilldesc, cls, list, stockCells, label)
//     skills, skilldesc  the tables as they are before the mod adds rows
//     cls                charclass of the page ('sor', 'bar', ...)
//     list               [{ name, slot, parent }]: the new skill, the stock skill whose cell it
//                        takes, and the parent tab's SkillPage ('1'-'3')
//     stockCells         slot name -> [page, row, column, reqlevel, IconCel, [prerequisites]] in
//                        the unmodded game
//   returns              name -> { SkillRow, SkillColumn, IconCel, reqlevel, reqskill1-3 }, the
//                        prerequisites already turned into the page's own new skills
//
// A new page shows its parent tab's picture, so each new skill takes the cell, level,
// prerequisites (as arrows) and icon of a skill on that tab. Normally that is its slot skill.
// Mods that rework the class trees (total conversions) may have moved or removed it, so:
//   1. the slot skill, if it is a class skill on the parent tab (the unmodded game: always);
//   2. else the class skill now in the slot's stock cell of the parent tab;
//   3. else a cell of the parent tab whose skill no new skill has taken yet (row by row), so
//      the picture still has a frame there;
//   4. else the stock cell if it is free, or any free cell, with the stock level and icon.
// Prerequisites that do not lead to a new skill of the same page are left out (with a warning).
function placeOnTree(skills, skilldesc, cls, list, stockCells, label) {
  const descs = {};
  skilldesc.rows.forEach((d) => {
    const k = String(d.skilldesc || '').toLowerCase();
    if (k && !descs[k]) descs[k] = d;
  });
  // Class skills on a tree cell, per page; first row of each name only (findRow does the same).
  const byName = {};
  const onPage = {};
  skills.rows.forEach((r) => {
    const name = String(r.skill || '').toLowerCase();
    if (!name || byName[name] !== undefined) return;
    byName[name] = null;
    if (r.charclass !== cls) return;
    const d = descs[String(r.skilldesc || '').toLowerCase()];
    if (!d) return;
    const row = Number(d.SkillRow);
    const col = Number(d.SkillColumn);
    if (!(row >= 1 && row <= 6 && col >= 1 && col <= 3)) return;
    const o = { skill: r, desc: d, page: String(d.SkillPage), cell: `${row}/${col}`, row, col };
    byName[name] = o;
    (onPage[o.page] = onPage[o.page] || []).push(o);
  });
  Object.keys(onPage).forEach((p) => onPage[p].sort((a, b) => a.row - b.row || a.col - b.col));

  const taken = {}; // page -> cell -> new skill name
  const used = new Set(); // occupants already given to a new skill
  const placed = {}; // new skill name -> { o, row, col, how }
  const free = (page, cell) => !(taken[page] && taken[page][cell]);
  function put(s, o, row, col, how) {
    const cell = `${row}/${col}`;
    if (!free(s.parent, cell)) throw new Error(`${label}: two skills share the cell of ${s.slot}`);
    (taken[s.parent] = taken[s.parent] || {})[cell] = s.name;
    if (o) used.add(o);
    placed[s.name] = { o, row, col, how };
  }
  const stock = (s) => stockCells[s.slot] || null;
  // 1. the slot skill itself
  list.forEach((s) => {
    const o = byName[s.slot.toLowerCase()];
    if (o && o.page === String(s.parent)) put(s, o, o.row, o.col, 1);
  });
  // 2. whoever sits in the slot's stock cell now
  list.forEach((s) => {
    const st = stock(s);
    if (placed[s.name] || !st) return;
    const o = (onPage[s.parent] || []).find((x) => x.row === st[1] && x.col === st[2]);
    if (o && !used.has(o) && free(s.parent, o.cell)) put(s, o, o.row, o.col, 2);
  });
  // 3. the tab's other skills, row by row, for the rest (in their stock order)
  const rest = list.filter((s) => !placed[s.name]);
  const order = (s) => (stock(s) ? stock(s)[1] * 10 + stock(s)[2] : 99);
  rest.sort((a, b) => order(a) - order(b)).forEach((s) => {
    const o = (onPage[s.parent] || []).find((x) => !used.has(x) && free(s.parent, x.cell));
    if (o) put(s, o, o.row, o.col, 3);
  });
  // 4. no skill left to mirror: the stock cell, or the first free cell
  rest.forEach((s) => {
    if (placed[s.name]) return;
    const st = stock(s);
    let row = st ? st[1] : 0;
    let col = st ? st[2] : 0;
    if (!st || !free(s.parent, `${row}/${col}`)) {
      row = 0;
      for (let r = 1; r <= 6 && !row; r++) {
        for (let c = 1; c <= 3 && !row; c++) {
          if (free(s.parent, `${r}/${c}`)) {
            row = r;
            col = c;
          }
        }
      }
      if (!row) throw new Error(`${label}: no free cell left for ${s.name}`);
    }
    put(s, null, row, col, 4);
  });

  // Level, prerequisites and icon of whatever the new skill mirrors.
  const pageOf = {};
  list.forEach((s) => (pageOf[s.name] = String(s.parent)));
  const newOn = (o, page) => {
    const n = o && list.find((s) => placed[s.name].o === o);
    return n && pageOf[n.name] === page ? n.name : '';
  };
  const out = {};
  list.forEach((s) => {
    const p = placed[s.name];
    const st = stock(s);
    const res = {
      SkillRow: p.o ? p.o.desc.SkillRow : String(p.row),
      SkillColumn: p.o ? p.o.desc.SkillColumn : String(p.col),
      IconCel: p.o ? p.o.desc.IconCel : st ? String(st[4]) : '0',
      reqlevel: p.o ? p.o.skill.reqlevel : st ? String(st[3]) : '1',
    };
    const needs = p.o
      ? ['reqskill1', 'reqskill2', 'reqskill3'].map((c) => p.o.skill[c] || '')
      : (st ? st[5] : []).concat(['', '', '']).slice(0, 3);
    needs.forEach((need, i) => {
      let mapped = '';
      if (need) {
        if (p.o) mapped = newOn(byName[need.toLowerCase()], pageOf[s.name]);
        else {
          const n = list.find((x) => x.slot.toLowerCase() === need.toLowerCase() && pageOf[x.name] === pageOf[s.name]);
          mapped = n ? n.name : '';
        }
        if (!mapped) console.warn(`${label}: ${s.name} drops its prerequisite ${need} (no new skill of the page takes its cell)`);
      }
      res[`reqskill${i + 1}`] = mapped;
    });
    if (p.how > 1) {
      const what = p.o ? `the cell of ${p.o.skill.skill}` : `an empty cell (row ${p.row}, column ${p.col})`;
      console.warn(`${label}: ${s.slot} is not on its tab (another mod changed the class tree); ${s.name} takes ${what}`);
    }
    out[s.name] = res;
  });
  return out;
}
